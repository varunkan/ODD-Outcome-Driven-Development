#!/usr/bin/env python3
"""odd: Outcome-Driven Development. An outcome counts as delivered only when its proof fails without the change.

An outcome is one sentence, a proof command and a boundary, kept in .odd/outcomes/<slug>.md. It is verified when the
proof passes on the tree as it is, fails on the same tree with the change taken out, and passes again once the
change is put back. `odd gate` checks that every changed product file is inside the boundary of one verified
outcome; with --recompute (CI) it trusts nothing recorded.

  odd init [--claude-hooks] [--mcp]                       install or repair
  odd new <slug> "<outcome>" --proof "<command>" --in "<globs, comma-separated>"   (--proof auto [--test PATH])
  odd seal <slug> [--base REF]                            optional: the proof fails now; fingerprint its tests
  odd done <slug> [--base REF]                            exit 0 verified, 1 not shown, 2 could not run
  odd gate [--base REF] [--recompute]                     exit 0 pass, 1 fail, 2 could not run
  odd park <slug> "<reason>"                              blocked, or cannot be done as specified
  odd escaped <slug> "<what went wrong, where found>"     a defect got past this outcome; record it
  odd stats                                               counts (self-reported)

Needs a POSIX system, git 2.23+ and Python 3.8+. One file, standard library only, so a project vendors it as
.odd/odd.py. Design and limits: DESIGN.md.
"""
import argparse
import collections
import datetime
import hashlib
import json
import os
import re
import shlex
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import traceback

try:
    import fcntl
except ImportError:  # not a POSIX system
    fcntl = None

VERSION = '0.4.0'
DEFAULTS = {
    'trivial_lines': 25,   # product lines that may change outside any outcome (a per-change budget)
    'exempt': ['.odd/outcomes/**', '**/*.md', 'LICENSE*', '.gitignore', '.gitattributes', '**/*.lock',
               '**/package-lock.json', '**/pnpm-lock.yaml', '**/go.sum', '**/__pycache__/**', '**/*.pyc'],
    'test_globs': ['**/tests/**', '**/test/**', '**/spec/**', '**/__tests__/**', '**/test_*.py', '**/*_test.*',
                   '**/*.test.*', '**/*.spec.*'],   # a proof's own files: never taken out, need no outcome
    'proof_timeout': 900,  # seconds per proof run
    'default_branch': None,
    'strength': 'report',  # small breaks in the changed lines after green-red-green: off, report, or enforce (a survivor fails)
    'mutants': 8,          # at most this many per outcome; each one is one proof run
}
CONTROL = ('.odd/odd.py', '.odd/config.json', '.odd/odd_mcp.py')  # no outcome needed; always reported; the first two read from the target in CI
FIELDS = ('outcome', 'proof', 'in', 'counterfactual', 'parked', 'escaped', 'sealed', 'test-change')
SLUG = re.compile(r'^[a-z0-9][a-z0-9._-]{0,63}$')
BIG = 10 ** 6  # a binary file or submodule pointer is never a "small change"
WIDE = 120     # bytes that count as one line in the small-change lane
MARKER = '<!-- odd-gate -->'  # finds the pull-request comment of an earlier run, so there is only ever one
RESULT = ('files', 'lines', 'seconds', 'red_says', 'skip', 'strength')  # what --json says of a verified outcome
ODD = 'odd'    # how the tool was invoked, for messages a reader can paste


class Fail(Exception):
    """The outcome is not shown (exit 1)."""


class CouldNotRun(Exception):
    """Nothing was established (exit 2). Never reported as a pass."""


# ---------------------------------------------------------------- git, paths, settings

def sh(args, cwd, **kw):
    """Run git. Paths are handed over as they are, never as patterns: a file named v[2].py is that file only."""
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True, errors='surrogateescape',
                          env=dict(os.environ, GIT_LITERAL_PATHSPECS='1'), **kw)


def git(root, *args):
    r = sh(['git'] + list(args), root)
    if r.returncode != 0:
        raise CouldNotRun('git %s: %s' % (' '.join(args[:3]), (r.stderr or r.stdout).strip()[:300]))
    return r.stdout


def zlist(root, *args):
    return [x for x in git(root, *args).split('\0') if x]


def chunks(paths, n=500):
    """Long path lists go to git a few hundred at a time, under any limit on the length of a command."""
    return [paths[i:i + n] for i in range(0, len(paths), n)]


def find_root():
    r = sh(['git', 'rev-parse', '--show-toplevel'], os.getcwd())
    if r.returncode != 0:
        raise CouldNotRun('not inside a git repository (odd uses git to see what changed)')
    return r.stdout.strip()


def odd_dir(root, *p):
    return os.path.join(root, '.odd', *p)


def state_dir(root, *p):
    """Journals, local evidence and hook marks live under the git directory: they cannot be committed, and a proof
    looking at the working tree sees nothing of them. One per worktree."""
    d = git(root, 'rev-parse', '--git-dir').strip()
    return os.path.join(d if os.path.isabs(d) else os.path.join(root, d), 'odd', *p)


def rev(root, ref):
    r = sh(['git', 'rev-parse', '--verify', '--quiet', ref + '^{commit}'], root)
    return r.stdout.strip() if r.returncode == 0 else None


def read_text(path):
    try:
        with open(path, encoding='utf-8') as f:
            return f.read()
    except ValueError:
        raise CouldNotRun('%s is not UTF-8 text' % path)


def glob_re(pat, tree=False):
    """Globs are relative to the repository root: * and ? stay inside one path segment, ** crosses segments. A
    boundary (`in:`) that names a directory covers everything under it; exempt and test globs match files only, so
    a directory called notes.md exempts nothing."""
    pat = pat.strip()
    while pat.startswith('./'):
        pat = pat[2:]
    pat = pat.rstrip('/')
    out, i = '', 0
    while i < len(pat):
        if pat.startswith('**/', i):
            out, i = out + '(?:.*/)?', i + 3
        elif pat.startswith('**', i):
            out, i = out + '.*', i + 2
        elif pat[i] == '*':
            out, i = out + '[^/]*', i + 1
        elif pat[i] == '?':
            out, i = out + '[^/]', i + 1
        else:
            out, i = out + re.escape(pat[i]), i + 1
    return re.compile('^' + out + ('(?:/.*)?' if tree else '') + '$')


def matches(path, globs, tree=False):
    return any(glob_re(g, tree).match(path) for g in globs if g.strip())


def split_globs(s):
    return [g.strip() for g in (s or '').split(',') if g.strip()]


def _globs(v):
    return isinstance(v, list) and all(isinstance(g, str) and g.strip() for g in v)


SETTINGS = {'trivial_lines': lambda v: type(v) is int and v >= 0,
            'proof_timeout': lambda v: type(v) in (int, float) and 0 < v < float('inf'),
            'default_branch': lambda v: v is None or (isinstance(v, str) and bool(v.strip())),
            'exempt': _globs, 'test_globs': _globs,
            'strength': lambda v: v in ('off', 'report', 'enforce'), 'mutants': lambda v: type(v) is int and v >= 0}


def load_config(root, at=None):
    """Settings, checked: a wrong shape stops the run instead of quietly meaning something else. When recomputing
    they are read at the tip of the target branch (`at`), so a change cannot loosen its own gate; a project adopting
    odd in this very change gets the defaults."""
    name = '.odd/config.json' + (' at %s' % at[:10] if at else '')
    if at:
        r = sh(['git', 'show', '%s:.odd/config.json' % at], root)
        text = r.stdout if r.returncode == 0 else '{}'
    else:
        text = read_text(odd_dir(root, 'config.json')) if os.path.isfile(odd_dir(root, 'config.json')) else '{}'
    try:
        data = json.loads(text)
    except ValueError as e:
        raise CouldNotRun('%s is not valid JSON (%s)' % (name, e))
    if not isinstance(data, dict):
        raise CouldNotRun('%s must hold one JSON object of settings (%s)' % (name, ', '.join(SETTINGS)))
    for k, v in data.items():
        if k not in SETTINGS:
            raise CouldNotRun('%s: "%s" is not a setting (the settings are: %s)' % (name, k, ', '.join(SETTINGS)))
        if not SETTINGS[k](v):
            raise CouldNotRun('%s: "%s" has the wrong kind of value (the default is %s)' % (name, k, json.dumps(DEFAULTS[k])))
    return dict(DEFAULTS, **data)


def full_ref(root, name):
    """The one ref a name stands for. Git prefers a tag, then a local branch, to a remote branch of the same name,
    so a pushed tag called origin/main would stand in for the target branch: a name that fits several is refused."""
    if name.startswith('refs/'):
        return name
    hits = [p + name for p in ('refs/tags/', 'refs/heads/', 'refs/remotes/')
            if sh(['git', 'show-ref', '--verify', '--quiet', p + name], root).returncode == 0]
    if len(hits) > 1:
        raise CouldNotRun('%r names more than one ref here (%s): pass the one you mean in full as --base'
                          % (name, ', '.join(hits)))
    return hits[0] if hits else name


def find_base(root, cfg, arg=None):
    """(base, target). The base is the one revision everything is measured from: where this branch left the target
    branch. The target is that branch's tip, where the settings are read when recomputing."""
    if not rev(root, 'HEAD'):
        return None, None  # no commits yet: everything is new
    ref = arg or os.environ.get('ODD_BASE')
    if ref:
        cands = [full_ref(root, ref)]
    else:
        d = cfg.get('default_branch')
        names = [d] if d else ['main', 'master']
        cands = ['refs/remotes/origin/' + n for n in names] + ['refs/heads/' + n for n in names]
        r = sh(['git', 'symbolic-ref', 'refs/remotes/origin/HEAD'], root)
        if not d and r.returncode == 0 and r.stdout.strip():
            cands.insert(0, r.stdout.strip())
    for c in cands:
        tip = rev(root, c)
        if tip:
            mb = sh(['git', 'merge-base', 'HEAD', tip], root)
            if mb.returncode == 0 and mb.stdout.strip():
                return mb.stdout.strip(), tip
            raise CouldNotRun('HEAD and %s share no history here (a shallow clone?). Fetch it: git fetch --unshallow '
                              '(in CI: a full-history checkout, fetch-depth: 0)' % c)
    if ref:
        raise CouldNotRun('base revision %r not found. Fetch it: git fetch origin %s' % (ref, ref.split('/')[-1]))
    raise CouldNotRun('cannot tell which branch this work leaves from (no main, master or origin/HEAD): pass --base '
                      '<branch>, or have the owner set "default_branch" in .odd/config.json')


EMPTY_TREE = '4b825dc642cb6eb9a060e54bf8d69288fbee4904'
DIFF = ('diff', '--no-renames', '--ignore-submodules=none', '-z')  # a rename is a delete and an add; no pointer is hidden


def changed_files(root, base):
    """Every path that differs from the base in the working tree (committed, staged or not), plus untracked files.
    Computed from git, so files written through a shell are seen like any other."""
    names = set(zlist(root, *DIFF, '--name-only', base or EMPTY_TREE))
    names |= set(zlist(root, 'ls-files', '--others', '--exclude-standard', '-z'))
    return sorted(names)


