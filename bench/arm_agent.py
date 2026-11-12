#!/usr/bin/env python3
"""The bench's side of an arm-supplied agent (arms/<arm>/agent.sh; SPEC.md "An arm-supplied agent").

run.py imports the transcript readers below, and copies this file beside agent.sh into the session's own top
directory (outside the repository and the bench) as $ARM_HELPER, so nothing an arm runs names the bench's path.

  arm_agent.py session --model M [--name NAME]   one claude session, the prompt on stdin, started exactly as run.py
                                                 starts the plain arm's (ARM_CLAUDE_FLAGS, the plain environment),
                                                 bounded by ARM_TIMEOUT; its stream-json goes to $ARM_TRANSCRIPTS;
                                                 prints its result object and "odd-cost: <usd>" (the line odd reads)
  arm_agent.py summary [--final-file F]          one result object: F's text as "result", figures summed over every
                                                 transcript in $ARM_TRANSCRIPTS
  arm_agent.py odd race|cascade|spec             the odd flows of the odd-race, odd-cascade and odd-spec arms (their
                                                 NOTES.md): a first session, then odd's own command with sessions
                                                 started by `session` as its agents, then the gate; prints the summary

Standard library only; Python 3.8.
"""
import argparse
import json
import os
import re
import shlex
import subprocess
import sys
import time

# ---------------------------------------------------------------- transcript readers (run.py uses these too)


def events(transcript):
    """The stream-json events of a transcript, in order; lines that are not JSON objects are skipped."""
    for line in transcript.splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if isinstance(event, dict):
            yield event


def parse_result(stdout):
    """The agent's result object: the whole output, or failing that its last line that is such an object."""
    for text in [stdout] + stdout.strip().splitlines()[::-1]:
        try:
            found = json.loads(text)
        except ValueError:
            continue
        if isinstance(found, list):
            found = next((o for o in reversed(found) if isinstance(o, dict) and o.get('type') == 'result'), None)
        if isinstance(found, dict) and ('result' in found or found.get('type') == 'result'):
            return found
    return None


USAGE_KEYS = ('input_tokens', 'output_tokens', 'cache_read_input_tokens', 'cache_creation_input_tokens')


def tokens(result):
    """(input, output, cache read, cache write) tokens. The CLI's "modelUsage" counts subagents too, so it is used
    when present; "usage" is the main conversation only."""
    per_model = [m for m in (result.get('modelUsage') or {}).values() if isinstance(m, dict)]
    if per_model:
        return [sum(m.get(k) or 0 for m in per_model)
                for k in ('inputTokens', 'outputTokens', 'cacheReadInputTokens', 'cacheCreationInputTokens')]
    usage = result.get('usage') or {}
    return [usage.get(k) for k in USAGE_KEYS]


def stream_usage(transcript):
    """(tokens, turns, models) rebuilt from the assistant events of a transcript that has no result event (a session
    stopped by the timeout), or None when it has no assistant event with usage. The CLI repeats one message's usage
    on every event it splits that message into, so each message id counts once (its last event). Subagents' messages
    count too, as modelUsage would; turns count the main conversation's messages only."""
    last, main = {}, set()
    for n, event in enumerate(events(transcript)):
        message = event.get('message') if event.get('type') == 'assistant' else None
        if not isinstance(message, dict) or not isinstance(message.get('usage'), dict):
            continue
        key = message.get('id') or n
        last[key] = message
        if not event.get('parent_tool_use_id'):
            main.add(key)
    if not last:
        return None
    totals = [sum(m['usage'].get(k) or 0 for m in last.values()) for k in USAGE_KEYS]
    return totals, len(main), sorted({m['model'] for m in last.values() if isinstance(m.get('model'), str)})


EMPHASIS = re.compile(r'[*`]|(?<![A-Za-z0-9])_+|_+(?![A-Za-z0-9])')
LEADING_MARKS = re.compile(r'^(?:[\s>#+-]+|\d+[.)]\s+)+')
VERDICT = re.compile(r'RESULT:\s*(NOT\s+DONE|DONE)\s*(?:[:\-–—]\s*(.*))?$', re.IGNORECASE)


def parse_claim(final):
    """(claim, reason): the last line of the final message that contains RESULT:, cleaned of Markdown, must read
    RESULT: DONE or RESULT: NOT DONE, optionally with ':' or a dash and a reason; anything else is ('none', '')."""
    line = next((x for x in reversed(final.splitlines()) if 'RESULT:' in x), '')
    line = LEADING_MARKS.sub('', EMPHASIS.sub('', line)).strip()
    found = VERDICT.match(line) if line.startswith('RESULT:') else None
    if not found:
        return 'none', ''
    return ('NOT DONE' if found.group(1).upper() != 'DONE' else 'DONE'), (found.group(2) or '').strip()


