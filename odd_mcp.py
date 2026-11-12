#!/usr/bin/env python3
"""odd_mcp: odd's commands as MCP tools, so a coding agent calls them as tools instead of through a shell.

Speaks MCP over stdio: JSON-RPC 2.0, one message per line. Each tool runs odd.py (the file beside this one) as a
subprocess in the server's working directory and returns its exit code and everything it printed: 0 pass, 1 fail or
not shown, 2 could not run. Nothing odd decides is repeated here.

Dual-era: it answers the stateless 2026-07-28 revision (server/discover, the version in each request's _meta) and
the initialize handshake of 2025-11-25 and earlier. `odd init --mcp` copies this file to .odd/ and adds it to the
project's .mcp.json. Standard library only, Python 3.8+.
"""
import json
import os
import subprocess
import sys

MODERN = '2026-07-28'
LEGACY = ('2025-11-25', '2025-06-18', '2025-03-26', '2024-11-05')
VERSION_KEY = 'io.modelcontextprotocol/protocolVersion'
ODD_PY = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'odd.py')
MEANING = {0: 'pass', 1: 'fail / not shown', 2: 'could not run'}
S, B = {'type': 'string'}, {'type': 'boolean'}
SLUG = ('slug', S, 'the outcome, as named in .odd/outcomes/<slug>.md')
BASE = ('base', S, 'measure from this revision instead of the target branch')
NOCACHE = ('no-cache', B, 'verify in full even when the inputs match an earlier verification (odd 0.4.0 with backlog '
                         'item 12 and later)')
POSITIONAL = ('slug', 'ticket', 'outcome', 'reason', 'what', 'question')
TOOLS = (  # name, description, arguments (name, schema, description), the required ones
    ('new', 'State an outcome before the code: writes .odd/outcomes/<slug>.md. proof "auto" picks a narrow command '
            'from the test runner the repository uses and says what it detected. Ends with "read these first": the files '
            'inside the boundary (largest change first, at most ten) and the files the proof names.',
     [SLUG, ('outcome', S, 'one sentence: who observes what result'),
      ('proof', S, 'a command that exits 0 only when the outcome holds, or "auto" (optional with kind "refactor": '
                   'the whole suite)'),
      ('in', S, 'globs of the product files the change may touch, comma-separated'),
      ('test', S, 'with proof "auto": the test file the proof runs'),
      ('covers', S, 'the requirements this outcome covers, comma-separated: R1, R3 (.odd/requirements/<ticket>.md)'),
      ('kind', S, '"bug": seal and done require the proof to fail at the base revision (reproduce first); "feature": '
                  'the proof covers the new behaviour; "refactor": the proof defaults to the whole suite and the '
                  'take-out check is skipped')],
     ('slug', 'outcome', 'in')),
    ('seal', 'Optional, before the code: the proof must fail now; fingerprints the test files so a later edit shows.',
     [SLUG, BASE], ('slug',)),
    ('done', 'Verify an outcome: the proof passes, fails with the change taken out, and passes again.',
     [SLUG, BASE, NOCACHE], ('slug',)),
    ('gate', 'Check the whole change: every changed product file is inside one verified outcome or an exemption.',
     [BASE, ('recompute', B, 'trust nothing recorded: verify every outcome again (as CI does)'), NOCACHE], ()),
    ('race', 'Run the outcome as N parallel agent attempts, each in its own git worktree; each is verified as done '
             'would, and the verified one with the strongest proof and fewest changed lines is applied.',
     [SLUG, ('n', S, 'how many attempts, as a number (default: one per configured agent, or 3)'),
      ('agent', S, 'the agent command for every attempt, instead of "agents" in .odd/config.json'), BASE, NOCACHE], ('slug',)),
    ('cascade', 'Try the outcome with the configured agents in order, cheapest first, each attempt in its own git '
                'worktree and verified as done would; escalate to the next agent, with the failure passed on, only when '
                'no attempt is verified; park the outcome with every reason after the last.',
     [SLUG, ('agents', S, 'agent commands, cheapest first, comma-separated (default: "agents" in .odd/config.json)'),
      ('race', S, 'attempts per level in parallel, as a number (default 1)'), BASE, NOCACHE], ('slug',)),
    ('chain', 'Do a long task as a chain of proven outcomes: .odd/chains/<ticket>.md lists outcome slugs in order; each '
              'one not yet proven is attempted as race (or cascade) would, verified, and committed as the checkpoint '
              '"odd: <slug> proven". An unproven one stops the chain, the tree is back at the last checkpoint and the '
              'outcome is parked with the reasons; calling it again continues from the first unproven outcome.',
     [('ticket', S, 'the chain, as named in .odd/chains/<ticket>.md'),
      ('race', S, 'attempts per outcome in parallel, as a number (with cascade: per level, default 1)'),
      ('cascade', B, 'attempt each outcome with the agents in order, cheapest first, as cascade does'),
      ('agents', S, 'agent commands, comma-separated (default: "agents" in .odd/config.json)'), BASE, NOCACHE], ('ticket',)),
    ('spec', 'Have another agent (in practice a stronger model) write only the proof, in its own git worktree; the '
             'test files come back and are sealed red before any code; retried, then parked, if the proof does not '
             'fail first.',
     [SLUG, ('proof-by', S, 'the agent command that writes the proof; {prompt_file} becomes the prompt path, else stdin'),
      ('tries', S, 'tries for a proof that fails before the code, as a number (default 3)'), BASE], ('slug', 'proof-by')),
    ('park', 'The honest exit: the outcome is blocked or cannot be done as specified.',
     [SLUG, ('reason', S, 'why')], ('slug', 'reason')),
    ('ask', 'The outcome cannot be made checkable from the ticket: record one precise question; the gate reports the '
            'outcome as waiting for an answer until its "asked:" line is deleted.',
     [SLUG, ('question', S, 'one precise question, ending in "?"')], ('slug', 'question')),
    ('escaped', 'Record a defect that got past a merged outcome.',
     [SLUG, ('what', S, 'what went wrong, and where it was found')], ('slug', 'what')),
)
OUTPUT = {'type': 'object', 'properties': {'exit_code': {'type': 'integer'}, 'output': {'type': 'string'},
                                         'next': {'type': 'array', 'items': {'type': 'string'}}},
          'required': ['exit_code', 'output']}