def sizes(root, base, paths, budget=None):
    """{path: changed lines}; BIG for a binary file, a submodule pointer or a directory. With a budget (the
    small-change lane) any change costs at least one line and a line holds at most WIDE bytes, so an empty file, a
    mode change and a module written on one line cost what they hold."""
    stat, links, toks, i = {}, set(), zlist(root, *DIFF, '--raw', '--numstat', base or EMPTY_TREE), 0
    while i < len(toks):
        if toks[i].startswith(':'):  # :oldmode newmode ... then the path
            if '160000' in toks[i].split()[:2]:
                links.add(toks[i + 1])
            i += 2
        else:
            a, d, p = toks[i].split('\t', 2)
            stat[p], i = (BIG if '-' in (a, d) else int(a) + int(d)), i + 1
    out, total = {}, 0
    for p in paths:
        full, wide = os.path.join(root, p), 0
        if p in links or (p not in stat and os.path.isdir(full) and not os.path.islink(full)):
            n = BIG
        elif p in stat:
            n = stat[p]
            if budget is not None and n < BIG and total <= budget:
                body = sh(['git', 'diff', '-U0', '--no-renames', '--no-ext-diff', '--no-textconv', base or EMPTY_TREE,
                           '--', p], root).stdout.split('\n@@', 1)[-1]
                wide = sum(len(l) for l in body.split('\n') if l[:1] in ('+', '-'))
        elif os.path.islink(full):
            n = 1
        else:  # untracked
            try:
                with open(full, 'rb') as f:
                    data = f.read()
                n = BIG if b'\0' in data[:8000] else data.count(b'\n') + (1 if data and not data.endswith(b'\n') else 0)
                wide = len(data)
            except OSError:
                n = BIG
        out[p] = n if budget is None or n >= BIG else max(n, 1, wide // WIDE)
        total += out[p]
    return out


def classify(changed, cfg):
    """(control, exempt, tests, product) — each changed path falls in exactly one."""
    control = [p for p in changed if p in CONTROL]
    exempt = [p for p in changed if p not in CONTROL and matches(p, cfg['exempt'])]
    tests = [p for p in changed if p not in control and p not in exempt and matches(p, cfg['test_globs'])]
    rest = set(control) | set(exempt) | set(tests)
    return control, exempt, tests, [p for p in changed if p not in rest]


# ---------------------------------------------------------------- outcome files and local evidence

class Outcome:
    """`.odd/outcomes/<slug>.md`: front matter of `key: value` lines (an indented line continues the value above),
    then free notes."""

    def __init__(self, root, slug):
        self.root, self.slug = root, slug
        self.path = odd_dir(root, 'outcomes', slug + '.md')
        self.rel = '.odd/outcomes/%s.md' % slug
        self.f, self.notes = collections.OrderedDict(), '\n'

    @classmethod
    def load(cls, root, slug):
        o = cls(root, slug)
        if not os.path.isfile(o.path):
            raise Fail('no outcome %r in .odd/outcomes/ (%s new creates one)' % (slug, ODD))
        try:
            with open(o.path, encoding='utf-8') as f:
                lines = f.read().split('\n')
        except ValueError:
            raise Fail('%s is not UTF-8 text' % o.rel)
        if not lines or lines[0].strip() != '---':
            raise Fail('%s: must start with a --- line' % o.rel)
        key, n = None, 1
        while n < len(lines) and lines[n].strip() != '---':
            line = lines[n]
            m = re.match(r'^([a-z][a-z_-]*):\s?(.*)$', line)
            if m:
                key = m.group(1)
                if key not in FIELDS:
                    raise Fail('%s line %d: unknown field "%s" (the fields are: %s)' % (o.rel, n + 1, key, ', '.join(FIELDS)))
                o.f[key] = m.group(2).strip()
            elif line[:1] in (' ', '\t') and key and line.strip():
                o.f[key] = (o.f[key] + ' ' + line.strip()).strip()
            elif line.strip():
                raise Fail('%s line %d: expected "key: value" (indent a line to continue the value above)' % (o.rel, n + 1))
            n += 1
        if n >= len(lines):
            raise Fail('%s: the front matter is not closed with a --- line' % o.rel)
        o.notes = '\n'.join(lines[n + 1:])
        for k in ('outcome', 'proof', 'in'):
            if not o.f.get(k):
                raise Fail('%s: missing "%s:"' % (o.rel, k))
        return o

    def get(self, k):
        return self.f.get(k, '')

    @property
    def ins(self):
        return split_globs(self.get('in'))

    def covers(self, path):
        return matches(path, self.ins, tree=True)

    @property
    def parked(self):
        return self.get('parked')

    @property
    def skip(self):
        v = self.get('counterfactual')
        return v if v.lower().startswith('skip') else ''

    def save(self):
        for k, v in self.f.items():
            if re.search(r'[\r\n]', v):
                raise Fail('"%s" must be one line (join the steps of a command with &&)' % k)
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.path, 'w', encoding='utf-8') as f:
            f.write('---\n' + ''.join('%s: %s\n' % kv for kv in self.f.items()) + '---\n' + self.notes)


ESCAPE = re.compile(r'(?:^|; )\d{4}-\d{2}-\d{2}: ')  # one entry of the escaped: line, as odd escaped writes it


def escapes(o):
    """How many defects the outcome records as having got past it; a free-text "escaped:" line counts as one."""
    v = o.get('escaped')
    return len(ESCAPE.findall(v)) or (1 if v else 0)


def escape_only(root, base, o):
    """True when the outcome file differs from the base only in its escaped: line. Recording a defect against a
    merged outcome does not put that outcome back in play."""
    r = sh(['git', 'show', '%s:%s' % (base, o.rel)], root) if base else None
    drop = lambda t: re.sub(r'(?m)^escaped:.*\n(?:[ \t]+\S.*\n)*', '', t)  # noqa: E731
    return bool(r) and r.returncode == 0 and drop(r.stdout) == drop(read_text(o.path))


def all_outcomes(root):
    d = odd_dir(root, 'outcomes')
    return [Outcome.load(root, n[:-3]) for n in (sorted(os.listdir(d)) if os.path.isdir(d) else []) if n.endswith('.md')]


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds')


def record(root, slug, **data):
    """Local evidence: a cache for the local gate and a log for `odd stats`. Never committed, never trusted in CI."""
    os.makedirs(state_dir(root, 'evidence'), exist_ok=True)
    with open(state_dir(root, 'evidence', slug + '.jsonl'), 'a') as f:
        f.write(json.dumps(dict(ts=now(), **data)) + '\n')


def evidence(root, slug):
    p, out = state_dir(root, 'evidence', slug + '.jsonl'), []
    if os.path.isfile(p):
        with open(p) as f:
            for line in f:
                try:
                    out.append(json.loads(line))
                except ValueError:
                    pass
    return out


def _state(path):
    """What is at a path right now: None, ['link', target] or ['file', sha256, mode]."""
    if os.path.islink(path):
        return ['link', os.readlink(path)]
    if os.path.isfile(path):
        with open(path, 'rb') as f:
            return ['file', hashlib.sha256(f.read()).hexdigest(), os.stat(path).st_mode & 0o7777]
    return None


def content_hash(root, cfg, o, changed, tests=None):
    """(hash, test files): the identity of what was verified. It covers the proof, the boundary, every changed
    product file inside it, and the test files that had changed when it was verified. A commit, an edit outside
    the boundary, or a test file added later for something else leaves it as it was."""
    _, _, now, product = classify(changed, cfg)
    tests = now if tests is None else tests
    h = hashlib.sha256()
    for k in ('proof', 'in', 'counterfactual'):
        h.update((k + '=' + o.get(k) + '\n').encode())
    for path in sorted(set(tests) | {p for p in product if o.covers(p)}):
        h.update((path + '\0' + json.dumps(_state(os.path.join(root, path))) + '\n').encode(errors='surrogateescape'))
    return h.hexdigest()[:20], sorted(tests)


def fingerprint(root, o, files):
    """The `sealed:` value: `proof@<hash>, <test file>@<hash>, ...`, one short hash of the proof command and of each
    test file as it is now (content, mode, links), so a reviewer sees which files are sealed."""
    h = lambda text: hashlib.sha256(text.encode(errors='surrogateescape')).hexdigest()[:12]  # noqa: E731
    return ', '.join(['proof@' + h(o.get('proof'))] +
                     ['%s@%s' % (p, h(json.dumps(_state(os.path.join(root, p))))) for p in files])


def check_seal(root, o):
    """Fail when the outcome is sealed and its proof command or a sealed test file differs from the seal."""
    if not o.get('sealed'):
        return
    files = [e.rsplit('@', 1)[0] for e in o.get('sealed').split(', ')[1:]]
    now = dict(e.rsplit('@', 1) for e in fingerprint(root, o, files).split(', '))
    was = dict(e.rsplit('@', 1) for e in o.get('sealed').split(', ') if '@' in e)
    if 'proof' not in was:
        raise Fail('%s: "sealed:" is not a seal odd wrote (proof@<hash>, <file>@<hash>, ...); run %s seal %s'
                   % (o.rel, ODD, o.slug))
    moved = ['the proof command' if k == 'proof' else k for k in was if now.get(k) != was[k]]
    if moved:
        raise Fail('the sealed proof changed after it was sealed: %s; reseal it (%s seal %s; the reseal shows in the '
                   'diff) or restore it' % (', '.join(moved), ODD, o.slug))


def standing(root, cfg, o, changed):
    """The latest attempt at this outcome, when it passed on exactly the content that is here now; else None."""
    e = ([x for x in evidence(root, o.slug) if 'ok' in x] or [None])[-1]  # a seal event is not an attempt
    return e if e and e.get('ok') and e.get('hash') == content_hash(root, cfg, o, changed, e.get('tests'))[0] else None


def test_change(root, base, tests, outcomes):
    """(touched, problem or '', what the reviewer reads or ''): test files that existed at the base and this change modified
    or deleted, allowed only by a `test-change: <reason>` line in one of the given (in-play, not parked) outcomes.
    A new test file needs no reason."""
    old = set(zlist(root, 'ls-tree', '-r', '--name-only', '-z', base)) if base else set()
    touched = [p for p in tests if p in old]
    if not touched:
        return touched, '', ''
    named = ', '.join(touched[:8]) + (', ...' if len(touched) > 8 else '')
    why = ['test-change (%s): %s' % (o.slug, o.get('test-change')) for o in outcomes if o.get('test-change')]
    if why:
        return touched, '', '; '.join(why)
    return touched, ('%s existed at the base and %s modified or deleted. A change that edits or deletes an existing test fails '
            'closed: rewriting the test is the easiest way to make a proof pass. If the edit is right, say why in the '
            'outcome with the line "test-change: <reason>"; the gate and the review comment show it.'
            % (named, 'was' if len(touched) == 1 else 'were')), ''


# ---------------------------------------------------------------- proofs, and taking the change out

def run_proof(root, cmd, timeout):
    """(exit code or None on timeout, last lines of output, seconds). The command's exit status is the verdict.
    Output goes to a file, so a process the proof leaves behind cannot hold the check open, and whatever is still
    running in the proof's process group when it ends is stopped. No environment variable marks the run."""
    t0 = time.time()
    with tempfile.TemporaryFile() as out:
        p = subprocess.Popen(cmd, shell=True, cwd=root, stdin=subprocess.DEVNULL, stdout=out, stderr=subprocess.STDOUT,
                             start_new_session=True)
        try:
            rc = p.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            rc = None
        finally:  # also when interrupted: the proof must not be running while the tree is put back
            try:
                os.killpg(p.pid, signal.SIGKILL)
            except OSError:
                pass
            p.wait()
        out.seek(max(0, out.seek(0, 2) - 8000))
        tail = out.read().decode(errors='replace')
    if rc is None:
        tail += '\ntimed out after %ss' % timeout
    return rc, '\n'.join(tail.strip().splitlines()[-20:])[-2000:], round(time.time() - t0, 1)