# ---------------------------------------------------------------- sessions and their sum

# The CLI's result subtypes for a cap: graded on the tree left, named in stopped_at (run.py) and never carried on from.
CAPS = {'error_max_turns': 'max_turns', 'error_max_budget_usd': 'max_budget'}
# The line an odd flow puts its own reason on when it, not a model, ends the run NOT DONE: run.py records it as
# arm_reason and never as claim_reason, so no hidden keyword grade reads words the harness wrote (SPEC.md).
ARM_REASON = 'arm reason: '

END = 'bench_session_end'  # the line `session` appends to each transcript: the model, exit status (null: timed out)


def transcripts(folder):
    """[(file name, text)] of every session transcript in folder, in the order they started."""
    names = sorted(n for n in os.listdir(folder) if n.endswith('.jsonl')) if os.path.isdir(folder) else []
    found = []
    for name in names:
        with open(os.path.join(folder, name), encoding='utf-8', errors='replace') as f:
            found.append((name, f.read()))
    return found


def total(folder):
    """The figures of every session in folder summed: cost (null when any session has none: the CLI prices a session
    only in its result event), turns, duration, tokens (each session's own result, else its assistant events), the
    models seen, and one entry per session (file, model, exit, cost, its result object or null)."""
    s = {'total_cost_usd': 0.0, 'num_turns': 0, 'duration_ms': 0, 'usage': dict.fromkeys(USAGE_KEYS, 0),
         'models': set(), 'sessions': []}
    for name, text in transcripts(folder):
        result = parse_result(text) or {}
        end = next((e for e in reversed(list(events(text))) if e.get('type') == END), {})
        rebuilt = stream_usage(text)
        if any(k in result for k in ('total_cost_usd', 'usage', 'modelUsage')):
            counts, turns = tokens(result), result.get('num_turns')
            s['models'].update(result.get('modelUsage') or {})
        else:
            counts, turns = (rebuilt[0], rebuilt[1]) if rebuilt else ([0] * 4, 0)
        if rebuilt:
            s['models'].update(rebuilt[2])
        for k, v in zip(USAGE_KEYS, counts):
            s['usage'][k] += v or 0
        s['num_turns'] += turns or 0
        s['duration_ms'] += result.get('duration_ms') or 0
        cost = result.get('total_cost_usd')
        if cost is None or s['total_cost_usd'] is None:
            s['total_cost_usd'] = None
        else:
            s['total_cost_usd'] = round(s['total_cost_usd'] + cost, 10)
        s['sessions'].append({'file': name, 'model': end.get('model'), 'exit': end.get('exit') if end else None,
                              'ended': bool(end), 'cost_usd': cost, 'result': result or None})
    s['models'] = sorted(s['models'])
    return s


def summary(final):
    """The one result object an arm-supplied agent ends with: `final` as its text, the figures of every session."""
    s = total(os.environ['ARM_TRANSCRIPTS'])
    return {'type': 'result', 'subtype': 'success', 'is_error': False, 'result': final,
            'total_cost_usd': s['total_cost_usd'], 'num_turns': s['num_turns'], 'duration_ms': s['duration_ms'],
            'usage': s['usage'], 'models': s['models'], 'sessions': len(s['sessions'])}


def run_caps(flags):
    """The plain arm's flags with --max-turns and --max-budget-usd set to what is left of the RUN's caps (ARM_MAX_TURNS,
    ARM_MAX_BUDGET_USD, less every earlier session's turns and cost), so the arm as a whole is held to plain's caps,
    not each of its sessions. Returns (flags, None), or (None, the CAPS subtype) when that cap is already spent."""
    spent = total(os.environ['ARM_TRANSCRIPTS'])
    used = {'--max-turns': spent['num_turns'], '--max-budget-usd': sum(x['cost_usd'] or 0 for x in spent['sessions'])}
    limits = (('--max-turns', os.environ.get('ARM_MAX_TURNS'), int, 'error_max_turns'),
              ('--max-budget-usd', os.environ.get('ARM_MAX_BUDGET_USD'), float, 'error_max_budget_usd'))
    flags = list(flags)
    for flag, limit, kind, cap in limits:
        if not limit or flag not in flags:
            continue
        left = round(kind(limit) - used[flag], 6)
        if left <= 0:
            return None, cap
        flags[flags.index(flag) + 1] = str(left)
    return flags, None