INFO = {'name': 'odd', 'version': '1'}


class RpcError(Exception):
    def __init__(self, code, message, data=None):
        Exception.__init__(self, message)
        self.code, self.data = code, data


def tool_list():
    return [{'name': name, 'description': text, 'outputSchema': OUTPUT,
             'inputSchema': {'type': 'object', 'additionalProperties': False, 'required': list(req),
                             'properties': {k: dict(schema, description=d) for k, schema, d in args}}}
            for name, text, args, req in TOOLS]


def argv_for(name, given):
    """odd's command line for one tool call; arguments of the wrong name or kind are refused before odd runs."""
    spec = [t for t in TOOLS if t[0] == name]
    if not spec:
        raise RpcError(-32602, 'unknown tool: %s (the tools are: %s)' % (name, ', '.join(t[0] for t in TOOLS)))
    _, _, args, req = spec[0]
    kinds = {k: schema['type'] for k, schema, _ in args}
    given = given if isinstance(given, dict) else {}
    wrong = [k for k in given if k not in kinds or not isinstance(given[k], bool if kinds[k] == 'boolean' else str)]
    missing = [k for k in req if not given.get(k)]
    if wrong or missing:
        raise RpcError(-32602, 'odd %s: %s' % (name, '; '.join(
            (['not an argument, or the wrong kind of value: ' + ', '.join(wrong)] if wrong else []) +
            (['missing: ' + ', '.join(missing)] if missing else []))))
    flags, pos = [], []
    for k, _, _ in args:  # flags first, then "--", so a value starting with "-" is never read as an option
        v = given.get(k)
        if k in POSITIONAL and v is not None:
            pos.append(v)
        elif v is True:
            flags.append('--' + k)
        elif isinstance(v, str):
            flags += ['--' + k, v]
    return [name] + flags + (['--'] + pos if pos else [])