RUNNERS = re.compile(r'^(python[\d.]*|pypy[\d.]*|(ba|z|da|k)?sh|node|deno|bun|ruby|perl|php|pytest|py\.test|jest|vitest|'
                     r'mocha|rspec|phpunit)$')


def proof_runs(proof, targets):
    """The targets a proof itself runs: its command words, and files or modules handed to an interpreter or a test
    runner. A proof that lives inside the change fails without it for the wrong reason. This reads the command as
    text, so `cd dir && python3 file.py` gets past it (DESIGN.md, limits)."""
    names = set()
    for step in re.split(r'&&|\|\||[;|\n]', proof):
        words = [w.strip('\'"`()') for w in step.split() if not re.match(r'^[A-Za-z_][A-Za-z0-9_]*=', w)]
        words = [w for w in words if w]
        names.update(words[:1])
        if not any(RUNNERS.match(os.path.basename(w)) for w in words):
            continue
        for i, w in enumerate(words[1:], 1):
            if w in ('-c', '-e', '--eval', '-p', '--print'):
                break  # what follows is code, not a file
            w = re.sub(r'::.*$|:\d+$', '', w.split('=', 1)[-1])  # --flag=path, pytest node ids, file:line
            names.add(w)
            if re.match(r'^[A-Za-z_][\w.]*$', w) and ('.' in w or words[i - 1] == '-m'):  # a module: shop.tests.Case
                parts = w.split('.')
                for n in range(1, len(parts) + 1):
                    names.update(['/'.join(parts[:n]) + '.py', '/'.join(parts[:n]) + '/__init__.py'])
    return sorted(set(targets) & {os.path.normpath(w) for w in names if w})


SUMMARY = (  # (runner, how a proof command calls it, the summary line it prints when it completes)
    ('unittest', re.compile(r'(^|\s)-m\s+unittest\b'), re.compile(r'(?m)^Ran \d+ tests? in ')),
    ('pytest', re.compile(r'(^|\s|/)(py\.test|pytest)(\s|$)'), re.compile(r'(?m)(\d+ (passed|failed|skipped|errors?|deselected|xfailed|xpassed)\b.* in [\d.]+s|no tests ran|\[100%\])')),  # -qq in addopts: progress only
    ('go test', re.compile(r'(^|\s|/)go\s+test\b'), re.compile(r'(?m)^(ok|\?|FAIL|PASS)\b')))
QUIET = re.compile(r'(^|\s)(-qq+|-p\s*no:terminal|--json|-json|--reporter\S*|--junit\S*|--result-log\S*)(\s|=|$)')


def hollow(proof, tail, seconds):
    """Why a proof that exited 0 showed nothing, or '': it ran no test, skipped every test it ran, or ended before
    its runner printed the summary it always prints. Read from the proof's own output for unittest, pytest, jest and
    go test; conservative, so a proof it cannot read is never refused (DESIGN.md, section 4)."""
    tail = tail or ''
    m = re.findall(r'(?m)^Ran (\d+) tests? in ([\d.]+)s\s*\n\s*OK(?: \(.*?skipped=(\d+))?', tail)
    if m and m[-1][0] == '0' or re.search(r'(?m)NO TESTS RAN|^no tests ran\b|=+ no tests ran|No tests found, exiting with code 0', tail):
        return 'it ran no test'
    if m and m[-1][2] and m[-1][2] == m[-1][0]:
        return 'it skipped every test it ran (%s)' % m[-1][2]
    pt = re.findall(r'(?m)^=*\s*((?:\d+ \w+(?:, )?)+) in ([\d.]+)s', tail)
    count = lambda text, w: sum(int(n) for n in re.findall(r'(\d+) (?:%s)\b' % w, text))  # noqa: E731
    if pt and count(pt[-1][0], 'skipped') and not count(pt[-1][0], 'passed|xpassed|failed'):
        return 'it skipped every test it ran (%d)' % count(pt[-1][0], 'skipped')
    js = re.findall(r'(?m)^Tests:\s+(.*\btotal)', tail)
    if js and (re.search(r'\b0 total', js[-1]) or count(js[-1], 'skipped') and not count(js[-1], 'passed|failed')):
        return 'it ran no test (jest: Tests: %s)' % js[-1].strip()
    pk = re.findall(r'(?m)^(ok|\?)\s+\S+\s+(.*)$', tail)
    if pk and len(tail.splitlines()) < 20 and all('[no test' in rest for _, rest in pk):
        return 'it ran no test (go: %s)' % pk[-1][1].strip()
    took = [float(t) for _, t, _ in m] + [float(t) for _, t in pt]
    if took and max(took) > seconds + 1:
        return 'its output says the tests took %ss, longer than the whole proof ran (%ss), so a run did not print it' % (
            max(took), seconds)
    if re.search(r'&&|\|\||[;|`\n]|\$\(', proof) or QUIET.search(proof):
        return ''  # several steps, or a runner told not to print its summary: what printed what is not read
    words = ' '.join(w for w in proof.split() if not re.match(r'^[A-Za-z_][A-Za-z0-9_]*=', w))
    for name, call, summary in SUMMARY:
        if call.search(words) and not summary.search(tail):
            return 'it exited 0 before %s printed its summary (for unittest "Ran N tests"), so no test ran to the end' % name
    return ''


def _bump(path, after):
    """A modification time two seconds past anything this run saw, so caches keyed on it (Python bytecode, make)
    notice both the revert and the restore even when size and second are unchanged."""
    t = max(time.time(), after or 0) + 2
    try:
        os.utime(path, (t, t), follow_symlinks=False)
    except (OSError, NotImplementedError):
        pass
    return t


def _prune(root, rel):
    """Remove directories left empty, upwards. Git keeps no empty directory, so neither side of a take-out does."""
    while rel:
        try:
            os.rmdir(os.path.join(root, rel))
        except OSError:
            return
        rel = os.path.dirname(rel)


def _lock(root):
    """One check at a time in a working tree. The kernel drops the lock when its holder ends, however it ends, so a
    journal found while the lock is free belongs to a check that is gone. None when another check holds it."""
    os.makedirs(state_dir(root), exist_ok=True)
    fd = os.open(state_dir(root, 'lock'), os.O_CREAT | os.O_RDWR, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return fd
    except OSError:
        os.close(fd)
        return None


def put_back(root, jdir, j):
    """Undo a take-out from its journal `j`. A path is put back only when it holds what the take-out left there, or
    nothing; anything else was written meanwhile and stays, with the saved version kept beside the journal.
    Returns (paths as they were before the check, descriptions of what was left alone). When a path cannot be
    written the others are still put back, the journal is kept, and CouldNotRun names what is missing."""
    mask = signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGINT, signal.SIGTERM, signal.SIGHUP})  # finish first
    try:
        unsure = [e['path'] for e in j['files'] if 'left' not in e and e['base']]  # killed before noting what it left
        differs = {p for part in chunks(unsure) for p in zlist(root, *DIFF, '--name-only', j['base'], '--', *part)}
        done, left, failed = 0, [], []
        for e in j['files']:
            full, was = os.path.join(root, e['path']), e['was']
            try:
                cur, tmp = _state(full), full + '.odd-putback'
                if cur == was and os.path.lexists(tmp):  # killed before a mutant was moved into place
                    os.remove(tmp)
                if cur != was:
                    as_left = cur == e['left'] if 'left' in e else e['base'] and e['path'] not in differs
                    if cur is not None and not as_left:
                        if was is None:
                            left.append('%s (did not exist before the check; left as it is)' % e['path'])
                            continue
                        keep = os.path.join(os.path.dirname(jdir), 'displaced-' + os.path.basename(jdir), e['path'])
                        os.makedirs(os.path.dirname(keep), exist_ok=True)
                        if was[0] == 'file':
                            shutil.copyfile(os.path.join(jdir, e['saved']), keep)
                        else:
                            with open(keep, 'w') as f:
                                f.write(was[1])
                        left.append('%s (your earlier version is at %s)' % (e['path'], keep))
                        continue
                    if was is None:
                        os.remove(full)
                        _prune(root, os.path.dirname(e['path']))
                    else:  # written beside the path and moved over it, so a kill never leaves half a file
                        os.makedirs(os.path.dirname(full) or '.', exist_ok=True)
                        if os.path.lexists(tmp):
                            os.remove(tmp)
                        if was[0] == 'link':
                            os.symlink(was[1], tmp)
                        else:
                            shutil.copyfile(os.path.join(jdir, e['saved']), tmp)
                            os.chmod(tmp, was[2])
                            _bump(tmp, max(e.get('touched') or 0, os.lstat(full).st_mtime if cur else 0))
                        os.replace(tmp, full)
                done += 1
            except OSError as err:
                failed.append('%s (%s)' % (e['path'], err.strerror or err))
        if failed:
            raise CouldNotRun('these paths could not be put back and hold the version from before your change, or '
                              'nothing: %s. Their saved copies, where they still exist, are in %s. Fix the cause and '
                              'run any odd command to try again, or restore them yourself and delete that directory.'
                              % ('; '.join(failed), jdir))
        shutil.rmtree(jdir, ignore_errors=True)
        return done, left
    finally:
        signal.pthread_sigmask(signal.SIG_SETMASK, mask)


def recover(root):
    """A check that was killed leaves its journal. Put the change back, unless a check is running right now.
    Returns a message when something was put back, so the caller stops and the tree can be looked at."""
    sd = state_dir(root)
    names = [n for n in (sorted(os.listdir(sd)) if os.path.isdir(sd) else []) if n.startswith('cf-')]
    lock = _lock(root) if names else None
    if lock is None:
        return ''
    msgs = []
    try:
        for name in names:
            jdir = os.path.join(sd, name)
            try:
                with open(os.path.join(jdir, 'journal.json')) as f:
                    j = json.load(f)
            except (OSError, ValueError):  # the journal is written before anything is touched: nothing to undo here
                if os.listdir(jdir):
                    os.replace(jdir, os.path.join(sd, 'displaced-' + name))
                    msgs.append('saved copies without a journal were found and kept at %s' % os.path.join(sd, 'displaced-' + name))
                else:
                    os.rmdir(jdir)
                continue
            n, left = put_back(root, jdir, j)
            msgs.append('an earlier check was interrupted while the change was taken out; %d file(s) were put back%s'
                        % (n, ('. Edited meanwhile and left as they are: ' + '; '.join(left)) if left else ''))
    finally:
        os.close(lock)
    return ' '.join(msgs)