def session(prompt, model, name='session'):
    """One claude session with the plain arm's command line and environment, bounded by ARM_TIMEOUT seconds (it is
    killed at that point, as run.py kills the plain arm's), its turn and budget caps what is left of the run's
    (run_caps). Its stream-json is written to a file of its own in ARM_TRANSCRIPTS, closed by an END line. A session
    the spent caps refuse starts no claude: its file holds a result event with the cap's subtype, cost 0, marked
    bench_refused. Returns (exit status or None on timeout, the result object or None)."""
    flags, spent = run_caps(json.loads(os.environ['ARM_CLAUDE_FLAGS']))
    names = json.loads(os.environ['ARM_AGENT_ENV']) + ['ODD_ATTEMPT']  # odd's mark for its process sweep
    env = {k: os.environ[k] for k in names if k in os.environ}
    path = os.path.join(os.environ['ARM_TRANSCRIPTS'], '%015d-%s-%d.jsonl' % (time.time() * 1000, name, os.getpid()))
    if spent:
        refused = {'type': 'result', 'subtype': spent, 'is_error': True, 'result': None, 'total_cost_usd': 0,
                   'num_turns': 0, 'duration_ms': 0, 'bench_refused': True,
                   'errors': ['bench: the run\'s %s is spent; no claude session was started' % CAPS[spent]]}
        with open(path, 'w', encoding='utf-8') as log:
            log.write(json.dumps(refused) + '\n' + json.dumps({'type': END, 'model': model, 'name': name, 'exit': 1,
                                                               'stderr': ''}) + '\n')
        return 1, refused
    with open(path, 'w', encoding='utf-8') as log:
        p = subprocess.Popen(['claude', '-p', prompt, '--model', model] + flags, stdin=subprocess.DEVNULL,
                             stdout=log, stderr=subprocess.PIPE, env=env, encoding='utf-8', errors='replace')
        try:
            err = p.communicate(timeout=float(os.environ['ARM_TIMEOUT']))[1]
            status = p.returncode
        except subprocess.TimeoutExpired:
            p.kill()
            err, status = p.communicate()[1], None
    with open(path, 'a', encoding='utf-8') as log:
        log.write(json.dumps({'type': END, 'model': model, 'name': name, 'exit': status,
                              'stderr': (err or '').strip()[-300:]}) + '\n')
    with open(path, encoding='utf-8', errors='replace') as f:
        return status, parse_result(f.read())


def session_command(model, name):
    """The shell command odd runs as an agent: this file's `session`, the prompt on stdin."""
    return ' '.join(shlex.quote(w) for w in (sys.executable, os.path.abspath(__file__), 'session', '--model', model,
                                             '--name', name))


# ---------------------------------------------------------------- the odd flows

OUTPUT = []  # what odd printed: the arm's own output before its result object, which run.py audits


def sh(cmd, said):
    """Run cmd (odd) in the session directory; one line for the final message goes into `said`, its whole output
    into OUTPUT."""
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, encoding='utf-8', errors='replace')
    shown = ' '.join(shlex.quote(w) for w in ['odd'] + cmd[2:4])
    OUTPUT.append('$ %s  (exit %d)\n%s' % (' '.join(shlex.quote(w) for w in ['odd'] + cmd[2:]), p.returncode,
                                           p.stdout.rstrip()))
    said.append('%s: exit %d' % (shown, p.returncode))
    return p.returncode, p.stdout


def why(output):
    """odd's reason for a refusal, one line: the first line with the first of `keys` found (most telling first), else
    its last non-empty line."""
    lines = [x.strip() for x in output.splitlines() if x.strip()]
    keys = ('parked', 'no attempt', 'not verified', 'refused', 'could not', 'left as a patch', 'fail', 'error')
    picked = next((x for k in keys for x in lines if k in x.lower()), lines[-1] if lines else 'no output')
    return ' '.join(picked.split())[:400]


def outcome_field(path, key):
    with open(path, encoding='utf-8', errors='replace') as f:
        return next((x.split(':', 1)[1].strip() for x in f.read().splitlines() if x.startswith(key + ':')), None)


def stated_outcomes():
    """The outcome files this session added (not on main), in name order."""
    folder = os.path.join('.odd', 'outcomes')
    on_main = subprocess.run(['git', 'ls-tree', '-r', '--name-only', 'main', '--', folder], stdout=subprocess.PIPE,
                             encoding='utf-8').stdout.split()
    here = sorted(os.path.join(folder, n) for n in os.listdir(folder) if n.endswith('.md')) \
        if os.path.isdir(folder) else []
    return [p for p in here if p not in on_main]