def call(name, given):
    argv = argv_for(name, given)
    if not os.path.isfile(ODD_PY):
        return result(2, 'odd: could not run: odd.py is not beside odd_mcp.py (%s)' % ODD_PY, name)
    try:
        r = subprocess.run([sys.executable, ODD_PY] + argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT, universal_newlines=True, errors='replace')
        rc, out = r.returncode, r.stdout
    except OSError as e:
        rc, out = 2, 'odd: could not run: %s (odd_mcp runs %s)' % (e, ODD_PY)
    return result(rc, out, name)


def result(rc, out, name):
    rc = rc if rc in MEANING else 2  # anything else is never reported as a pass or a plain failure
    lines = out.rstrip('\n').split('\n')
    at = [i for i, line in enumerate(lines) if line == 'next:']  # odd's next: block (a failed done, race or cascade)
    more = {'next': [line.strip() for line in lines[at[-1] + 1:]]} if at else {}
    return {'content': [{'type': 'text', 'text': 'odd %s: exit %d (%s)\n%s' % (name, rc, MEANING[rc], out)}],
            'structuredContent': dict({'exit_code': rc, 'output': out}, **more), 'isError': rc != 0}


def handle(method, params):
    meta_in = params.get('_meta')
    version = meta_in.get(VERSION_KEY) if isinstance(meta_in, dict) else None
    if version is not None and version not in (MODERN,) + LEGACY:
        raise RpcError(-32022, 'Unsupported protocol version', {'supported': [MODERN] + list(LEGACY), 'requested': version})
    if method == 'initialize':  # the handshake of 2025-11-25 and earlier
        asked = params.get('protocolVersion')
        return {'protocolVersion': asked if asked in LEGACY else LEGACY[0], 'capabilities': {'tools': {}}, 'serverInfo': INFO}
    meta = {'_meta': {'io.modelcontextprotocol/serverInfo': INFO}, 'resultType': 'complete'}
    if method == 'server/discover':
        return dict(meta, supportedVersions=[MODERN] + list(LEGACY), capabilities={'tools': {}}, ttlMs=3600000,
                    cacheScope='public')
    if method == 'tools/list':
        return dict(meta, tools=tool_list(), ttlMs=3600000, cacheScope='public')
    if method == 'tools/call':
        return dict(meta, **call(params.get('name'), params.get('arguments')))
    if method == 'ping':
        return {}
    raise RpcError(-32601, 'method not found: %s' % method)


def reply(msg):
    """The answer to one parsed message, or None for a notification."""
    if not isinstance(msg, dict) or not isinstance(msg.get('method'), str):
        return {'jsonrpc': '2.0', 'id': msg.get('id') if isinstance(msg, dict) else None,
                'error': {'code': -32600, 'message': 'invalid request'}}
    if 'id' not in msg:
        return None
    try:
        params = msg.get('params') if isinstance(msg.get('params'), dict) else {}
        return {'jsonrpc': '2.0', 'id': msg['id'], 'result': handle(msg['method'], params)}
    except RpcError as e:
        err = {'code': e.code, 'message': str(e)}
        if e.data is not None:
            err['data'] = e.data
        return {'jsonrpc': '2.0', 'id': msg['id'], 'error': err}


def main():
    inp = sys.stdin.buffer
    while True:
        line = inp.readline()
        if not line:
            return 0
        if not line.strip():
            continue
        try:
            out = reply(json.loads(line.decode('utf-8', 'replace')))
        except ValueError:
            out = {'jsonrpc': '2.0', 'id': None, 'error': {'code': -32700, 'message': 'parse error'}}
        if out is not None:
            sys.stdout.write(json.dumps(out) + '\n')
            sys.stdout.flush()


if __name__ == '__main__':
    sys.exit(main())