def without_change(root, cfg, o, base, targets):
    """Run the proof with `targets` (this outcome's changed product files) taken out, in place, then put them back.
    Returns (exit code or None on timeout, output tail, seconds)."""
    named = proof_runs(o.get('proof'), targets)
    if named:
        raise CouldNotRun('the proof runs %s, which is part of the change and would be taken out by the check. Keep '
                          'what the proof runs under a test path (for example tests/).' % ', '.join(named))
    at_base = (set(zlist(root, 'ls-tree', '-r', '--name-only', '-z', base)) & set(targets)) if base else set()
    for p in targets:  # nothing has been touched yet
        parts = p.split('/')
        for n in range(1, len(parts) + 1):
            full = os.path.join(root, *parts[:n])
            real_dir = os.path.isdir(full) and not os.path.islink(full)
            if real_dir if n == len(parts) else (os.path.lexists(full) and not real_dir):
                raise CouldNotRun('%s: this change turns a directory into a file or a link, or the reverse, or '
                                  'moves a submodule pointer. That cannot be taken out and put back safely: add '
                                  '"counterfactual: skip - <reason>" to the outcome.' % '/'.join(parts[:n]))

    def take_out(entries, save, lock):
        for e in entries:  # removals first, then git writes the base versions (content, mode, links, filters)
            if not e['base'] and e['was']:
                os.remove(os.path.join(root, e['path']))
                _prune(root, os.path.dirname(e['path']))
        for part in chunks([e['path'] for e in entries if e['base']]):
            # git holds the lock too: were odd killed now, nothing would be put back under a git still writing
            r = sh(['git', 'restore', '--source=' + base, '--worktree', '--'] + part, root, pass_fds=[lock])
            if r.returncode != 0:
                raise CouldNotRun('git could not write the base versions (git 2.23 or newer is needed): %s'
                                  % r.stderr.strip()[:200])
        for e in entries:
            full = os.path.join(root, e['path'])
            e['left'] = _state(full)
            if e['left']:
                e['touched'] = _bump(full, e.get('mtime'))
        save()
    return in_place(root, cfg, o, base, targets, at_base, take_out, 'take the change out')


def in_place(root, cfg, o, base, targets, at_base, alter, what):
    """Change `targets` in the working tree with `alter(entries, save, lock)`, run the proof, and put every target
    back from a journal written before the first byte changes (put_back; recover after a kill). Returns (exit code or
    None on timeout, output tail, seconds). `alter` notes in each entry what it `left`, then calls save()."""
    lock = _lock(root)
    if lock is None:
        raise CouldNotRun('another check is taking a change out of this working tree; retry when it ends (and leave '
                          '%s alone meanwhile)' % state_dir(root))
    try:
        jdir = state_dir(root, 'cf-%s-%d' % (o.slug, os.getpid()))
        os.makedirs(jdir)
        entries = []
        for n, p in enumerate(targets):
            full = os.path.join(root, p)
            e = {'path': p, 'base': p in at_base, 'was': _state(full)}
            if e['was'] and e['was'][0] == 'file':
                shutil.copyfile(full, os.path.join(jdir, str(n)))
                e.update(saved=str(n), mtime=os.stat(full).st_mtime)
            entries.append(e)
        journal = {'base': base, 'pid': os.getpid(), 'files': entries}

        def save():
            with open(os.path.join(jdir, 'journal.tmp'), 'w') as f:
                json.dump(journal, f)
                f.flush()
                os.fsync(f.fileno())
            os.replace(os.path.join(jdir, 'journal.tmp'), os.path.join(jdir, 'journal.json'))

        save()  # everything needed to undo is on disk before the first file is touched
        try:
            try:
                alter(entries, save, lock)
            except OSError as err:  # never run a proof on a half-changed tree
                raise CouldNotRun('could not %s (%s); nothing was verified' % (what, err))
            rc, tail, secs = run_proof(root, o.get('proof'), cfg['proof_timeout'])
        finally:
            _, left = put_back(root, jdir, journal)
    finally:
        os.close(lock)
    if left:
        raise CouldNotRun('files changed while the check was running and were left as they are: ' + '; '.join(left))
    return rc, tail, secs


def unrunnable(rc):
    """Timeout, not found, not runnable, or killed by a signal: the proof did not run to completion."""
    return rc is None or rc in (126, 127) or 129 <= rc <= 192 or rc < 0


# ---------------------------------------------------------------- proof strength: small breaks in the changed lines

SWAPS = (  # (pattern, replacement); textual and language-agnostic, applied to code with strings and comments blanked
    (r'(?<![<>=!\-])(?:<=|>=|==|!=|<|>)(?![<>=])', {'<': '<=', '<=': '<', '>': '>=', '>=': '>', '==': '!=', '!=': '=='}),
    (r'&&|\|\|', {'&&': '||', '||': '&&'}),
    (r'\b(?:and|or)\b', {'and': 'or', 'or': 'and'}),
    (r'(?<![+\-=<>!*/%&|^])(?<!\d[eE])[+-](?![+\-=>])', {'+': '-', '-': '+'}),
    (r'\b(?:true|false|True|False|TRUE|FALSE)\b', {'true': 'false', 'false': 'true', 'True': 'False',
                                                    'False': 'True', 'TRUE': 'FALSE', 'FALSE': 'TRUE'}),
    (r'(?<![\w.])(?<!\d[eE][+-])\d+(?![\w.])', None),  # an integer literal, plus one
)


def _code(text):
    """`text` with string literals and comments blanked to spaces, same length and lines. Cheap and approximate:
    quotes, triple quotes, /* */, and # or // or a leading -- to the end of the line. Python's // and a C #define
    are blanked too, which only means fewer mutants."""
    out, i, n, end = [], 0, len(text), None
    while i < n:
        c = text[i]
        if end is None:
            lead = text[text.rfind('\n', 0, i) + 1:i].strip() == ''
            for start, close in (('"""', '"""'), ("'''", "'''"), ('/*', '*/'), ('//', '\n'), ('#', '\n'),
                                 ('"', '"'), ("'", "'"), ('`', '`')) + ((('-- ', '\n'),) if lead else ()):
                if text.startswith(start, i):
                    out.append(' ' * len(start))
                    i, end = i + len(start), close
                    break
            else:
                out.append(c)
                i += 1
        elif end != '\n' and text.startswith(end, i):
            out.append(' ' * len(end))
            i, end = i + len(end), None
        elif c == '\n' and (end == '\n' or len(end) == 1):  # a comment, or an unclosed one-line string, ends here
            out.append(c)
            i, end = i + 1, None
        else:
            skip = 2 if c == '\\' and end in ('"', "'", '`', '"""', "'''") else 1
            out.append(''.join('\n' if x == '\n' else ' ' for x in text[i:i + skip]))
            i += skip
    return ''.join(out)


def mutations(text, lines=None):
    """Every small break of `lines` (1-based; None for all) of `text`: [(line, column, old, new)], in the order of
    the lines, then the column, then SWAPS."""
    out = []
    for n, code in enumerate(_code(text).split('\n'), 1):
        if lines is not None and n not in lines:
            continue
        found = []
        for k, (pat, swap) in enumerate(SWAPS):
            found += [(m.start(), k, m.group(), swap[m.group()] if swap else str(int(m.group()) + 1))
                      for m in re.finditer(pat, code)]
        out += [(n, c, old, new) for c, _, old, new in sorted(found)]
    return out