def commit(message):
    subprocess.run(['git', 'add', '-A'], stdout=subprocess.DEVNULL)
    subprocess.run(['git', 'commit', '-q', '--allow-empty', '--no-verify', '-m', message], stdout=subprocess.DEVNULL)


def odd_flow(mode, prompt):
    """Returns the final message (ending in the RESULT line) of the odd-race, odd-cascade or odd-spec arm."""
    odd = [sys.executable, os.environ['ARM_ODD_PY']]
    cheap, strong = os.environ['ARM_MODEL'], os.environ['ARM_STRONG_MODEL']
    status, result = session(prompt, cheap, 'outcome')
    if result is None:
        sys.exit('the first claude session printed no result object (exit %s)' % status)
    first = result.get('result') if isinstance(result.get('result'), str) else ''
    claim, _ = parse_claim(first)
    # NOT DONE is the method's honest exit (nothing to race); a session stopped at a cap, or one with no RESULT line,
    # ends the arm as plain's only session would: its own final message is graded, nothing carries on from it.
    if claim != 'DONE' or result.get('subtype') in CAPS or result.get('is_error'):
        return first
    said = ['first session (%s): claim %s' % (cheap, claim)]

    def refuse(reason):  # the harness's reason, kept off the RESULT line: no keyword grade may credit it
        return '\n'.join(said + [ARM_REASON + reason, 'RESULT: NOT DONE'])

    outcomes = stated_outcomes()
    live = [p for p in outcomes if not outcome_field(p, 'parked')]
    if not live:
        parked = [outcome_field(p, 'parked') for p in outcomes]
        if parked:  # the model's own words, from the outcome file it parked
            return '\n'.join(said + ['RESULT: NOT DONE: %s' % parked[0]])
        return refuse('no outcome was stated with odd new')
    for path in live:
        slug = os.path.basename(path)[:-3]
        if mode == 'spec':
            code, out = sh(odd + ['spec', slug, '--proof-by', session_command(strong, 'proof'), '--base', 'main'], said)
            if code:
                return refuse('odd spec %s: %s' % (slug, why(out)))
        elif not outcome_field(path, 'sealed'):
            code, out = sh(odd + ['seal', slug, '--base', 'main'], said)
            if code:
                return refuse('the proof of %s could not be sealed: %s' % (slug, why(out)))
        commit('odd: %s stated and its proof sealed' % slug)  # every attempt starts from HEAD
        if mode == 'cascade':
            levels = ','.join(session_command(m, 'level%d' % i) for i, m in enumerate((cheap, strong), 1))
            cmd = odd + ['cascade', slug, '--agents', levels, '--base', 'main']
        else:
            cmd = odd + ['race', slug, '--n', '3' if mode == 'race' else '1', '--agent',
                         session_command(cheap, 'attempt'), '--base', 'main']
        code, out = sh(cmd, said)
        if code:
            return refuse('odd %s %s: %s' % (cmd[2], slug, why(out)))
        code, out = sh(odd + ['done', slug, '--base', 'main'], said)
        if code:
            return refuse('odd done %s after the winner was applied: %s' % (slug, why(out)))
        commit('odd: %s proven' % slug)
    code, out = sh(odd + ['gate', '--recompute', '--base', 'main'], said)
    return '\n'.join(said + ['RESULT: DONE']) if code == 0 else refuse('the odd gate failed: %s' % why(out))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    sub = ap.add_subparsers(dest='cmd')
    s = sub.add_parser('session')
    s.add_argument('--model', required=True)
    s.add_argument('--name', default='session')
    s = sub.add_parser('summary')
    s.add_argument('--final-file')
    s = sub.add_parser('odd')
    s.add_argument('mode', choices=('race', 'cascade', 'spec'))
    a = ap.parse_args(argv)
    if a.cmd == 'session':
        status, result = session(sys.stdin.read(), a.model, a.name)
        if result is not None:
            print(json.dumps(result))
            if isinstance(result.get('total_cost_usd'), (int, float)):
                print('odd-cost: %.6f' % result['total_cost_usd'])  # the line odd cascade and odd stats read
        return 0 if status == 0 and result is not None else (status or 1)
    if a.cmd == 'summary':
        final = ''
        if a.final_file:
            with open(a.final_file, encoding='utf-8') as f:
                final = f.read()
        print(json.dumps(summary(final)))
        return 0
    if a.cmd == 'odd':
        final = odd_flow(a.mode, sys.stdin.read())
        print('\n'.join(OUTPUT))  # odd's output, for the contamination audit
        print(json.dumps(summary(final)))
        return 0
    ap.print_usage()
    return 2


if __name__ == '__main__':
    sys.exit(main())