def pick(items, cap):
    """At most `cap` of `items`, spread evenly over them, always the same ones."""
    return list(items) if len(items) <= cap else [items[i * len(items) // cap] for i in range(cap)]


def changed_lines(root, base, path):
    """The lines of `path` in the working tree that differ from the base; None (all) for a file the base lacks."""
    if not base or sh(['git', 'cat-file', '-e', '%s:%s' % (base, path)], root).returncode != 0:
        return None
    diff = git(root, 'diff', '-U0', '--no-renames', '--no-ext-diff', '--no-textconv', base, '--', path)
    out = set()
    for m in re.finditer(r'^@@ -\S+ \+(\d+)(?:,(\d+))? @@', diff, re.M):
        out.update(range(int(m.group(1)), int(m.group(1)) + int(m.group(2) or 1)))
    return out


def strength(root, cfg, o, base, targets, say=lambda s: None, core=None):
    """Small breaks ("mutants") in the changed lines of this outcome's product files, put in one at a time through
    in_place, each run against the proof. A mutant the proof does not notice survives: a changed line the proof
    does not depend on. One whose run could not run counts as neither (under "enforce" it fails, see weak). Under
    "report", given `core` (the seconds of the three core runs), sampling stops once the breaks have taken about
    that long (at least 2 s), so a slow runner pays about twice the core check, not up to eight times."""
    cands = []
    for p in targets:
        full = os.path.join(root, p)
        if os.path.islink(full) or not os.path.isfile(full):
            continue
        with open(full, 'rb') as f:
            data = f.read()
        try:
            text = data.decode('utf-8')
        except ValueError:
            continue
        if '\0' not in text:
            cands += [(p, data, text) + m for m in mutations(text, changed_lines(root, base, p))]
    picked = pick(cands, cfg['mutants'])
    res = {'mutants': len(picked), 'of': len(cands), 'killed': 0, 'survivors': [], 'unrun': [], 'seconds': 0.0}
    budget = max(sum(core), 2.0) if core and cfg['strength'] == 'report' else None
    if picked:
        say('  proof strength: %d small break(s) in the changed lines, one proof run each, about %s s%s; '
            '"mutants": N in .odd/config.json sets how many' % (len(picked), round(len(picked) * core[0], 1) if core else '?',
                                                                ' (stops after about %s s)' % round(budget, 1) if budget else ''))
    for i, (p, data, text, line, col, old, new) in enumerate(picked):
        if budget is not None and res['seconds'] >= budget:
            res.update(mutants=i, stopped='stopped after %d of %d: the breaks had taken about as long as the core check'
                                          % (i, len(picked)))
            break
        lines = text.split('\n')
        was = lines[line - 1]
        lines[line - 1] = was[:col] + new + was[col + len(old):]
        after = '\n'.join(lines).encode('utf-8')

        def swap_in(entries, save, lock, p=p, data=data, after=after):
            e, full = entries[0], os.path.join(root, p)
            if e['was'] is None or e['was'][0] != 'file' or not _same(full, data):
                raise CouldNotRun('%s changed while the proof-strength check was running; run the command again' % p)
            e['left'] = ['file', hashlib.sha256(after).hexdigest(), e['was'][2]]
            save()  # what will be left is noted first, so a kill at any point is put back
            tmp = full + '.odd-putback'
            with open(tmp, 'wb') as f:
                f.write(after)
            os.chmod(tmp, e['was'][2])
            e['touched'] = _bump(tmp, e.get('mtime'))
            os.replace(tmp, full)
        rc, _, secs = in_place(root, cfg, o, base, [p], set(), swap_in, 'put a mutant in')
        res['seconds'] = round(res['seconds'] + secs, 1)
        where = '%s:%d %s -> %s: %s' % (p, line, old, new, was.strip()[:80])
        if rc == 0:
            res['survivors'].append(where)
        elif unrunnable(rc):
            res['unrun'].append('%s (%s)' % (where, 'timeout' if rc is None else 'exit %d' % rc))
        else:
            res['killed'] += 1
    return res


def _same(path, data):
    with open(path, 'rb') as f:
        return f.read() == data


def weak(cfg, o, res):
    """Under "strength": "enforce" a surviving mutant is a Fail, also for a verification recorded earlier."""
    if cfg['strength'] != 'enforce' or res.get('skip'):
        return
    st = res.get('strength')
    if st is None:
        raise Fail('verified before the proof\'s strength was measured; run: %s done %s' % (ODD, o.slug))
    if st['unrun']:
        raise Fail('%d of %d small break(s) in the changed lines did not run to completion ("strength": "enforce"), so '
                   'they show nothing about the proof; a proof that exits 126, 127, 129-192 or times out under a break '
                   'is not evidence of strength:\n%s\n  make the proof fail with an ordinary exit code (1) when what it '
                   'checks is wrong.' % (len(st['unrun']), st['mutants'], '\n'.join('    ' + w for w in st['unrun'])))
    if st['survivors']:
        raise Fail('the proof does not notice %d of %d small break(s) in the changed lines ("strength": "enforce"); '
                   'each is a changed line the proof does not depend on:\n%s\n  make the proof assert what those '
                   'lines do, or take them out of the change.' % (len(st['survivors']), st['killed'] + len(st['survivors']),
                                                                  '\n'.join('    ' + w for w in st['survivors'])))


def verify(root, cfg, o, base, changed, say=lambda s: None):
    """Green, red with the change taken out, green again. Returns a result dict; raises Fail (the outcome is not
    shown) or CouldNotRun (nothing was established)."""
    check_seal(root, o)
    _, _, _, product = classify(changed, cfg)
    targets = [p for p in product if o.covers(p)]
    lines = sum(sizes(root, base, targets).values())
    rc, tail, s1 = run_proof(root, o.get('proof'), cfg['proof_timeout'])
    if rc is None:
        raise CouldNotRun('the proof timed out (%ss): %s' % (cfg['proof_timeout'], o.get('proof')))
    if rc != 0:
        raise Fail('the proof fails (exit %d): %s\n%s%s' % (rc, o.get('proof'), _indent(tail), (
            '\n  it ran no tests: the runner may be wrong for these tests (pytest exits 5 when it collects none; '
            'unittest finds only unittest.TestCase classes); pick the runner in the proof yourself.')
            if rc == 5 or re.search(r'NO TESTS RAN|no tests ran|collected 0 items|Ran 0 tests', tail or '') else ''))
    empty = hollow(o.get('proof'), tail, s1)
    if empty:
        raise Fail('the proof exited 0 but %s, so it is not a proof: %s\n%s\n  make the proof run the test that shows '
                   'the outcome; a skip, an empty suite or an early exit 0 shows nothing.' % (empty, o.get('proof'), _indent(tail)))
    res = {'files': len(targets), 'lines': lines, 'seconds': [s1], 'red_says': '', 'skip': o.skip}
    if o.skip:
        return res
    if not targets:
        where = 'Globs are separated by commas and relative to the repository root.'
        if base and base == rev(root, 'HEAD'):
            raise Fail('nothing inside "in: %s" differs from %s, the commit you are on, so only uncommitted work is '
                       'measured. %s If the work is already committed here, measure from the commit before it: %s done '
                       '%s --base <revision>. Next time start a branch before the first commit.'
                       % (o.get('in'), base[:10], where, ODD, o.slug))
        raise Fail('nothing inside "in: %s" changed since %s, so the proof cannot be shown to depend on the change. %s '
                   'If this change removes or restructures code and nothing can fail first, add the line '
                   '"counterfactual: skip - <reason>" to %s.' % (o.get('in'), (base or 'the first commit')[:10], where, o.rel))
    say('  proof passed in %ss; two more runs (without the change, then with it again), about %ss' % (s1, round(2 * s1, 1)))
    crc, ctail, s2 = without_change(root, cfg, o, base, targets)
    if crc == 0:
        raise Fail('the proof still passes with the change taken out, so it does not depend on the change.\n'
                   '  taken out: %s\n  usual causes: the proof asserts nothing the change does; the result comes '
                   'from an installed dependency or a cache rather than these files; the test lives in a file that '
                   'was taken out (keep it under a test path); this change removes or restructures code (then add '
                   '"counterfactual: skip - <reason>").' % ', '.join(targets[:8]))
    if unrunnable(crc):
        raise CouldNotRun('with the change taken out the proof did not fail, it could not run (%s). A proof must run '
                          'to completion and exit non-zero.\n%s' % ('timeout' if crc is None else 'exit %d' % crc, _indent(ctail)))
    rc3, tail3, s3 = run_proof(root, o.get('proof'), cfg['proof_timeout'])
    if rc3 != 0:
        raise Fail('the proof passed, failed without the change, and then did not pass again with the change put back '
                   '(%s). A proof must give the same answer each time it runs; this one may leave state behind.\n%s'
                   % ('timeout' if rc3 is None else 'exit %d' % rc3, _indent(tail3)))
    res.update(seconds=[s1, s2, s3], red_says=says(ctail))
    if cfg['strength'] != 'off':
        res['strength'] = strength(root, cfg, o, base, targets, say, [s1, s2, s3])
        weak(cfg, o, res)
    return res


WHY = re.compile(r'Error\b|Exception\b|[Cc]annot |[Aa]ssert|[Ee]xpected|\u2715|\u2717|^not ok|panicked|No such file')


def says(tail):
    """What a failing proof said, in one line: the last line that names a reason (an error, a failed assertion), then
    the runner's last line when that is a different one (so a footer such as jest's "Ran all test suites" never
    stands alone)."""
    lines = [l.strip() for l in (tail or '').splitlines() if l.strip()] or ['(no output)']
    why = [l for l in lines if WHY.search(l)]
    return (why[-1][:120] + ' / ' if why and why[-1] != lines[-1] else '') + lines[-1][:120]


def _indent(text):
    return '\n'.join('    ' + l for l in (text or '').splitlines()[-12:])


def _describe(o, res):
    if res.get('skip'):
        return 'SKIPPED the take-out check (%s): the proof passes; %d line(s) in %d file(s) not verified' % (
            res['skip'].split('-', 1)[-1].strip() or 'no reason', res['lines'], res['files'])
    text = 'took out %d file(s), %d line(s); without them the proof said: %s; %s s' % (
        res['files'], res['lines'], res['red_says'], '+'.join(str(s) for s in res['seconds']))
    st = res.get('strength')
    if st:
        text += '\n          strength: the proof caught %d of %d mutant(s)%s%s; %s s' % (
            st['killed'], st['killed'] + len(st['survivors']),
            ' (%d of %d sampled)' % (st['mutants'], st['of']) if st['of'] > st['mutants'] else '',
            '; %d could not run' % len(st['unrun']) if st['unrun'] else '', st['seconds'])
        text += '\n          ' + st['stopped'] if st.get('stopped') else ''
        text += ''.join('\n          survived: ' + w for w in st['survivors'])
        text += ''.join('\n          could not run: ' + w for w in st['unrun'])
        if st['survivors']:
            text += ('\n          next: add a proof case that tells %s apart from the break, or leave it (reported '
                     'only, unless "strength": "enforce")' % st['survivors'][0].split(' ', 1)[0])
    return text


# ---------------------------------------------------------------- the gate

def survey(root, base_arg=None, recompute=False):
    """Everything the gate and the hooks need to know about the change, computed once."""
    cfg = load_config(root)
    if recompute:  # nothing the change says about itself decides what it is measured from, or by which settings
        base, target = find_base(root, {}, base_arg)
        named = load_config(root, target)['default_branch'] if target else None
        if named and not (base_arg or os.environ.get('ODD_BASE')):
            base, target = find_base(root, {'default_branch': named})
        cfg = load_config(root, target) if target else cfg
        if base and base != rev(root, 'HEAD'):  # there are commits: they are what would be merged
            dirty = set(zlist(root, *DIFF, '--name-only', 'HEAD')) | set(zlist(root, 'ls-files', '--others', '--exclude-standard', '-z'))
            dirty = sorted(p for p in dirty if not matches(p, cfg['exempt']))
            if dirty:
                raise CouldNotRun('--recompute judges what is committed, and %d path(s) here differ from HEAD: %s%s. '
                                  'Commit, stash or ignore them (plain `%s gate` judges work in progress).'
                                  % (len(dirty), ', '.join(dirty[:6]), ', ...' if len(dirty) > 6 else '', ODD))
    else:
        base, _ = find_base(root, cfg, base_arg)
    changed = changed_files(root, base)
    control, exempt, tests, product = classify(changed, cfg)
    inplay = [o for o in all_outcomes(root) if o.rel in changed and not escape_only(root, base, o)]
    active = [o for o in inplay if not o.parked]
    stray = [p for p in product if not any(o.covers(p) for o in active)]
    return dict(cfg=cfg, base=base, changed=changed, control=control, exempt=exempt, tests=tests, product=product,
                inplay=inplay, active=active, stray=stray,
                stray_lines=sum(sizes(root, base, stray, cfg['trivial_lines']).values()))


def gate(root, base_arg=None, recompute=False, say=lambda s: None, facts=None):
    """(exit code, report lines). Raises CouldNotRun. A dict passed as facts is filled with the same result as data,
    for the --json and --summary renderings."""
    s = survey(root, base_arg, recompute)
    cfg, base, changed, product, active, stray = s['cfg'], s['base'], s['changed'], s['product'], s['active'], s['stray']
    lines, problems, skips, outs, exempted = [], [], [], [], []
    facts = {} if facts is None else facts
    facts.update(base=base, recompute=recompute, changed=len(changed), in_play=len(s['inplay']), outcomes=outs,
                 exemptions=exempted, control=s['control'], problems=problems)
    fact = lambda o, state, **k: outs.append(dict(slug=o.slug, outcome=o.get('outcome'), proof=o.get('proof'),  # noqa: E731
                                                  state=state, **k))
    for p in product:  # within one change a file belongs to one outcome
        owners = [o.slug for o in active if o.covers(p)]
        if len(owners) > 1:
            problems.append('%s is inside the boundary of %s: within one change a file belongs to one outcome. Make '
                            'them one outcome, or ship them as successive changes.' % (p, ' and '.join(owners)))
    for o in active:
        try:
            if recompute:
                say('%s: %s' % (o.slug, o.get('proof')))
                res = verify(root, cfg, o, base, changed, say)
            else:
                check_seal(root, o)
                res = standing(root, cfg, o, changed)
                if not res:
                    raise Fail('run: %s done %s' % (ODD, o.slug))
                weak(cfg, o, res)
            if res.get('skip'):
                skips.append('%s - %s, %d line(s)' % (o.slug, res['skip'].split('-', 1)[-1].strip(), res['lines']))
            lines += ['  ok      %s: %s' % (o.slug, o.get('outcome')[:100]), '          ' + _describe(o, res)]
            fact(o, 'ok', **{k: res[k] for k in RESULT if k in res})
        except Fail as e:
            problems.append('%s: %s' % (o.slug, e))
            fact(o, 'fail', why=str(e))
    for o in s['inplay']:
        if o.parked:
            lines.append('  parked  %s: %s (a parked outcome covers no files)' % (o.slug, o.parked))
            fact(o, 'parked', why=o.parked)
    n = s['stray_lines']
    if stray and n > cfg['trivial_lines']:
        un = set(zlist(root, 'ls-files', '--others', '--exclude-standard', '-z'))
        hint = [p for p in stray if p in un]
        problems.append(
            '%s changed line(s) in %d file(s) are outside every outcome (up to %d need none): %s%s\n'
            '    state the outcome in .odd/outcomes/<slug>.md, then run %s done <slug>:\n'
            '      ---\n      outcome: <one sentence: who observes what>\n      proof: <a command that exits 0 only when that is true>\n'
            '      in: %s\n      ---%s'
            % ('a binary file, directory or submodule pointer and other' if n >= BIG else n, len(stray), cfg['trivial_lines'],
               ', '.join(stray[:8]), ', ...' if len(stray) > 8 else '', ODD,
               ', '.join(sorted({p.split('/')[0] + '/**' if '/' in p else p for p in stray})[:6]),
               ('\n    untracked: %s. If that is build output, add it to .gitignore instead.' % ', '.join(hint[:4])) if hint else ''))
    elif stray:
        exempted.append('small-change lane: %d line(s) outside any outcome (%s); the budget is %d'
                        % (n, ', '.join(stray[:5]), cfg['trivial_lines']))
    if s['exempt']:
        exempted.append('exempt paths: %d file(s), %s line(s)' % (
            len(s['exempt']), sum(min(v, 10 ** 5) for v in sizes(root, base, s['exempt']).values())))
    if s['tests']:
        touched, bad, why = test_change(root, base, s['tests'], active)
        exempted.append('test files: %d changed%s%s' % (len(s['tests']), ('; existed before and were modified or deleted: '
                                                                         + ', '.join(touched[:8])) if touched else '',
                                                        '; allowed by ' + why if why else ''))
        problems += [bad] if bad else []
    lines += ['  ' + e for e in exempted]
    exempted += ['skip: ' + k for k in skips]
    if s['control']:
        lines.append('  CONTROL FILES CHANGED (a person must review; in CI the tool and settings are read from the target): '
                     + ', '.join(s['control']))
    head = '%s gate%s: base %s, %d file(s) changed, %d outcome(s) in this change' % (
        ODD, ' --recompute' if recompute else '', (base or 'none')[:10], len(changed), len(s['inplay']))
    tail = ' (%d skipped the take-out check: %s)' % (len(skips), '; '.join(skips)) if skips else ''
    if problems:
        return 1, [head] + lines + ['FAIL' + tail] + ['  ' + p for p in problems]
    return 0, [head] + lines + ['PASS' + tail]


# ---------------------------------------------------------------- commands

# what `--proof auto` picks: (runner, command, the test path when none is given); most specific runner first
PROOFS = (('pytest', 'python3 -m pytest -q {test}', 'tests/test_{name}.py'),
          ('jest', 'npx jest {test}', 'test/{slug}.test.js'),
          ('vitest', 'npx vitest run {test}', 'test/{slug}.test.js'),
          ('node', 'node --test {test}', 'test/{slug}.test.js'),
          ('mocha', 'npx mocha {test}', 'test/{slug}.test.js'),
          ('go', 'go test {dir}', '{name}_test.go'),
          ('cargo', 'cargo test --test {stem}', 'tests/{name}.rs'),
          ('unittest', 'python3 -m unittest -q {test}', 'tests/test_{name}.py'),
          ('make', 'make test', ''))
NO_RUNNER = ('no test runner detected (looked for pytest settings, a conftest.py, pytest in requirements*.txt, *.py '
             'files, a package.json test script running jest, vitest, mocha or node --test, go.mod, Cargo.toml, a '
             'Makefile test target)')


def runners(root):
    """The test runners this repository already uses, each with the file that shows it, most specific first."""
    text = lambda rel: read_text(os.path.join(root, rel)) if os.path.isfile(os.path.join(root, rel)) else ''  # noqa: E731
    try:
        script = str(((json.loads(text('package.json') or '{}').get('scripts') or {}).get('test')) or '')
    except (ValueError, AttributeError):
        script = ''
    files = [p for p in zlist(root, 'ls-files', '-z', '-co', '--exclude-standard') if not p.startswith('.odd/')]
    py = any(p.endswith('.py') for p in files)
    deps = [p for p in files if re.match(r'requirements[^/]*\.txt$', p) and re.search(r'(?im)^pytest\b', text(p))]
    seen = {'pytest': ([r for r, mark in (('pytest.ini', ''), ('pyproject.toml', '[tool.pytest'),
                                           ('tox.ini', '[pytest]'), ('setup.cfg', '[tool:pytest]'))
                        if os.path.isfile(os.path.join(root, r)) and mark in text(r)] +
                       sorted((p for p in files if os.path.basename(p) == 'conftest.py'), key=len) + deps)[:1],
            'go': ['go.mod'] if os.path.isfile(os.path.join(root, 'go.mod')) else [],
            'cargo': ['Cargo.toml'] if os.path.isfile(os.path.join(root, 'Cargo.toml')) else [],
            'unittest': ['*.py files'] if py else [],
            'make': ['Makefile test target'] if any(re.search(r'(?m)^test\s*:', text(m)) for m in ('Makefile', 'makefile', 'GNUmakefile')) else []}
    for js in ('jest', 'vitest', 'mocha'):
        seen[js] = ['package.json test script'] if re.search(r'\b%s\b' % js, script) else []
    seen['node'] = ['package.json test script'] if re.search(r'\bnode\s+--test\b', script) else []
    return [(name, seen[name][0]) for name, _, _ in PROOFS if seen[name]]


def suggest_proof(root, slug, test=None):
    """(the proof command, what was detected and chosen), or (None, why not): never a silent guess."""
    found = runners(root)
    if not found:
        return None, NO_RUNNER
    name, cmd, default = [p for p in PROOFS if p[0] == found[0][0]][0]
    path = test or default.format(slug=slug, name=re.sub(r'[.-]', '_', slug))
    q = shlex.quote if test else (lambda x: x)  # a path from the slug needs no quoting; the init placeholder must stay readable
    proof = cmd.format(test=q(path), dir=q('./' + os.path.dirname(path) if os.path.dirname(path) else '.'),
                       stem=q(os.path.splitext(os.path.basename(path))[0]))
    return proof, 'detected: %s\nproof: %s%s' % (', '.join('%s (%s)' % f for f in found), proof, (
        ' (runs the whole test target: narrow it by hand if the Makefile allows)' if not default else
        '  (the test goes in %s)' % path))


def cmd_new(a, root):
    if not SLUG.match(a.slug):
        raise Fail('slug: lowercase letters, digits, dot, dash, underscore')
    o = Outcome(root, a.slug)
    if os.path.exists(o.path):
        raise Fail('%s exists' % o.rel)
    sentence = ' '.join(a.outcome.split())
    if len(sentence.split()) < 4 or re.search(r'<[^>]+>', sentence):
        raise Fail('the outcome is one full sentence: who observes what result')
    globs = split_globs(','.join(a.in_))
    if not a.proof.strip() or not globs:
        raise Fail('--proof and --in must not be empty')
    if a.test and a.proof.strip() != 'auto':
        raise Fail('--test goes with --proof auto only; the test path is already in your proof command')
    if a.proof.strip() == 'auto':
        a.proof, said = suggest_proof(root, a.slug, a.test)
        if a.proof is None:
            raise Fail('%s.\ngive the command yourself: %s new %s "<outcome>" --proof "<command>" --in "<globs>"' % (said, ODD, a.slug))
        print(said)
    o.f.update([('outcome', sentence), ('proof', a.proof.strip()), ('in', ', '.join(globs))])
    o.save()
    odd_looking = [g for g in globs if re.search(r'[\s{}]', g)]
    print('%s created (paths and the proof are relative to the repository root).%s\n'
          'next: write the proof under a test path, make the change inside "%s", then: %s done %s'
          % (o.rel, ('\nnote: globs are separated by commas and braces are not expanded; "%s" is read as one path.'
                     % odd_looking[0]) if odd_looking else '', o.get('in'), ODD, a.slug))


def cmd_done(a, root):
    o, s = Outcome.load(root, a.slug), survey(root, a.base)
    cfg, base = s['cfg'], s['base']
    try:
        _, bad, _ = test_change(root, base, s['tests'], [o] + [x for x in s['active'] if x.slug != o.slug])
        if bad:
            raise Fail(bad)
        res = verify(root, cfg, o, base, changed_files(root, base), print)
    except Fail as e:
        record(root, a.slug, ok=False, why=str(e)[:300])
        raise
    if o.parked:
        del o.f['parked']
        o.save()
    h, tests = content_hash(root, cfg, o, changed_files(root, base))  # read again: a proof may write files of its own
    record(root, a.slug, ok=True, hash=h, tests=tests, **res)
    print('%s: verified. %s' % (a.slug, _describe(o, res)))
    code, lines = gate(root, a.base)
    print('\n'.join(['', 'the change as a whole:'] + lines))


def cmd_seal(a, root):
    """Red first, recorded: the proof must fail now, before the change; then the proof command and the test files
    changed so far are fingerprinted in the outcome file. Optional; done and the gate check the seal when present."""
    o, cfg = Outcome.load(root, a.slug), load_config(root)
    base, _ = find_base(root, cfg, a.base)
    tests = classify(changed_files(root, base), cfg)[2]
    if not tests:
        raise Fail('no test file has changed since %s, so there is nothing to seal: write the proof as a test under a '
                   'test path first' % (base or 'the first commit')[:10])
    rc, tail, _ = run_proof(root, o.get('proof'), cfg['proof_timeout'])
    if unrunnable(rc):
        raise CouldNotRun('the proof did not run to completion (%s), so it is not red. A proof must run and exit '
                          'non-zero before the change.\n%s' % ('timeout' if rc is None else 'exit %d' % rc, _indent(tail)))
    if rc == 0:
        raise Fail('the proof already passes, so it cannot be sealed red first: %s. Seal it before the change, or '
                   'take the change out first.' % o.get('proof'))
    o.f['sealed'] = fingerprint(root, o, tests)
    o.save()
    record(root, a.slug, seal=o.f['sealed'], base=base, red=says(tail))  # what stats counts as sealed
    print('%s: sealed; the proof fails now (%s). Sealed: %s. Now write the code; a later edit to these files fails '
          '%s done and the gate until it is resealed.' % (a.slug, says(tail),
                                                        ', '.join(tests), ODD))


def cmd_gate(a, root):
    facts = {}
    try:
        code, lines = gate(root, a.base, a.recompute, print, facts)
    except (Fail, CouldNotRun) as e:  # written too, so a reader never mistakes a missing summary for a pass
        bad = isinstance(e, Fail)
        facts.update(exit=1 if bad else 2, verdict='FAIL' if bad else 'COULD NOT RUN',
                     problems=facts.get('problems', []) + [str(e)])
        report(a, facts)
        raise
    facts.update(exit=code, verdict='FAIL' if code else 'PASS')
    report(a, facts)
    print('\n'.join(lines))
    return code


def report(a, facts):
    for path, text in ((a.json, lambda: json.dumps(facts, indent=1, sort_keys=True) + '\n'), (a.summary, lambda: markdown(facts))):
        if path:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(text())


def _cell(text, code=False, table=True):
    """One line of text from the change as inert Markdown: never a link, image, tag or emphasis. In a table cell a
    pipe would end the cell, a newline the row. A code span's fence is one backtick longer than any run inside it."""
    t = ' '.join(str(text).split())
    if not code:
        t = t.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        t = re.sub(r'([\\`*_\[\]])', r'\\\1', t)
    t = t.replace('|', '\\|') if table else t
    if not code or not t:
        return t
    fence = '`' * (max([len(r) for r in re.findall('`+', t)] or [0]) + 1)
    return '%s %s %s' % (fence, t, fence) if '`' in t else '`%s`' % t


def markdown(f):
    """The gate's result for a person reviewing the change: the verdict, then per outcome its sentence, its proof,
    what the proof said with the change taken out and how many small breaks it caught."""
    md = [MARKER, '### odd gate: %s' % f['verdict']] + (['%s base %s, %s file(s) changed, %s outcome(s) in this change.' % (
        'Every proof run again (`--recompute`);' if f['recompute'] else 'Recorded local results;',
        _cell((f['base'] or 'none')[:10], True), f['changed'], f['in_play'])] if 'changed' in f else [])
    outs, survived = f.get('outcomes', []), []
    if outs:
        md += ['', '| outcome | proof | with the change taken out | strength |', '|---|---|---|---|']
    for o in outs:
        st = o.get('strength')
        if o['state'] == 'ok' and o.get('skip'):
            red = 'not taken out (skip: %s); %s line(s) not verified' % (_cell(o['skip'].split('-', 1)[-1]), o.get('lines'))
        elif o['state'] == 'ok':
            red = 'the proof failed: %s (%s file(s), %s line(s))' % (_cell(o.get('red_says') or '(no output)', True),
                                                                  o.get('files'), o.get('lines'))
        else:
            red = '**%s**: %s' % ('not shown' if o['state'] == 'fail' else 'parked',
                                  _cell(o.get('why', '').split('\n')[0][:200]))
        score = '-'
        if st:
            score = 'caught %d of %d' % (st['killed'], st['killed'] + len(st['survivors']))
            score += ''.join('; %d %s' % (len(st[k]), w) for k, w in (('survivors', 'survived'), ('unrun', 'could not run')) if st[k])
            survived += st['survivors']
        md.append('| **%s**: %s | %s | %s | %s |' % (o['slug'], _cell(o.get('outcome') or ''), _cell(o.get('proof') or '', True),
                                                    red, score))
    if survived:
        md += ['', 'Survived (each a changed line the proof does not depend on):'] + ['- ' + _cell(w, True, False) for w in survived]
    if f.get('exemptions'):
        md += ['', '**Exemptions** (passed without verification):'] + ['- ' + _cell(e, table=False) for e in f['exemptions']]
    if f.get('control'):
        md += ['', '**Control files changed** (a person must review): ' + ', '.join(_cell(c, True, False) for c in f['control'])]
    if f.get('problems'):
        md += ['', '**Why it did not pass:**', '', '~~~text'] + [p.replace('~~~', '~ ~ ~') for p in f['problems']] + ['~~~']
    return '\n'.join(md) + '\n'


def cmd_park(a, root):
    if len(a.reason.strip()) < 10:
        raise Fail('give a reason someone else can act on')
    o = Outcome.load(root, a.slug)
    o.f['parked'] = ' '.join(a.reason.split())
    o.save()
    print('%s: parked. This is the expected, correct answer when %s, or when you are blocked: explain why in your '
          'report, plainly. A parked outcome covers no files: remove its changes, with the test that proved it, or move '
          'them to another outcome. The gate fails when more than %d changed line(s) remain outside every outcome. Keep '
          'this file as the record; to resume, delete its "parked:" line.' % (a.slug, PARK_WHEN, load_config(root)['trivial_lines']))


def cmd_escaped(a, root):
    what = ' '.join(a.what.split())
    if len(what) < 10:
        raise Fail('say what went wrong and where it was found, so someone else can reproduce it')
    o = Outcome.load(root, a.slug)
    entry = '%s: %s' % (now()[:10], what)
    o.f['escaped'] = o.get('escaped') + '; ' + entry if o.get('escaped') else entry
    o.save()
    print('%s: escaped defect recorded (%d on this outcome) in %s. Its proof passed and the defect got through.\n'
          'next: prove it. Write a proof that fails on the escaped behaviour now, as a new outcome:\n'
          '  %s new <slug> "<who observes the correct behaviour>" --proof "<command>" --in "<globs>"\n'
          'then %s seal <slug>, fix it, and %s done <slug>. %s stats shows which kinds of proof let defects through.'
          % (a.slug, escapes(o), o.rel, ODD, ODD, ODD, ODD))


def cmd_stats(a, root):
    outs = all_outcomes(root)
    print('self-reported, from this machine only; not a measurement')
    print('%-28s %-8s %9s %8s %8s %-7s %s' % ('outcome', 'state', 'attempts', 'passed', 'escaped', 'sealed', 'strength'))
    kind = {}  # slug -> how strong the latest verification recorded here said the proof was
    for o in outs:
        ev = evidence(root, o.slug)
        seals = [e['seal'] for e in ev if e.get('seal')]
        o.sealed_here = 'sealed' if o.get('sealed') and o.get('sealed') in seals else ('unseen' if o.get('sealed') else '-')
        ev = [e for e in ev if 'ok' in e]  # attempts are done runs; a seal is not one
        st = ([e['strength'] for e in ev if e.get('ok') and e.get('strength')] or [None])[-1]
        n = st and st['killed'] + len(st['survivors'])
        kind[o.slug] = 'survived' if n and st['survivors'] else ('caught' if n else '')
        state = 'parked' if o.parked else ('skip' if o.skip else '')
        print('%-28s %-8s %9d %8d %8d %-7s %s' % (o.slug, state, len(ev), sum(1 for e in ev if e.get('ok')), escapes(o),
                                               o.sealed_here, '%d/%d' % (st['killed'], n) if n else '-'))
    print('%d outcome(s): %d parked, %d skip the take-out check, %d record an escaped defect' % (
        len(outs), sum(1 for o in outs if o.parked), sum(1 for o in outs if o.skip), sum(1 for o in outs if o.get('escaped'))))
    split = lambda name, pick: '%s: %d in %d of %d' % (  # noqa: E731
        name, sum(escapes(o) for o in outs if pick(o)), sum(1 for o in outs if pick(o) and escapes(o)),
        sum(1 for o in outs if pick(o)))
    print('escaped defects (self-reported): %d against %d of %d outcome(s)' % (
        sum(escapes(o) for o in outs), sum(1 for o in outs if escapes(o)), len(outs)))
    print('  ' + '; '.join([split('sealed', lambda o: o.sealed_here == 'sealed'),
                            split('not sealed', lambda o: o.sealed_here != 'sealed')]))
    print('  ' + '; '.join([split('skipped the take-out check', lambda o: o.skip), split('checked', lambda o: not o.skip)]))
    print('  ' + '; '.join([split('strength, every mutant caught', lambda o: kind[o.slug] == 'caught'),
                            split('a mutant survived', lambda o: kind[o.slug] == 'survived'),
                            split('not measured here', lambda o: not kind[o.slug])]))


# when parking is the answer: the method, `odd park` and the Stop hook say it in the same words (ImpossibleBench's
# strict stop-and-explain wording plus an abort path cut cheating; docs/evidence/14-research.md section 2.3)
PARK_WHEN = 'the task cannot be done as asked or the proof cannot honestly pass'
METHOD = '''## Outcome-driven development (odd)

Work here is done when a proof says so, not when it looks finished. `odd` below means `python3 .odd/odd.py`.

For any change of more than a few lines, on a branch of its own:

1. State the outcome before writing code: one sentence saying who observes what, a command that exits 0 only when
   that is true, and the files the change may touch. If the request is unclear, ask (at most five questions)
   instead of guessing.
   `odd new <slug> "<outcome>" --proof "<command>" --in "<globs, comma-separated, relative to the repository root>"`
2. Write the proof as a test in a file of its own under a test path (`tests/`, `test_*.py`, `*_test.*`, `*.test.*`,
   `*.spec.*`). Make it the narrowest command that shows the outcome, not the whole suite. Recommended: run
   `odd seal <slug>` now, before the code; it checks the proof fails and fingerprints the test, so changing the test
   later fails `done` until it is resealed, and the reseal shows in review.
3. Make the change, staying inside the files the outcome names. If more are needed, add them to `in:` in
   `.odd/outcomes/<slug>.md`. Work that is not part of this outcome is a later outcome.
4. Finish with `odd done <slug>`, then `odd gate`. `done` passes only when the proof passes, fails with your change
   taken out, and passes again. Report the work as done only when both exit 0, and report what they printed.
5. When you are blocked, or {park_when}
   (a test contradicts the outcome, or a pass would take special-casing the test's inputs or editing, weakening or
   deleting a test), STOP and explain: run `odd park <slug> "<why>"`, say why in your report, and take the attempt
   out again. Parking is then the expected, correct answer, not a failure. A forced pass is the wrong answer, even
   when it turns the gate green.

Small edits (up to {trivial} changed lines) need no outcome. If a command can answer a question, run the command.
Decisions only the owner can make (credentials, billing, deploys, releases, deleting data, relaxing a check) go to
the owner; decide the rest yourself and note why in the outcome file. Do not edit `.odd/odd.py` or
`.odd/config.json`.
'''.replace('{park_when}', PARK_WHEN)
BEGIN, END = '<!-- odd:begin -->', '<!-- odd:end -->'
CI_HELP = '''
To make the gate count, add it as the last step of your existing test job. On GitHub Actions, one step:

  - uses: varunkan/ODD-Outcome-Driven-Development@v%s

Elsewhere (full history, not a depth-1 checkout):

  git show "refs/remotes/origin/$TARGET:.odd/odd.py" > "$TMP/odd.py" 2>/dev/null || cp .odd/odd.py "$TMP/odd.py"
  python3 "$TMP/odd.py" gate --recompute --base "refs/remotes/origin/$TARGET"

CI is the authority only when (1) that step is a required check on the target branch, (2) .odd/odd.py,
.odd/config.json and the CI configuration cannot change without a person's review, and (3) the agent cannot merge
or push to the target branch. Otherwise the gate is advice. Without CI, fetch the target branch and run
`%s gate --recompute --base <target branch>` on the committed work before merging.'''
HOOK = 'python3 "$(git rev-parse --show-toplevel 2>/dev/null)/.odd/odd.py" hook %s 2>/dev/null || true'
HOOKS = (('Stop', 'stop'), ('SessionStart', 'session-start'), ('UserPromptSubmit', 'prompt-submit'))


def read_json(path):
    try:
        return json.loads(read_text(path)) if os.path.isfile(path) else {}
    except ValueError as e:
        raise CouldNotRun('%s is not valid JSON (%s): fix it or move it aside, then run init again' % (path, e))


def write_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)
        f.write('\n')


def mcp_settings(path):
    """The project's .mcp.json with odd's server added and every other server left exactly as it is."""
    s = read_json(path)
    servers = s.setdefault('mcpServers', {}) if isinstance(s, dict) else None
    if not isinstance(servers, dict):
        raise CouldNotRun('%s: "mcpServers" is not an object; fix it by hand, then run init again' % path)
    servers['odd'] = {'command': 'python3', 'args': ['.odd/odd_mcp.py']}
    return s


def hook_settings(path):
    """The person's .claude/settings.local.json with odd's hooks added and their own left exactly as they are."""
    s = read_json(path)
    hooks = s.setdefault('hooks', {}) if isinstance(s, dict) else None
    if not isinstance(hooks, dict):
        raise CouldNotRun('%s: "hooks" is not an object; fix it by hand, then run init again' % path)
    for event, arg in HOOKS:
        groups = hooks.get(event, [])
        if not isinstance(groups, list) or not all(isinstance(g, dict) and isinstance(g.get('hooks', []), list) for g in groups):
            raise CouldNotRun('%s: hooks.%s is not a list of hook groups; fix it by hand, then run init again' % (path, event))
        mine = lambda h: isinstance(h, dict) and '/.odd/odd.py" hook ' in str(h.get('command'))  # noqa: E731
        kept = [dict(g, hooks=[h for h in g.get('hooks', []) if not mine(h)]) for g in groups]
        hooks[event] = [g for g in kept if g['hooks']] + [{'hooks': [{'type': 'command', 'command': HOOK % arg, 'timeout': 60}]}]
    return s


def cmd_init(a, root):
    cfg = load_config(root)  # everything is read and checked before anything is written
    agents = os.path.join(root, 'AGENTS.md')
    old = read_text(agents) if os.path.isfile(agents) else ''
    claude = [r for r in ('CLAUDE.md', os.path.join('.claude', 'CLAUDE.md'), 'CLAUDE.local.md')
              if os.path.isfile(os.path.join(root, r)) and os.path.realpath(os.path.join(root, r)) != os.path.realpath(agents)]
    texts = {r: read_text(os.path.join(root, r)) for r in claude}
    sp = os.path.join(root, '.claude', 'settings.local.json')
    settings = hook_settings(sp) if a.claude_hooks else None
    mp, server = os.path.join(root, '.mcp.json'), os.path.join(os.path.dirname(os.path.abspath(__file__)), 'odd_mcp.py')
    servers = mcp_settings(mp) if a.mcp else None
    if a.mcp and not os.path.isfile(server):
        raise CouldNotRun('odd_mcp.py is not beside %s: put it there (it ships with odd), then run init --mcp again'
                          % os.path.abspath(__file__))
    proof = suggest_proof(root, '<slug>')[1]

    os.makedirs(odd_dir(root, 'outcomes'), exist_ok=True)
    cp = odd_dir(root, 'config.json')
    if not os.path.isfile(cp):
        with open(cp, 'w') as f:
            json.dump(DEFAULTS, f, indent=1)
            f.write('\n')
    # fixed names: hooks, the method and the CI step all run .odd/odd.py, whatever the copy run here is called
    for me, name in [(os.path.abspath(__file__), 'odd.py')] + ([(server, 'odd_mcp.py')] if a.mcp else []):
        mine = odd_dir(root, name)
        if not (os.path.exists(mine) and os.path.samefile(me, mine)):
            shutil.copyfile(me, mine)
    did = ['.odd/odd.py and .odd/config.json (control files: changes to them need a person\'s review)']
    block = BEGIN + '\n' + METHOD.replace('{trivial}', str(cfg['trivial_lines'])).rstrip('\n') + '\n' + END
    if BEGIN in old and END in old:
        new = old[:old.index(BEGIN)] + block + old[old.index(END) + len(END):]
    else:
        new = block + '\n' + ('\n' + old if old.strip() else '')
    with open(agents, 'w', encoding='utf-8') as f:
        f.write(new)
    did.append('AGENTS.md: the method (read by Codex, Cursor, Copilot in VS Code, Claude Code, Junie, Windsurf)')
    imported = False  # Claude Code reads any of these three in place of AGENTS.md, so one of them must import it
    for rel in claude:
        imp = '@' + os.path.relpath(agents, os.path.dirname(os.path.join(root, rel))).replace(os.sep, '/')
        lines = [l for l in texts[rel].split('\n') if imp == '@AGENTS.md' or l.strip() != '@AGENTS.md']  # one that led nowhere
        if not imported and imp not in [l.strip() for l in lines]:
            lines = '\n'.join(lines).rstrip('\n').split('\n') + ['', imp, '']
        imported = imported or imp in [l.strip() for l in lines]
        if '\n'.join(lines) != texts[rel]:
            with open(os.path.join(root, rel), 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines))
    if claude:
        did.append('%s imports AGENTS.md (Claude Code reads that file in place of AGENTS.md)' % claude[0])
    if servers is not None:
        write_json(mp, servers)
        did.append('.mcp.json: the odd MCP server (.odd/odd_mcp.py, a control file), tools new, seal, done, gate, park, '
                   'escaped; other servers kept')
    if settings is not None:
        write_json(sp, settings)
        ex = os.path.join(root, git(root, 'rev-parse', '--git-path', 'info/exclude').strip())
        have = read_text(ex) if os.path.isfile(ex) else ''
        if '.claude/settings.local.json' not in have:
            os.makedirs(os.path.dirname(ex), exist_ok=True)
            with open(ex, 'a') as f:
                f.write(('' if have.endswith('\n') or not have else '\n') + '.claude/settings.local.json\n')
        did.append('.claude/settings.local.json: three Claude Code hooks for this machine only (not committed)')
    log = state_dir(root, 'hook-errors.log')
    if os.path.isfile(log) and os.path.getsize(log):
        did.append('WARNING: the editor hooks failed %d time(s): see %s' % (sum(1 for _ in open(log)), log))
    try:
        find_base(root, cfg)
    except CouldNotRun as e:
        did.append('NOTE: %s' % e)
    print('odd %s is set up:\n  ' % VERSION + '\n  '.join(did))
    print(CI_HELP % (VERSION, ODD))
    print('\nstart: %s new <slug> "<outcome>" --proof "<command>" --in "<globs>"' % ODD)
    print('proof suggestion (--proof auto): ' + proof.replace('\n', '; '))


# ---------------------------------------------------------------- opt-in Claude Code hooks (internal)

def cmd_hook(a, root):
    try:
        ev = json.load(sys.stdin)
    except ValueError:
        ev = {}
    sid = re.sub(r'[^A-Za-z0-9_-]', '', str(ev.get('session_id') or ev.get('conversation_id') or 'x'))[:64]
    os.makedirs(state_dir(root), exist_ok=True)
    fp_path = state_dir(root, 'turn-%s.fp' % sid)
    msg = recover(root) if a.event != 'prompt-submit' else ''
    try:
        s = survey(root)
    except CouldNotRun:
        s = None  # no target branch to measure from: nothing to say
    # what the change is right now: every changed path and what it holds; staging or committing alters nothing here
    fp = hashlib.sha256(json.dumps([[p, _state(os.path.join(root, p))] for p in s['changed']]).encode()).hexdigest() if s else ''
    before = read_text(fp_path) if os.path.isfile(fp_path) else None
    if a.event != 'session-start' or ev.get('source') != 'compact':
        with open(fp_path, 'w') as f:
            f.write(fp)
    if a.event == 'prompt-submit':
        return  # only marks where the turn starts: what the person changed between turns is not the agent's turn
    if a.event == 'session-start':
        if msg or (s and s['inplay']):
            print('odd: ' + (msg + '. ' if msg else '') + '; '.join(
                '%s %s' % (o.slug, 'parked' if o.parked else 'in this change') for o in (s['inplay'] if s else [])))
        return
    if ev.get('stop_hook_active') or (ev.get('loop_count') or 0) >= 1:  # never blocks twice in a row
        if msg:
            print(json.dumps({'systemMessage': 'odd: ' + msg + '. Check the working tree.'}))
        return
    if msg:
        print(json.dumps({'decision': 'block', 'reason': 'odd: ' + msg + '. Check the working tree before ending the turn.'}))
        return
    if not s or before == fp:
        return  # this turn changed no files: a question or a discussion is never blocked
    cfg, changed, n = s['cfg'], s['changed'], s['stray_lines']
    tried = {o.slug: evidence(root, o.slug) for o in s['active']}
    stale = [o.slug for o in s['active'] if any(e.get('ok') for e in tried[o.slug]) and not standing(root, cfg, o, changed)]
    run = 'python3 .odd/odd.py'
    if stale:
        print(json.dumps({'decision': 'block', 'reason': 'odd: %s was verified and its files have changed since, or its '
                          'latest check failed. Run `%s done %s` again, or, if %s, STOP and explain (`%s park %s "<why>"`).'
                          % (', '.join(stale), run, stale[0], PARK_WHEN, run, stale[0])}))
    elif not s['inplay'] and n > cfg['trivial_lines']:
        print(json.dumps({'decision': 'block', 'reason': 'odd: this turn left %d changed line(s) with no outcome. State '
                          'the outcome (`%s new <slug> "<outcome>" --proof "<command>" --in "<globs>"`) and verify it '
                          '(`%s done <slug>`), or, if %s, STOP and explain (`%s park <slug> "<why>"`): that is the '
                          'expected answer then, not a failure.' % (n, run, run, PARK_WHEN, run)}))
    else:
        notes = ['not verified yet: ' + ', '.join(o.slug for o in s['active'] if not any(e.get('ok') for e in tried[o.slug]))]
        if not s['active'] and n > cfg['trivial_lines']:
            notes = ['%d changed line(s) are outside every outcome and the outcome in this change is parked: remove them '
                     'or move them to another outcome, or the gate fails' % n]
        if notes[0] != 'not verified yet: ':
            print(json.dumps({'systemMessage': 'odd: ' + notes[0]}))


def main(argv=None):
    global ODD
    p = argparse.ArgumentParser(prog='odd', description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--version', action='version', version='odd ' + VERSION)
    sub = p.add_subparsers(dest='cmd', required=True)
    s = sub.add_parser('init')
    s.add_argument('--claude-hooks', action='store_true')
    s.add_argument('--mcp', action='store_true', help='also install the MCP server and add it to .mcp.json')
    s = sub.add_parser('new')
    s.add_argument('slug')
    s.add_argument('outcome')
    s.add_argument('--proof', required=True, help='a command that exits 0 only when the outcome holds, or "auto": '
                   'one picked from the test runner the repository uses')
    s.add_argument('--test', metavar='PATH', help='with --proof auto: the test file the proof runs')
    s.add_argument('--in', dest='in_', required=True, action='append', help='globs, comma-separated (may be repeated)')
    s = sub.add_parser('seal')
    s.add_argument('slug')
    s.add_argument('--base', help='measure from this revision instead of the target branch')
    s = sub.add_parser('done')
    s.add_argument('slug')
    s.add_argument('--base', help='measure from this revision instead of the target branch')
    s = sub.add_parser('gate')
    s.add_argument('--base')
    s.add_argument('--recompute', action='store_true')
    s.add_argument('--summary', metavar='FILE', help='also write the result as Markdown, for a pull request')
    s.add_argument('--json', metavar='FILE', help='also write the result as JSON')
    s = sub.add_parser('park')
    s.add_argument('slug')
    s.add_argument('reason')
    s = sub.add_parser('escaped')
    s.add_argument('slug')
    s.add_argument('what', help='what went wrong, and where it was found')
    sub.add_parser('stats')
    sub.add_parser('hook').add_argument('event', choices=[arg for _, arg in HOOKS])
    a = p.parse_args(argv)
    if os.path.basename(sys.argv[0]) == 'odd.py':
        rel = os.path.relpath(os.path.abspath(sys.argv[0]))
        ODD = 'python3 ' + (rel if not rel.startswith('..') else sys.argv[0])
    if a.cmd == 'hook':  # a hook must never strand a session: any error passes, and `odd init` reports it
        root = None
        try:
            root = find_root()
            cmd_hook(a, root)
        except Exception as e:
            try:
                os.makedirs(state_dir(root), exist_ok=True)
                with open(state_dir(root, 'hook-errors.log'), 'a') as f:
                    f.write('%s %s %r\n' % (now(), a.event, e))
            except Exception:
                pass
        return 0
    for name in ('SIGTERM', 'SIGHUP'):  # so an interrupted check still puts the change back before exiting
        if hasattr(signal, name):
            signal.signal(getattr(signal, name), lambda *_: sys.exit(143))
    try:
        if fcntl is None:
            raise CouldNotRun('odd needs a POSIX system (Linux, macOS, or WSL on Windows)')
        root = find_root()
        msg = recover(root)
        if msg:
            raise CouldNotRun(msg + '. Look at your working tree, then run the command again.')
        return globals()['cmd_' + a.cmd](a, root) or 0
    except Fail as e:
        print('odd: ' + str(e), file=sys.stderr)
        return 1
    except CouldNotRun as e:
        print('odd: could not run: ' + str(e), file=sys.stderr)
        return 2
    except Exception as e:  # nobody planned for this: nothing was established, and that is not a "fail"
        if os.environ.get('ODD_DEBUG'):
            traceback.print_exc()
        here = [f.lineno for f in traceback.extract_tb(e.__traceback__) if f.filename == __file__] or [0]
        print('odd: could not run: %s: %s (odd.py line %d; set ODD_DEBUG=1 for the trace)' % (type(e).__name__, e, here[-1]),
              file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
