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
  odd race <slug> [--n N] [--agent CMD] [--base REF]      N agent attempts in worktrees; the proof picks the winner
  odd cascade <slug> [--agents C1,C2] [--race N]          agents in order, cheapest first; escalate until one is proven
  odd chain <ticket> [--race N] [--cascade]               .odd/chains/<ticket>.md: each outcome proven, checkpointed
  odd spec <slug> --proof-by CMD [--tries N]              another agent writes only the proof; sealed red first
  odd gate [--base REF] [--recompute]                     exit 0 pass, 1 fail, 2 could not run
  odd park <slug> "<reason>"                              blocked, or cannot be done as specified
  odd escaped <slug> "<what went wrong, where found>"     a defect got past this outcome; record it
  odd stats                                               counts (self-reported)

Needs a POSIX system, git 2.23+ and Python 3.8+. One file, standard library only, so a project vendors it as
.odd/odd.py. Design and limits: DESIGN.md.
"""
import argparse
import ast
import collections
import datetime
import hashlib
import json
import os
import queue
import re
import shlex
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
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
    'agents': [],          # odd race: agent commands, one per attempt in turn; {prompt_file} is the prompt's path, else stdin
    'race_timeout': 1800,  # odd race: seconds an attempt's agent may run before it is killed with its process group
    'race_seal': False,    # odd race: refuse an outcome that is not sealed
    'proof_tries': 3,      # odd spec: tries for the proof author to write a proof that fails before the code
    'coverage': 'report',  # requirements no outcome in the change covers: off, report, or enforce (an uncovered one fails)
    'ambiguity_stop': True,  # odd new refuses an outcome sentence with no observable (an English word list)
    'guard': 'enforce',    # earlier merged outcomes whose in: holds a touched file: proofs run again (off, report, enforce)
    'auto_lane': False,    # odd gate says "lane": "auto" or "review" (backlog item 11); odd itself never merges
    'auto_min_strength': 1.0,  # the auto lane: least share k/n of small breaks each outcome's proof must catch
    'auto_max_lines': 120,     # the auto lane: most changed product lines
}
CONTROL = ('.odd/odd.py', '.odd/config.json', '.odd/odd_mcp.py')  # no outcome needed; always reported; the first two read from the target in CI
FIELDS = ('outcome', 'proof', 'in', 'counterfactual', 'parked', 'escaped', 'sealed', 'test-change', 'proof-by', 'covers', 'kind', 'asked')
KINDS = ('bug', 'feature', 'refactor')  # kind: bug, the proof must fail at the base revision (reproduce first)
REFACTOR_SKIP = 'skip - behaviour-preserving refactor'  # backlog item 7: what `new --kind refactor` records
HINTS = {  # backlog item 7: printed by `new --kind <kind>` after the outcome file is written
    'bug': 'reproduce first: write the proof so it fails on the current code the way the ticket describes; seal and '
           'done require it to fail at the base revision and refuse "counterfactual: skip". Then fix.',
    'feature': 'the proof covers the new behaviour: a test that fails without the change and passes with it; keep the '
               'existing suite green as well (run it before done; the proof alone does not).',
    'refactor': 'the existing suite is the proof: behaviour must not change, so the take-out check is skipped '
                '(counterfactual: %s) and done passes when the suite passes; an edit of an existing test is refused '
                'unless explained, so do not change the tests to fit.' % REFACTOR_SKIP}
SLUG = re.compile(r'^[a-z0-9][a-z0-9._-]{0,63}$')
BIG = 10 ** 6  # a binary file or submodule pointer is never a "small change"
WIDE = 120     # bytes that count as one line in the small-change lane
MARKER = '<!-- odd-gate -->'  # finds the pull-request comment of an earlier run, so there is only ever one
RESULT = ('files', 'lines', 'seconds', 'red_says', 'skip', 'strength')  # what --json says of a verified outcome
ODD = 'odd'    # how the tool was invoked, for messages a reader can paste


class Fail(Exception):
    """The outcome is not shown (exit 1). `items`: (kind, text) pairs an agent can act on, for the "next:" block."""

    def __init__(self, msg, items=()):
        Exception.__init__(self, msg)
        self.items = list(items)


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
            'strength': lambda v: v in ('off', 'report', 'enforce'), 'mutants': lambda v: type(v) is int and v >= 0,
            'agents': lambda v: isinstance(v, list) and all(isinstance(c, str) and c.strip() for c in v),
            'race_timeout': lambda v: type(v) in (int, float) and 0 < v < float('inf'),
            'race_seal': lambda v: type(v) is bool,
            'proof_tries': lambda v: type(v) is int and 1 <= v <= 32,
            'coverage': lambda v: v in ('off', 'report', 'enforce'),
            'ambiguity_stop': lambda v: type(v) is bool,
            'guard': lambda v: v in ('off', 'report', 'enforce'),
            'auto_lane': lambda v: type(v) is bool,
            'auto_min_strength': lambda v: type(v) in (int, float) and 0 <= v <= 1,
            'auto_max_lines': lambda v: type(v) is int and v >= 0}


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


COLLECT = re.compile(r'(^|/)(conftest\.py|pytest\.ini)$')  # pytest reads these to decide which tests run
SECTIONS = {'pyproject.toml': r'\[tool\.pytest', 'setup.cfg': r'\[(tool:)?pytest\]', 'tox.ini': r'\[pytest\]'}


def classify(changed, cfg):
    """(control, exempt, tests, product) — each changed path falls in exactly one. A conftest.py or pytest.ini
    counts as a test file: it decides which tests run."""
    control = [p for p in changed if p in CONTROL]
    exempt = [p for p in changed if p not in CONTROL and matches(p, cfg['exempt'])]
    tests = [p for p in changed if p not in control and p not in exempt and
             (matches(p, cfg['test_globs']) or COLLECT.search(p))]
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
        if o.get('kind') and o.get('kind') not in KINDS:
            raise Fail('%s: unknown kind "%s" (the kinds are: %s)' % (o.rel, o.get('kind'), ', '.join(KINDS)))
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
    def asked(self):
        return self.get('asked')

    @property
    def bug(self):
        return self.get('kind') == 'bug'

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


# ---------------------------------------------------------------- requirement coverage (backlog item 4)

REQ_FILE = re.compile(r'^\.odd/requirements/([A-Za-z0-9][A-Za-z0-9._-]{0,63})\.md$')
REQ_LINE = re.compile(r'^\s*(?:[-*]\s+)?(R\d+)\s*:\s*(\S.*)$')   # "R1: ...", also as a list item
COVER_ID = re.compile(r'^(?:([A-Za-z0-9][A-Za-z0-9._-]{0,63}):)?(R\d+)$')  # R1, or <ticket>:R1


def cover_ids(value):
    """The ids a covers: value names, as (ticket or None, id); a malformed one raises Fail."""
    out = []
    for item in split_globs(value):
        m = COVER_ID.match(item)
        if not m:
            raise Fail('covers: %r is not a requirement id (R<number>, or <ticket>:R<number> naming '
                       '.odd/requirements/<ticket>.md)' % item)
        out.append(m.groups())
    return out


def requirements(root, ticket, at=None):
    """{id: text} from .odd/requirements/<ticket>.md, in file order (at a revision when `at` is given; None when
    the file is not there). A repeated id raises Fail."""
    rel = '.odd/requirements/%s.md' % ticket
    if at:
        r = sh(['git', 'show', '%s:%s' % (at, rel)], root)
        if r.returncode:
            return None
        text = r.stdout
    elif os.path.isfile(os.path.join(root, rel)):
        text = read_text(os.path.join(root, rel))
    else:
        return None
    reqs = collections.OrderedDict()
    for line in text.split('\n'):
        m = REQ_LINE.match(line)
        if m and m.group(1) in reqs:
            raise Fail('%s: %s is listed twice; number each requirement once' % (rel, m.group(1)))
        if m:
            reqs[m.group(1)] = m.group(2).strip()
    return reqs


def coverage(root, s):
    """(report lines, problems, facts) for the requirements of the tickets this change records: each id in a
    changed .odd/requirements/<ticket>.md and the outcomes in the change that cover it. A covers: id that names no
    requirement is always a problem; an uncovered requirement is one only under "coverage": "enforce"."""
    mode = s['cfg']['coverage']
    if mode == 'off':
        return [], [], []
    tickets = [m.group(1) for m in map(REQ_FILE.match, s['changed']) if m]
    lists, problems = collections.OrderedDict(), []
    for t in tickets:
        try:
            reqs = requirements(root, t)
        except Fail as e:
            problems.append(str(e))
            continue
        if reqs is None:  # deleted in this change
            continue
        if not reqs:
            problems.append('.odd/requirements/%s.md has no "R<number>: ..." lines; write one requirement per line '
                            '(R1: ..., R2: ...)' % t)
            continue
        lists[t] = reqs
    who = {t: collections.OrderedDict((r, []) for r in reqs) for t, reqs in lists.items()}
    for o in s['inplay']:
        try:
            ids = cover_ids(o.get('covers'))
        except Fail as e:
            problems.append('%s: %s' % (o.slug, e))
            continue
        for t, r in ids:
            if t is None and len(lists) != 1:
                problems.append('%s: covers: %s %s' % (o.slug, r, 'is ambiguous: this change has requirements for %s; '
                                'write <ticket>:%s' % (' and '.join(lists), r) if lists else
                                'names a requirement, but this change has no .odd/requirements/<ticket>.md; add it, '
                                'or write <ticket>:%s for a ticket recorded earlier' % r))
                continue
            t = t or list(lists)[0]
            if t not in lists:  # a ticket recorded in an earlier change: read as it is now, counted for nothing
                try:
                    reqs = requirements(root, t)
                except Fail:
                    reqs = None
                if not reqs or r not in reqs:
                    problems.append('%s: covers: %s:%s, but %s' % (o.slug, t, r, '.odd/requirements/%s.md has no %s'
                                    % (t, r) if reqs else 'there is no .odd/requirements/%s.md' % t))
                continue
            if r not in lists[t]:
                problems.append('%s: covers: %s, but .odd/requirements/%s.md has no %s (it has %s)'
                                % (o.slug, r, t, r, ', '.join(lists[t])))
            elif not o.parked and not o.asked and o.slug not in who[t][r]:  # a parked or asked outcome covers nothing
                who[t][r].append(o.slug)
    lines, facts = [], []
    for t, reqs in lists.items():
        missing = [r for r, slugs in who[t].items() if not slugs]
        try:
            was = (requirements(root, t, s['base']) if s['base'] else None) or {}
        except Fail:
            was = {}
        dropped = [r for r in was if r not in reqs]
        lines.append('  requirements %s: %d of %d covered%s%s' % (
            t, len(reqs) - len(missing), len(reqs),
            '; not covered: ' + ', '.join('%s (%s)' % (r, reqs[r][:80]) for r in missing) if missing else '',
            '; removed in this change: ' + ', '.join(dropped) if dropped else ''))
        if mode == 'enforce':
            problems += ['%s %s is covered by no outcome in this change: %s. Cover it (an outcome with covers: %s, '
                         '%s new ... --covers %s), or take it out of .odd/requirements/%s.md if it is not part of '
                         'this ticket.' % (t, r, reqs[r][:120], r, ODD, r, t) for r in missing]
        facts.append(dict(ticket=t, covered={r: v for r, v in who[t].items() if v}, uncovered=missing, removed=dropped,
                          text=dict(reqs)))
    return lines, problems, facts


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds')


def record(root, slug, **data):
    """Local evidence: a cache for the local gate and a log for `odd stats`. Never committed, never trusted in CI."""
    os.makedirs(state_dir(root, 'evidence'), exist_ok=True)
    with open(state_dir(root, 'evidence', slug + '.jsonl'), 'a') as f:
        f.write(json.dumps(dict(ts=now(), **data)) + '\n')


def _kind(o):
    """The kind an attempt ran under, for the evidence log: the gate says when a bug outcome later changed kind."""
    return {'kind': o.get('kind')} if o.get('kind') else {}


def was_bug(root, o):
    """True when this outcome is not kind: bug now but an earlier done or seal here ran it as one (local evidence)."""
    return not o.bug and any(e.get('kind') == 'bug' for e in evidence(root, o.slug))


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
                     ['%s@%s' % (p, h(json.dumps(_state(os.path.join(root, p))))) for p in files] +
                     (['kind@' + o.get('kind')] if o.get('kind') else []))  # a sealed bug stays a bug until resealed


def check_seal(root, o):
    """Fail when the outcome is sealed and its proof command or a sealed test file differs from the seal."""
    if not o.get('sealed'):
        return
    files = [e.rsplit('@', 1)[0] for e in o.get('sealed').split(', ')[1:] if not e.startswith('kind@')]
    now = dict(e.rsplit('@', 1) for e in fingerprint(root, o, files).split(', '))
    was = dict(e.rsplit('@', 1) for e in o.get('sealed').split(', ') if '@' in e)
    if 'proof' not in was:
        raise Fail('%s: "sealed:" is not a seal odd wrote (proof@<hash>, <file>@<hash>, ...); run %s seal %s'
                   % (o.rel, ODD, o.slug))
    moved = [{'proof': 'the proof command', 'kind': 'the kind (sealed as %s)' % was[k]}.get(k, k)
             for k in was if now.get(k) != was[k]]
    if moved:
        raise Fail('the sealed proof changed after it was sealed: %s; reseal it (%s seal %s; the reseal shows in the '
                   'diff) or restore it' % (', '.join(moved), ODD, o.slug))


def standing(root, cfg, o, changed):
    """The latest attempt at this outcome, when it passed on exactly the content that is here now; else None."""
    e = ([x for x in evidence(root, o.slug) if 'ok' in x] or [None])[-1]  # a seal event is not an attempt
    return e if e and e.get('ok') and e.get('hash') == content_hash(root, cfg, o, changed, e.get('tests'))[0] else None


def collects(root, base, path):
    """True when a changed line of `path` can decide which tests run: a line in a pytest section of pyproject.toml,
    setup.cfg or tox.ini, or a `load_tests` in an __init__.py (unittest calls it to build the suite). Only lines in
    the working tree are read, so a deletion alone is not seen (DESIGN.md, section 10)."""
    name = os.path.basename(path)
    if name not in SECTIONS and name != '__init__.py' or not os.path.isfile(os.path.join(root, path)):
        return False
    text = read_text(os.path.join(root, path)).splitlines()
    lines = changed_lines(root, base, path)
    if name == '__init__.py':
        return any('load_tests' in t for n, t in enumerate(text, 1) if lines is None or n in lines)
    section = ''
    for n, t in enumerate(text, 1):
        section = t.strip() if re.match(r'\s*\[', t) else section
        if (lines is None or n in lines) and re.match(SECTIONS[name], section):
            return True
    return False


def test_change(root, base, tests, outcomes, product=(), globs=()):
    """(touched, problem or '', what the reviewer reads or '', the files no reason covers): test files that existed at the base and this change modified
    or deleted, and files that decide which tests run (a conftest.py or pytest.ini, new or not; a changed pytest
    section or load_tests, collects), allowed only by a `test-change: <reason>` line in one of the given (in-play, not
    parked) outcomes. A reason that names test files (`globs`, or a file above) covers only those; one that names none covers every
    edit, as in earlier versions, and the reviewer's line says so. Any other new test file needs no reason."""
    old = set(zlist(root, 'ls-tree', '-r', '--name-only', '-z', base)) if base else set()
    picks = [p for p in list(tests) + list(product) if COLLECT.search(p) or collects(root, base, p)]
    touched = [p for p in tests if p in old and p not in picks] + picks
    if not touched:
        return touched, '', '', []
    why, left = [], list(touched)
    for o in outcomes:
        if not o.get('test-change'):
            continue
        words = {w.strip('.,;:()\'"`') for w in o.get('test-change').split()}
        named = [p for p in touched if p in words] if any(
            w in touched or COLLECT.search(w) or matches(w, globs) for w in words) else None
        covers = touched if named is None else named
        left = [p for p in left if p not in covers]
        why.append('test-change (%s): %s [%s]' % (o.slug, o.get('test-change'), (
            'names no file, so it covers every test edit: ' if named is None else 'covers: ') + (', '.join(covers) or 'none')))
    if not left:
        return touched, '', '; '.join(why), []
    named = ', '.join(left[:8]) + (', ...' if len(left) > 8 else '')
    return touched, ('%s: %s. A change that edits or deletes an existing test, or changes which tests run, fails closed: '
            'rewriting the test is the easiest way to make a proof pass. If the edit is right, say why in the outcome with '
            'the line "test-change: <reason>" (name the files to cover only those); the gate and the review comment show it.'
            % (named, 'an existing test file or one that decides which tests run, and no reason covers %s'
               % ('it' if len(left) == 1 else 'them'))), '', left


# ---------------------------------------------------------------- proofs, and taking the change out

def run_proof(root, cmd, timeout, env=None):
    """(exit code or None on timeout, last lines of output, seconds). The command's exit status is the verdict.
    Output goes to a file, so a process the proof leaves behind cannot hold the check open, and whatever is still
    running in the proof's process group when it ends is stopped. No environment variable marks the run, except
    `env` for the one traced run of the execution check (ran), whose exit code is no verdict."""
    t0 = time.time()
    with tempfile.TemporaryFile() as out:
        p = subprocess.Popen(cmd, shell=True, cwd=root, stdin=subprocess.DEVNULL, stdout=out, stderr=subprocess.STDOUT,
                             start_new_session=True, env=env)
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


PY = re.compile(r'^(python[\d.]*|pypy[\d.]*)$')
CHECKS = re.compile(r'^(exit|_exit|quit|abort|fail\w*|assert\w*|system|popen|exec\w*|spawn\w*|eval|__import__|'
                    r'import_module|run_path|run_module)$')  # a call that can end the run with a code, or run more
INERT = {'sys', 'os', 'json', 'math', 'decimal', 'fractions', 'datetime', 'time', 're', 'string', 'textwrap',
         'collections', 'itertools', 'functools', 'pprint', 'random'}  # imports that cannot check anything themselves


def _cannot_fail(node, calls):
    """True when evaluating this expression cannot end the run on purpose: no subscript, no division or modulo, no
    call that exits or checks (CHECKS), and, unless `calls`, no call but print and calls on inert modules."""
    for n in ast.walk(node):
        if isinstance(n, (ast.Subscript, ast.Lambda, ast.Await, ast.Yield, ast.YieldFrom)) or (
                isinstance(n, ast.BinOp) and isinstance(n.op, (ast.Div, ast.FloorDiv, ast.Mod, ast.MatMult))):
            return False
        if isinstance(n, ast.Call):
            f, root = n.func, n.func
            while isinstance(root, ast.Attribute):
                root = root.value
            if CHECKS.match(getattr(f, 'id', None) or getattr(f, 'attr', '')) or not calls and not (
                    getattr(f, 'id', None) in ('print', 'str', 'repr') or isinstance(f, ast.Attribute) and getattr(root, 'id', '') in INERT):
                return False
    return True


def prints_only(root, proof, targets):
    """True when every step of the proof only prints: an echo or printf, or Python code (-c, or a .py file) whose
    statements are only imports of the change itself and a few inert stdlib modules, print() calls, calls on those
    inert modules, and assignments to names; where no expression can fail on purpose (_cannot_fail: no subscript,
    division or modulo; a call into the change only inside print() or an assignment). Anything else (a test runner,
    grep, a helper module from the repository, -m, an if, an assert, a bare call into the change) may check: never
    refused. A pipe into `grep -q .` checks nothing and is not detected (DESIGN.md, section 10)."""
    try:
        lex = shlex.shlex(proof, posix=True, punctuation_chars=True)
        lex.whitespace_split = True
        words = list(lex)
    except ValueError:
        return False
    steps, step = [], []
    for w in words + [';']:
        if w in ('&&', '||', ';', '|', '&', ';;'):
            steps, step = steps + ([step] if step else []), []
        elif step or not re.match(r'^[A-Za-z_][A-Za-z0-9_]*=', w):
            step.append(w)
    mods = {t[:-3].replace('/', '.') for t in targets if t.endswith('.py')}
    mods |= {m.rsplit('.', n)[0] for m in list(mods) for n in range(1, m.count('.') + 1)}  # packages above them
    mods |= {m.split('.', n)[-1] for m in list(mods) for n in range(1, m.count('.') + 1)}  # run from inside one
    mods = {m[:-9] if m.endswith('.__init__') else m for m in mods}
    for step in steps:
        name = os.path.basename(step[0])
        if name in ('echo', 'printf'):
            continue
        if not PY.match(name) or '-m' in step:
            return False
        if '-c' in step:
            code = step[step.index('-c') + 1] if step.index('-c') + 1 < len(step) else ''
        else:
            files = [w for w in step[1:] if w.endswith('.py')]
            if not files or not os.path.isfile(os.path.join(root, files[0])):
                return False
            with open(os.path.join(root, files[0]), encoding='utf-8', errors='replace') as f:
                code = f.read()
        try:
            tree = ast.parse(code)
        except (SyntaxError, ValueError):
            return False
        for n in tree.body:
            call = isinstance(n, ast.Expr) and isinstance(n.value, ast.Call)
            printed = call and getattr(n.value.func, 'id', None) == 'print'
            if isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant) or isinstance(n, ast.Pass):
                continue
            if call and not _cannot_fail(n.value, printed) or isinstance(n, ast.Assign) and not (
                    all(isinstance(t, ast.Name) for t in n.targets) and _cannot_fail(n.value, True)):
                return False
            if not (call or isinstance(n, (ast.Assign, ast.Import, ast.ImportFrom))):
                return False
            names = [a.name for a in n.names] if isinstance(n, ast.Import) else (
                [n.module or ''] if isinstance(n, ast.ImportFrom) and not n.level else
                ['.'] if isinstance(n, ast.ImportFrom) else [])
            if any(m not in mods and m.split('.')[0] not in INERT for m in names):
                return False
    return bool(steps)


def hollow(proof, tail, seconds, root=None, targets=()):
    """Why a proof that exited 0 showed nothing, or '': it only prints (prints_only, given `root`), it ran no test,
    skipped every test it ran, or ended before its runner printed the summary it always prints. Read from the
    proof's own output for unittest, pytest, jest and go test; conservative, so a proof it cannot read is never
    refused (DESIGN.md, section 4)."""
    if root and prints_only(root, proof, targets):
        return 'it only prints (no test runner, no assert, no exit with a code of its own)'
    tail = tail or ''
    m = re.findall(r'(?m)^Ran (\d+) tests? in ([\d.]+)s\s*\n\s*OK(?: \((.*?)\))?', tail)
    if m and m[-1][0] == '0' or re.search(r'(?m)NO TESTS RAN|^no tests ran\b|=+ no tests ran|No tests found, exiting with code 0', tail):
        return 'it ran no test'
    count = lambda text, w: sum(int(n) for n in re.findall(r'(\d+) (?:%s)\b' % w, text))  # noqa: E731
    shown = sum(int(n) for n in re.findall(r'(?:skipped|expected failures)=(\d+)', m[-1][2])) if m and m[-1][2] else -1
    if m and shown == int(m[-1][0]):  # an expected failure shows nothing either
        return ('it skipped every test it ran (%s)' % m[-1][0] if 'expected' not in m[-1][2] else
                'no test it ran passed (OK (%s))' % m[-1][2])
    pt = re.findall(r'(?m)^=*\s*((?:\d+ \w+(?:, )?)+) in ([\d.]+)s', tail)
    if pt and count(pt[-1][0], 'skipped|xfailed') and not count(pt[-1][0], 'passed|xpassed|failed'):
        return ('it skipped every test it ran (%d)' % count(pt[-1][0], 'skipped') if 'xfailed' not in pt[-1][0] else
                'no test it ran passed (%s)' % pt[-1][0])
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


def pick(items, cap, where=None):
    """At most `cap` of `items`, spread evenly over them, always the same ones, in their order. Given `where(item)`
    -> (file, line): one per line first, the files sharing the cap evenly and each file's lines spread, and a second
    item on a line only once every line has one (one mutant per changed line is enough; DESIGN.md section 4)."""
    if where is None:
        return list(items) if len(items) <= cap else [items[i * len(items) // cap] for i in range(cap)]
    lines = {}
    for i, it in enumerate(items):
        lines.setdefault(where(it), []).append(i)
    out, depth = [], 0
    while len(out) < cap:
        files = {}
        for (f, _), at in lines.items():
            if len(at) > depth:
                files.setdefault(f, []).append(at[depth])
        if not files:
            break
        share, left = dict.fromkeys(files, 0), cap - len(out)
        while left and any(share[f] < len(files[f]) for f in files):
            for f in files:
                if left and share[f] < len(files[f]):
                    share[f], left = share[f] + 1, left - 1
        out += [i for f in files for i in pick(files[f], share[f])]
        depth += 1
    return [items[i] for i in sorted(out)]


def changed_lines(root, base, path):
    """The lines of `path` in the working tree that differ from the base; None (all) for a file the base lacks."""
    if not base or sh(['git', 'cat-file', '-e', '%s:%s' % (base, path)], root).returncode != 0:
        return None
    diff = git(root, 'diff', '-U0', '--no-renames', '--no-ext-diff', '--no-textconv', base, '--', path)
    out = set()
    for m in re.finditer(r'^@@ -\S+ \+(\d+)(?:,(\d+))? @@', diff, re.M):
        out.update(range(int(m.group(1)), int(m.group(1)) + int(m.group(2) or 1)))
    return out


TRACE = r"""# odd's execution check: which lines of the changed files this Python process runs (odd.py, ran)
import atexit, json, os, sys, threading


def _odd_trace(d):
    import types
    with open(os.path.join(d, 'targets.json')) as f:
        want = set(json.load(f))
    seen, keep = {}, {}

    def line(frame, event, arg):
        if event == 'line':
            seen[frame.f_code.co_filename].add(frame.f_lineno)
        return line

    def call(frame, event, arg):
        fn = frame.f_code.co_filename
        if fn not in keep:
            keep[fn] = os.path.realpath(fn) in want
        if keep[fn]:
            seen.setdefault(fn, set())
            return line
        return None

    def lines(code):
        import dis
        out = {n for _, n in dis.findlinestarts(code) if n}
        for c in code.co_consts:
            if isinstance(c, types.CodeType):
                out |= lines(c)
        return out

    def dump():
        sys.settrace(None)
        ran, can = {}, {}
        for fn, got in seen.items():
            ran.setdefault(os.path.realpath(fn), set()).update(got)
        for path in want:
            try:
                with open(path, 'rb') as f:
                    can[path] = sorted(lines(compile(f.read(), path, 'exec')))
            except Exception:
                pass
        with open(os.path.join(d, 'ran-%d.json' % os.getpid()), 'w') as f:
            json.dump({'ran': {k: sorted(v) for k, v in ran.items()}, 'can': can}, f)
    atexit.register(dump)
    sys.settrace(call)
    threading.settrace(call)


if os.environ.get('ODD_TRACE_DIR'):
    _odd_trace(os.environ['ODD_TRACE_DIR'])
    try:  # then a sitecustomize of the project's own, which this one hides
        import importlib.machinery, importlib.util
        here = os.path.dirname(os.path.abspath(__file__))
        spec = importlib.machinery.PathFinder.find_spec('sitecustomize', [p for p in sys.path if os.path.abspath(p or '.') != here])
        if spec:
            spec.loader.exec_module(importlib.util.module_from_spec(spec))
    except Exception:
        pass
"""


def ran(root, cfg, o, base, targets):
    """The execution check, for Python only: the proof run once more with a trace hook (a sitecustomize put first on
    PYTHONPATH, sys.settrace) restricted to the changed .py files. Returns (["file:line,line", ...] for changed
    executable lines no Python process of the proof ran, None, seconds), or (None, why it was not measured, seconds).
    The proof's own interpreter says which lines are executable, so its version's line table is the one used."""
    py = [p for p in targets if p.endswith('.py') and os.path.isfile(os.path.join(root, p))]
    steps = [[w for w in step.split() if not re.match(r'^[A-Za-z_][A-Za-z0-9_]*=', w)][:1]
             for step in re.split(r'&&|\|\||[;|\n]', o.get('proof') or '')]
    if not py:
        return None, 'no Python file in the change', 0.0
    if not any(w and re.match(r'^(python[\d.]*|pypy[\d.]*|pytest|py\.test)$', os.path.basename(w[0])) for w in steps):
        return None, 'the proof is not a Python run', 0.0
    real = {os.path.realpath(os.path.join(root, p)): p for p in py}
    d = tempfile.mkdtemp(prefix='odd-trace-')
    try:
        with open(os.path.join(d, 'sitecustomize.py'), 'w') as f:
            f.write(TRACE)
        with open(os.path.join(d, 'targets.json'), 'w') as f:
            json.dump(sorted(real), f)
        env = dict(os.environ, ODD_TRACE_DIR=d, PYTHONPATH=os.pathsep.join(
            [d] + [x for x in [os.environ.get('PYTHONPATH')] if x]))
        rc, _, secs = run_proof(root, o.get('proof'), cfg['proof_timeout'], env)
        dumps = []
        for name in sorted(os.listdir(d)):
            if name.startswith('ran-'):
                with open(os.path.join(d, name)) as f:
                    dumps.append(json.load(f))
    finally:
        shutil.rmtree(d, True)
    if rc != 0:
        return None, 'the traced run %s' % ('timed out' if rc is None else 'exited %d' % rc), secs
    if not dumps:
        return None, 'no Python process of the proof loaded the trace hook (python -I, -S or -E?)', secs
    out = []
    for path, p in sorted(real.items(), key=lambda kv: kv[1]):
        done = set().union(*[x['ran'].get(path, []) for x in dumps])
        can = set().union(*[x['can'].get(path, []) for x in dumps])
        changed = changed_lines(root, base, p)
        missing = sorted(n for n in can - done if changed is None or n in changed)
        if missing:
            out.append('%s:%s' % (p, ','.join(str(n) for n in missing)))
    return out, None, secs


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
    picked = pick(cands, cfg['mutants'], lambda c: (c[0], c[3]))
    res = {'mutants': len(picked), 'of': len(cands), 'killed': 0, 'survivors': [], 'unrun': [], 'seconds': 0.0}
    res['not_run'], why, res['trace_seconds'] = ran(root, cfg, o, base, targets)
    if why:
        res['not_measured'] = why
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
    """Under "strength": "enforce" a surviving mutant, or a changed line the proof never ran (ran), is a Fail, also
    for a verification recorded earlier."""
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
    why = []
    if st['survivors']:
        why.append('the proof does not notice %d of %d small break(s) in the changed lines ("strength": "enforce"); '
                   'each is a changed line the proof does not depend on:\n%s\n  make the proof assert what those '
                   'lines do, or take them out of the change.' % (len(st['survivors']), st['killed'] + len(st['survivors']),
                                                                  '\n'.join('    ' + w for w in st['survivors'])))
    if st.get('not_run'):
        why.append('%s\n  the proof never executes these changed lines ("strength": "enforce"), so it cannot show what '
                   'they do: make the proof run them, or take them out of the change.' % lines_run(st))
    if why:
        raise Fail('\n'.join(why), [('survived', w) for w in st['survivors']] + [
            ('not run', '%s:%s' % (f, n)) for f, ns in (x.rsplit(':', 1) for x in st.get('not_run') or []) for n in ns.split(',')])


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
            if rc == 5 or re.search(r'NO TESTS RAN|no tests ran|collected 0 items|Ran 0 tests', tail or '') else ''),
                   [('proof', failing(tail))])
    empty = hollow(o.get('proof'), tail, s1, root, targets)
    if empty:
        raise Fail('the proof exited 0 but %s, so it is not a proof: %s\n%s\n  make the proof run the test that shows '
                   'the outcome; a skip, an empty suite or an early exit 0 shows nothing.' % (empty, o.get('proof'), _indent(tail)))
    res = {'files': len(targets), 'lines': lines, 'seconds': [s1], 'red_says': '', 'skip': o.skip}
    if o.skip and o.bug:
        raise Fail('a bug outcome cannot skip the run at the base revision: the proof must reproduce the bug there. '
                   'Take the "counterfactual:" line out of %s, or drop "kind: bug" if this is not a bug fix.' % o.rel)
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
    if crc == 0 and o.bug:
        raise Fail(NO_REPRO % (o.get('proof'), ', '.join(targets[:8])))
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
                   % ('timeout' if rc3 is None else 'exit %d' % rc3, _indent(tail3)), [('proof', failing(tail3))])
    res.update(seconds=[s1, s2, s3], red_says=says(ctail))
    if o.bug:
        res['reproduced'] = last_line(ctail)
    if cfg['strength'] != 'off':
        res['strength'] = strength(root, cfg, o, base, targets, say, [s1, s2, s3])
        weak(cfg, o, res)
    return res


NO_REPRO = ('the proof does not reproduce the bug: it passes at the base revision (%s), so it cannot show the fix.\n'
            '  base for: %s\n  write a proof that fails on the unfixed code with the reported symptom.')


def last_line(tail):
    """The last non-blank line of a proof's output: how a bug outcome's proof failed at the base."""
    return next((x.strip() for x in reversed((tail or '').split('\n')) if x.strip()), '(no output)')


WHY = re.compile(r'Error\b|Exception\b|[Cc]annot |[Aa]ssert|[Ee]xpected|\u2715|\u2717|^not ok|panicked|No such file')


def says(tail):
    """What a failing proof said, in one line: the last line that names a reason (an error, a failed assertion), then
    the runner's last line when that is a different one (so a footer such as jest's "Ran all test suites" never
    stands alone)."""
    why, last = failing(tail), last_line(tail)[:120]
    return (why + ' / ' if why != last else '') + last


def failing(tail):
    """The proof's failing line: the last line of its output that names a reason, else its last line."""
    why = [l.strip() for l in (tail or '').splitlines() if WHY.search(l)]
    return (why[-1] if why else last_line(tail))[:120]


def next_block(items, rerun):
    """What a failed done, race or cascade ends with, and what the cascade prompt and the MCP server pass on: "next:",
    one line per actionable item (kind: text, from Fail.items), then the one command to rerun."""
    return '\n'.join(['next:'] + ['  %s: %s' % kv for kv in items] + ['  rerun: ' + rerun])


def _rerun(a):
    """The command line of `a` (parsed arguments of done, race or cascade), to paste: odd, the command, the slug, then
    every option that was given."""
    opts = [('--%s %s' % (k.rstrip('_').replace('_', '-'), shlex.quote(str(v)))).replace(' True', '')
            for k, v in sorted(vars(a).items()) if k not in ('cmd', 'slug', 'ticket') and v not in (None, False)]
    return ' '.join([ODD, a.cmd, shlex.quote(getattr(a, 'slug', None) or a.ticket)] + opts)


def _indent(text):
    return '\n'.join('    ' + l for l in (text or '').splitlines()[-12:])


def lines_run(st):
    """What the execution check (ran) found, in one line; '' for a result recorded before it existed."""
    if st.get('not_run'):
        return 'not run by the proof: ' + ' '.join(st['not_run'])
    if st.get('not_measured'):
        return 'lines run: not measured (%s)' % st['not_measured']
    return 'lines run: every changed executable line ran under the proof' if 'not_run' in st else ''


def _describe(o, res):
    if res.get('skip'):
        return 'SKIPPED the take-out check (%s): the proof passes; %d line(s) in %d file(s) not verified' % (
            res['skip'].split('-', 1)[-1].strip() or 'no reason', res['lines'], res['files'])
    text = 'took out %d file(s), %d line(s); without them the proof said: %s; %s s' % (
        res['files'], res['lines'], res['red_says'], '+'.join(str(s) for s in res['seconds']))
    if res.get('reproduced'):
        text += '\n          reproduced: ' + res['reproduced']
    st = res.get('strength')
    if st:
        text += '\n          proof strength %d of %d (small breaks in the changed lines the proof caught)%s%s; %s s' % (
            st['killed'], st['killed'] + len(st['survivors']),
            ' (%d of %d sampled)' % (st['mutants'], st['of']) if st['of'] > st['mutants'] else '',
            '; %d could not run' % len(st['unrun']) if st['unrun'] else '', st['seconds'])
        text += '\n          ' + st['stopped'] if st.get('stopped') else ''
        text += ''.join('\n          survived: ' + w for w in st['survivors'])
        text += ''.join('\n          could not run: ' + w for w in st['unrun'])
        text += '\n          ' + lines_run(st) if lines_run(st) else ''
        if st['survivors']:
            text += ('\n          next: add a proof case that tells %s apart from the break, or leave it (reported '
                     'only, unless "strength": "enforce")' % st['survivors'][0].split(' ', 1)[0])
    return text


# ---------------------------------------------------------------- the gate

def guards(root, s, say=lambda s: None):
    """Backlog item 9, the regression guard: [(outcome, commit, exit code, last line, seconds)] for every earlier
    outcome, merged at the base and not in play in this change, not parked, asked or skipped, whose boundary holds a
    file this change touches. Each proof runs once on the tree as it is (green only: no take-out run)."""
    if s['cfg']['guard'] == 'off' or not s['base']:
        return []
    touched, out = s['product'] + s['tests'], []
    for o in all_outcomes(root):
        if o.rel in s['changed'] or o.parked or o.asked or o.skip or not any(o.covers(p) for p in touched):
            continue
        commit = git(root, 'log', '-1', '--format=%h', s['base'], '--', o.rel).strip()
        if not commit:
            continue  # not merged: an outcome file git does not track is no earlier outcome
        say('guard %s: %s' % (o.slug, o.get('proof')))
        rc, tail, secs = run_proof(root, o.get('proof'), s['cfg']['proof_timeout'])
        out.append((o, commit, rc, last_line(tail), secs))
    return out



def _strong(cfg, o):
    """Why one verified outcome's recorded proof strength (strength, weak) is short of the auto lane, or []."""
    st, need, slug = o.get('strength'), cfg['auto_min_strength'], o['slug']
    if o.get('skip'):
        return []  # named as a skipped take-out check
    if not st:
        return ['%s: proof strength was not measured' % slug]
    n, why = st['killed'] + len(st['survivors']), []
    if not n:
        why.append('%s: no small break could be made in its changed lines, so its proof strength is unknown' % slug)
    elif st['killed'] < need * n - 1e-9:
        why.append('%s: proof strength %d of %d, below "auto_min_strength" %s' % (slug, st['killed'], n, need))
    if st['unrun']:
        why.append('%s: %d small break(s) did not run to completion' % (slug, len(st['unrun'])))
    if st.get('not_run'):
        why.append('%s: %s' % (slug, lines_run(st)))
    return why


def lane(root, s, facts, skips, allowed):
    """Backlog item 11, the auto-merge lane: [] when the change may merge with its outcomes and proofs read, else
    each reason it goes to review. A disqualifier is never weighed against the rest. odd only says; it never merges."""
    cfg, outs, why = s['cfg'], facts['outcomes'], []
    if facts['problems']:
        why.append('the gate did not pass')
    if not any(o['state'] == 'ok' for o in outs):
        why.append('no verified outcome in this change')
    for o in outs:
        if o['state'] == 'ok':
            why += _strong(cfg, o)
        elif o['state'] in ('parked', 'asked'):
            why.append('%s is %s' % (o['slug'], 'parked' if o['state'] == 'parked' else 'waiting for an answer'))
    why += ['%s skipped the take-out check' % k.split(' - ', 1)[0] for k in skips]
    n = sum(min(v, BIG) for v in sizes(root, s['base'], s['product']).values())
    if n > cfg['auto_max_lines']:
        why.append('%s changed product line(s), more than "auto_max_lines" %d'
                   % ('a binary file or other' if n >= BIG else n, cfg['auto_max_lines']))
    if s['stray']:
        why.append('%d line(s) outside every outcome: %s' % (s['stray_lines'], ', '.join(s['stray'][:5])))
    if s['control']:
        why.append('control file(s) changed: ' + ', '.join(s['control']))
    if allowed:
        why.append('an existing test changed: ' + allowed)
    if cfg['guard'] == 'off':
        why.append('the regression guard is off')
    why += ['the regression guard failed: %s (proven in %s)' % (g['slug'], g['commit'])
            for g in facts.get('guards', []) if g['state'] != 'ok']
    return why


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
    active = [o for o in inplay if not o.parked and not o.asked]
    stray = [p for p in product if not any(o.covers(p) for o in active)]
    return dict(cfg=cfg, base=base, changed=changed, control=control, exempt=exempt, tests=tests, product=product,
                inplay=inplay, active=active, stray=stray,
                stray_lines=sum(sizes(root, base, stray, cfg['trivial_lines']).values()))


def gate(root, base_arg=None, recompute=False, say=lambda s: None, facts=None):
    """(exit code, report lines). Raises CouldNotRun. A dict passed as facts is filled with the same result as data,
    for the --json and --summary renderings."""
    s = survey(root, base_arg, recompute)
    cfg, base, changed, product, active, stray = s['cfg'], s['base'], s['changed'], s['product'], s['active'], s['stray']
    lines, problems, skips, outs, exempted, changed_kind = [], [], [], [], [], []
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
    if cfg['auto_lane']:  # until the end is reached: a gate that stops is never the auto lane
        facts.update(lane='review', lane_reasons=['the gate stopped before it finished'])
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
            if was_bug(root, o):
                changed_kind.append(o.slug)
                lines.append('          kind changed from bug to %s: the proof no longer has to fail at the base'
                             % (o.get('kind') or 'none'))
            fact(o, 'ok', **dict({k: res[k] for k in RESULT if k in res}, **({'kind_was': 'bug'} if o.slug in changed_kind else {})))
        except Fail as e:
            problems.append('%s: %s' % (o.slug, e))
            fact(o, 'fail', why=str(e))
    ran_guards = facts['guards'] = []
    for o, commit, rc, last, secs in guards(root, s, say):
        name = '%s (proven in %s)' % (o.slug, commit)
        ran_guards.append(dict(slug=o.slug, commit=commit, proof=o.get('proof'), seconds=secs,
                               state='ok' if rc == 0 else 'fail', **({} if rc == 0 else {'why': last})))
        if rc == 0:
            lines.append('  guard   %s: still passes, %ss' % (name, secs))
        elif cfg['guard'] == 'enforce':
            lines.append('  guard   %s now fails' % name)
            problems.append('%s now fails: %s\n    an earlier proven outcome whose files this change touches; its '
                            'proof: %s' % (name, last, o.get('proof')))
        else:
            lines.append('  guard   %s now fails: %s (reported only; "guard": "enforce" fails the gate)' % (name, last))
    for o in s['inplay']:
        if o.parked:
            lines.append('  parked  %s: %s (a parked outcome covers no files)' % (o.slug, o.parked))
            fact(o, 'parked', why=o.parked)
        elif o.asked:
            lines.append('  asked   %s: %s (waiting for an answer; covers no files until the "asked:" line is deleted)'
                         % (o.slug, o.asked))
            fact(o, 'asked', why=o.asked)
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
    allowed = ''
    if s['tests'] or s['product']:
        touched, bad, why, _ = test_change(root, base, s['tests'], active, s['product'], cfg['test_globs'])
        picks = [p for p in touched if COLLECT.search(p) or collects(root, base, p)]
        old = [p for p in touched if p not in picks]
        exempted += [] if not (s['tests'] or touched) else ['test files: %d changed%s%s%s' % (
            len(s['tests']), '; existed before and were modified or deleted: ' + ', '.join(old[:8]) if old else '',
            '; decide which tests run: ' + ', '.join(picks[:8]) if picks else '', '; allowed by ' + why if why else '')]
        problems += [bad] if bad else []
        allowed = why
    lines += ['  ' + e for e in exempted]
    exempted += ['skip: ' + k for k in skips]
    cov_lines, cov_problems, cov_facts = coverage(root, s)
    lines += cov_lines
    problems += cov_problems
    if cov_facts:
        facts['requirements'] = cov_facts
    if s['control']:
        lines.append('  CONTROL FILES CHANGED (a person must review; in CI the tool and settings are read from the target): '
                     + ', '.join(s['control']))
    head = '%s gate%s: base %s, %d file(s) changed, %d outcome(s) in this change' % (
        ODD, ' --recompute' if recompute else '', (base or 'none')[:10], len(changed), len(s['inplay']))
    tail = ' (%d skipped the take-out check: %s)' % (len(skips), '; '.join(skips)) if skips else ''
    tail += ' (%d changed kind from bug: %s)' % (len(changed_kind), ', '.join(changed_kind)) if changed_kind else ''
    waiting = [o.slug for o in s['inplay'] if o.asked and not o.parked]
    tail += ' (%d waiting for an answer: %s)' % (len(waiting), ', '.join(waiting)) if waiting else ''
    if cfg['auto_lane']:
        reasons = lane(root, s, facts, skips, allowed)
        facts.update(lane='review' if reasons else 'auto', lane_reasons=reasons)
        lines.append('  lane    ' + ('review: ' + '; '.join(reasons) if reasons else
                                     'auto (every condition of the auto-merge lane holds; odd itself never merges)'))
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
# backlog item 7: the whole suite of each runner, the proof `new --kind refactor` defaults to ({dir}: the test folder)
SUITES = {'pytest': 'python3 -m pytest -q', 'jest': 'npx jest', 'vitest': 'npx vitest run', 'node': 'node --test',
          'mocha': 'npx mocha', 'go': 'go test ./...', 'cargo': 'cargo test',
          'unittest': 'python3 -m unittest discover -q{dir}', 'make': 'make test'}
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


def suggest_proof(root, slug, test=None, suite=False):
    """(the proof command, what was detected and chosen), or (None, why not): never a silent guess. suite: the
    runner's whole suite instead of one test file (unless a test path is given)."""
    found = runners(root)
    if not found:
        return None, NO_RUNNER
    name, cmd, default = [p for p in PROOFS if p[0] == found[0][0]][0]
    if suite and not test:
        folder = [d for d in ('tests', 'test') if os.path.isdir(os.path.join(root, d))][:1]
        proof = SUITES[name].format(dir=''.join(' -s ' + d for d in folder))
        return proof, 'detected: %s\nproof: %s  (the whole test suite)' % (', '.join('%s (%s)' % f for f in found), proof)
    path = test or default.format(slug=slug, name=re.sub(r'[.-]', '_', slug))
    q = shlex.quote if test else (lambda x: x)  # a path from the slug needs no quoting; the init placeholder must stay readable
    proof = cmd.format(test=q(path), dir=q('./' + os.path.dirname(path) if os.path.dirname(path) else '.'),
                       stem=q(os.path.splitext(os.path.basename(path))[0]))
    return proof, 'detected: %s\nproof: %s%s' % (', '.join('%s (%s)' % f for f in found), proof, (
        ' (runs the whole test target: narrow it by hand if the Makefile allows)' if not default else
        '  (the test goes in %s)' % path))


# backlog item 6: a sentence names something checkable when it has a verb of observation, a state predicate ("is
# disabled", "keeps", "no longer"), a capability ("can export") or a measurable term. English only. "The tests pass" is
# no observable (it is what every proof says), so a sentence whose only such word is the suite passing is refused.
OBSERVE = re.compile(r'\b(?:(?:see|get|receive|observe|read|find|show|display|print|return|report|list|log|exit|fail|'
                     r'pass|reject|refuse|accept|raise|throw|respond|answer|reply|load|contain|hear|notice|measure|'
                     r'match|appear|produce|output|emit|render|download|send|warn|alert|block|stay|remain|succeed|'
                     r'complete|finish|reach|hold|include|exclude|equal|count|total|sum|lose|crash|hang|redirect|'
                     r'record|allow|deny|restore|recover|survive|detect|notify|keep|export|import|split|save|delete|'
                     r'remove|open|close|upload|cancel|undo|disappear|become)(?:s|es|ed|d|n|ing)?|'
                     r'saw|seen|got|gotten|found|shown|heard|ran|held|sent|lost|told|gives|gave|given|kept|became|'
                     r'no longer|still|can(?:not)?|(?:is|are|was|were|stays?|remains?|becomes?)(?: not)? (?:\w+(?:ed|en)|'
                     r'visible|hidden|empty|active|inactive|available|unavailable|open|closed|on|off|valid|invalid|'
                     r'present|absent|unchanged|blank|greyed out|read-only|locked|unlocked))\b', re.I)
MEASURE = re.compile(r'\d|%|\b(?:zero|one|two|three|four|five|six|seven|eight|nine|ten|hundred|thousand|every|each|'
                     r'none|never|always|only|exactly|within|under|at (?:least|most)|(?:fewer|less|more) than|same|'
                     r'percent|ms|seconds?|minutes?|hours?|bytes?|errors?|status|empty)\b', re.I)
SUITE_PASSES = re.compile(r'\b(?:the |all (?:the )?)?(?:unit |existing )?(?:tests?|test suite|suite|build|ci|checks?)'
                          r'(?: all)?(?: still)? (?:pass|succeed|go green|are green|is green)(?:es|ed|s|ing)?\b', re.I)


def observable(sentence):
    """True unless the sentence has neither an observation (verb, state, capability) nor a measurable term, once "the
    tests pass" is taken out (conservative: it refuses "Refactor X." and "Clean X so the tests pass.")."""
    rest = SUITE_PASSES.sub(' ', sentence)
    return bool(OBSERVE.search(rest) or MEASURE.search(rest))


def cmd_new(a, root):
    if not SLUG.match(a.slug):
        raise Fail('slug: lowercase letters, digits, dot, dash, underscore')
    o = Outcome(root, a.slug)
    if os.path.exists(o.path):
        raise Fail('%s exists' % o.rel)
    sentence = ' '.join(a.outcome.split())
    if len(sentence.split()) < 4 or re.search(r'<[^>]+>', sentence):
        raise Fail('the outcome is one full sentence: who observes what result')
    if load_config(root)['ambiguity_stop'] and not observable(sentence):
        raise Fail('the outcome has no checkable observable (nothing anyone would see, get or measure): %r.\n'
                   'state it in the form "<who> <observes> <what>, measurably", e.g. "A cashier who splits a bill three '
                   'ways sees three totals that add up to the bill."\nIf the ticket does not say what should be '
                   'observable, ask one precise question instead of guessing: %s ask <slug> "<question>" (on an '
                   'outcome file) or ask the person who wrote the ticket.' % (sentence, ODD))
    globs = split_globs(','.join(a.in_))
    if a.proof is None:
        if a.kind != 'refactor':
            raise CouldNotRun('odd new: --proof is required (only --kind refactor defaults it, to the whole test suite)')
        a.proof = 'auto'
    if not a.proof.strip() or not globs:
        raise Fail('--proof and --in must not be empty')
    if a.test and a.proof.strip() != 'auto':
        raise Fail('--test goes with --proof auto only; the test path is already in your proof command')
    if a.proof.strip() == 'auto':
        a.proof, said = suggest_proof(root, a.slug, a.test, suite=a.kind == 'refactor')
        if a.proof is None:
            raise Fail('%s.\ngive the command yourself: %s new %s "<outcome>" --proof "<command>" --in "<globs>"' % (said, ODD, a.slug))
        print(said)
    covers = ', '.join('%s:%s' % (k, r) if k else r for k, r in cover_ids(a.covers or ''))
    o.f.update([('outcome', sentence), ('proof', a.proof.strip()), ('in', ', '.join(globs))] +
               ([('covers', covers)] if covers else []) + ([('kind', a.kind)] if a.kind else []) +
               ([('counterfactual', REFACTOR_SKIP)] if a.kind == 'refactor' else []))
    o.save()
    odd_looking = [g for g in globs if re.search(r'[\s{}]', g)]
    print('%s created (paths and the proof are relative to the repository root).%s\n'
          'next: write the proof under a test path, make the change inside "%s", then: %s done %s'
          % (o.rel, ('\nnote: globs are separated by commas and braces are not expanded; "%s" is read as one path.'
                     % odd_looking[0]) if odd_looking else '', o.get('in'), ODD, a.slug))
    if a.kind:
        print('hint (%s): %s' % (a.kind, HINTS[a.kind]))


def prove(root, o, s, say=lambda s: None):
    """The checks of `odd done`: no unexplained edit of an existing test (R2), then verify. `s` is survey(root).
    Shared by done and race, which runs it inside each attempt's worktree."""
    cfg, base = s['cfg'], s['base']
    if o.asked:
        raise Fail('%s is waiting for an answer: %s\nanswer it, then delete the "asked:" line of %s' % (o.slug, o.asked, o.rel))
    _, bad, _, left = test_change(root, base, s['tests'], [o] + [x for x in s['active'] if x.slug != o.slug], s['product'],
                            cfg['test_globs'])
    if bad:
        raise Fail(bad, [('refused', p) for p in left])
    return verify(root, cfg, o, base, changed_files(root, base), say)


def _verified(root, o, s, res):
    """What a verified outcome leaves: its "parked:" line gone, and the local evidence the gate reads. Shared by done
    and chain."""
    if o.parked:
        del o.f['parked']
        o.save()
    h, tests = content_hash(root, s['cfg'], o, changed_files(root, s['base']))  # read again: a proof may write files
    record(root, o.slug, ok=True, hash=h, tests=tests, **dict(res, **_kind(o)))


def cmd_done(a, root):
    o, s = Outcome.load(root, a.slug), survey(root, a.base)
    cfg, base = s['cfg'], s['base']
    try:
        res = prove(root, o, s, print)
    except Fail as e:
        record(root, a.slug, ok=False, why=str(e)[:300], **_kind(o))
        raise Fail('%s\n%s' % (e, next_block(e.items, _rerun(a))) if e.items else e, e.items)  # no item: rerunning fails alike
    _verified(root, o, s, res)
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
    targets = [p for p in classify(changed_files(root, base), cfg)[3] if o.covers(p)] if o.bug else []
    if targets:  # a bug: the proof runs at the base revision of the outcome's files, the fix taken out
        rc, tail, _ = without_change(root, cfg, o, base, targets)
    else:
        rc, tail, _ = run_proof(root, o.get('proof'), cfg['proof_timeout'])
    if unrunnable(rc):
        raise CouldNotRun('the proof did not run to completion (%s), so it is not red. A proof must run and exit '
                          'non-zero before the change.\n%s' % ('timeout' if rc is None else 'exit %d' % rc, _indent(tail)))
    if rc == 0 and o.bug:
        raise Fail(NO_REPRO % (o.get('proof'), ', '.join(targets[:8]) or 'no file changed yet, the tree is the base'))
    if rc == 0:
        raise Fail('the proof already passes, so it cannot be sealed red first: %s. Seal it before the change, or '
                   'take the change out first.' % o.get('proof'))
    o.f['sealed'] = fingerprint(root, o, tests)
    o.save()
    record(root, a.slug, seal=o.f['sealed'], base=base, red=says(tail), **_kind(o))  # what stats counts as sealed
    print('%s: sealed; the proof fails now (%s). Sealed: %s. Now write the code; a later edit to these files fails '
          '%s done and the gate until it is resealed.' % (a.slug, says(tail),
                                                        ', '.join(tests), ODD))
    if o.bug:
        print('reproduced: ' + last_line(tail))


# ---------------------------------------------------------------- race: N attempts, the proof picks the winner

RACE_PROMPT = """You are one attempt of several at one outcome. Each attempt works in its own copy of the repository (the
current directory); the proof decides which attempt is kept, and the others are discarded.

Outcome: %(outcome)s
Proof (a command that exits 0 only when the outcome holds): %(proof)s
Change only files inside: %(ins)s (new test files are allowed too)
Leave alone: %(fixed)s. An attempt that edits them is discarded.

When you have finished, exit. odd then checks this copy as `odd done %(slug)s` would: the proof passes, fails with the
change taken out and passes again, and small breaks in the changed lines make it fail. Do not commit, push or run
`odd park` here; if the outcome cannot honestly be reached, say why in your output and exit.

"""


def _killpg(p):
    try:
        os.killpg(p.pid, signal.SIGKILL)
    except OSError:
        pass


def _alive(pid):
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except OSError:
        return True
    return True


def _sweep(prefix, skip_group=None):
    """Kill every process whose environment carries ODD_ATTEMPT=<prefix...>, the mark each agent is started with, so a
    process an agent detached from its group (setsid, a daemon) is found too. Returns the pids found outside the
    process group `skip_group` (the agent's own group, killed already). Reads /proc: where there is none (macOS) nothing
    is found, and a process that clears its environment is not found."""
    mark, left = b'ODD_ATTEMPT=' + os.fsencode(prefix), []
    for _ in range(20):
        found = []
        for d in os.listdir('/proc') if os.path.isdir('/proc') else ():
            if not d.isdigit() or int(d) == os.getpid():
                continue
            try:
                with open('/proc/%s/environ' % d, 'rb') as f:
                    if not any(e.startswith(mark) for e in f.read().split(b'\0')):
                        continue
                with open('/proc/%s/stat' % d, 'rb') as f:
                    group = int(f.read().rsplit(b')', 1)[1].split()[2])
            except (OSError, ValueError, IndexError):
                continue
            found.append(int(d))
            try:
                os.kill(int(d), signal.SIGKILL)
            except OSError:
                pass
            if group != skip_group and int(d) not in left:
                left.append(int(d))
        if not found:
            break
        time.sleep(0.05)  # killed; it leaves /proc's marked set once it has exited
    return left


def _drop_run(root, run):
    """Remove one run's attempts: first any process still carrying an attempt's mark, then the directory (also a run
    an older odd made of linked worktrees, which `worktree prune` then forgets). The user's working tree is never
    touched."""
    _sweep(run + os.sep)
    shutil.rmtree(run, ignore_errors=True)
    sh(['git', 'worktree', 'prune'], root)


def _wait_agent(at, p, timeout, done):
    try:
        rc = p.wait(timeout=max(0.0, timeout - (time.time() - at['t0'])))
    except subprocess.TimeoutExpired:
        rc = None
    _killpg(p)  # whatever the agent left running in its process group goes with it
    p.wait()
    at.update(rc=rc, agent_s=round(time.time() - at['t0'], 1), left=_sweep(at['wt'] + os.sep, skip_group=p.pid))
    done.put(at)


def _clear(path):
    """Remove a file, a symlink (never what it points to) or a directory tree."""
    if os.path.isdir(path) and not os.path.islink(path):
        shutil.rmtree(path, ignore_errors=True)
    elif os.path.lexists(path):
        os.remove(path)


def _exclude(root, wt):
    """The user's info/exclude in the attempt's git directory, so files the user keeps out of git stay out there."""
    src = os.path.join(root, git(root, 'rev-parse', '--git-path', 'info/exclude').strip())
    os.makedirs(os.path.join(wt, '.git', 'info'), exist_ok=True)
    if os.path.isfile(src):
        shutil.copyfile(src, os.path.join(wt, '.git', 'info', 'exclude'))


def _settle(root, at):
    """Before a finished attempt is checked: why it is refused (a process it left running, its .git replaced), or ''
    with its git directory put back as odd made it (config, info/exclude, no hooks, the index of its start), so
    nothing the agent set up in git hides a change from the check or runs during it, and with the ignored files the
    agent made that the user's tree does not have removed, since the applied patch would not carry them."""
    wt, g = at['wt'], os.path.join(at['wt'], '.git')
    if at.get('left'):
        return 'left process %s running (killed)' % ', '.join(str(x) for x in at['left'][:6])
    if os.path.islink(g) or not os.path.isdir(g) or os.path.lexists(os.path.join(g, 'commondir')):
        return 'replaced its .git directory, which odd checks it with'
    for name in ('config', 'hooks', 'info'):
        _clear(os.path.join(g, name))
    shutil.copyfile(wt + '.config', os.path.join(g, 'config'))
    _exclude(root, wt)
    git(wt, 'read-tree', at['start'])
    for p in zlist(wt, 'ls-files', '--others', '--ignored', '--exclude-standard', '-z'):
        if not os.path.lexists(os.path.join(root, p)):
            _clear(os.path.join(wt, p))
    return ''


def _judge(root, cfg, o, base, at, fixed):
    """Check one finished attempt inside its worktree: what it may not touch, then the checks of `odd done`."""
    wt, start = at['wt'], at['start']
    if at['rc'] is None:
        return 'timed out after %ss (killed with its process group)' % cfg['race_timeout']
    why = _settle(root, at)
    if why:
        return why
    delta = changed_files(wt, start)
    control, exempt, tests, product = classify(delta, cfg)
    at['delta'] = delta
    at['lines'] = sum(sizes(wt, start, tests + product).values())
    moved = sorted(set(zlist(wt, *DIFF, '--name-only', start, '--', *fixed)) | set(control))
    if moved:
        return 'edited %s, which an attempt must leave alone' % ', '.join(moved[:6])
    outside = [p for p in product if not o.covers(p)]
    if outside:
        return 'changed files outside "in: %s": %s' % (o.get('in'), ', '.join(outside[:6]))
    try:
        at['res'] = prove(wt, Outcome.load(wt, o.slug), survey(wt, base))
    except (Fail, CouldNotRun) as e:
        at['items'] = getattr(e, 'items', [])
        at['detail'] = str(e).strip()[:3000]  # the whole finding: what failed, which break survived, which line did not run
        first = str(e).strip().split('\n')[0][:160]
        return first if isinstance(e, Fail) else 'could not verify: ' + first
    return ''


def _score(at):
    """(caught, of): small breaks the proof caught; (0, 0) when strength was not measured."""
    st = (at.get('res') or {}).get('strength') or {}
    return st.get('killed', 0), st.get('killed', 0) + len(st.get('survivors', [])) + len(st.get('unrun', []))


def _rank(at):
    k, n = _score(at)
    return (-(float(k) / n if n else 0.0), at['lines'], at['agent_s'], at['n'])


def _why_won(ranked):
    if len(ranked) == 1:
        return 'the only verified attempt'
    w, r = ranked[0], ranked[1]
    if _rank(w)[0] != _rank(r)[0]:
        return 'won on proof strength (%d of %d against %d of %d for attempt %s)' % (_score(w) + _score(r) + (r['name'],))
    if w['lines'] != r['lines']:
        return 'won on fewer changed lines (%d against %d for attempt %s)' % (w['lines'], r['lines'], r['name'])
    return 'won on the earlier finish (%ss against %ss for attempt %s)' % (w['agent_s'], r['agent_s'], r['name'])


def _race_start(root, cfg, slug, base_arg):
    """What race and cascade establish before any attempt: the outcome (and its seal), the commit every attempt starts
    from, the base, and the files an attempt must leave alone. Returns (o, head, base, fixed)."""
    try:
        o = Outcome.load(root, slug)
        check_seal(root, o)
    except Fail as e:
        raise CouldNotRun(str(e))
    if cfg['race_seal'] and not o.get('sealed'):
        raise CouldNotRun('"race_seal" is on and %s is not sealed: run %s seal %s first, so the proof is shown to fail '
                          'before any attempt and no attempt can change it unseen' % (o.rel, ODD, o.slug))
    head = rev(root, 'HEAD')
    if not head:
        raise CouldNotRun('each attempt starts from a commit and there is none yet: commit first')
    base, _ = find_base(root, cfg, base_arg)
    tests = classify(changed_files(root, base), cfg)[2]
    fixed = [o.rel] + [p for p in tests if os.path.isfile(os.path.join(root, p)) and not os.path.islink(os.path.join(root, p))]
    fixed += ['.odd/config.json'] if os.path.isfile(odd_dir(root, 'config.json')) else []
    return o, head, base, fixed


def _keep(root, cmd, slug):
    """The directory for one command's prompts, agent logs and patch, replaced by the next run; also removes the
    worktrees of a run that was killed outright."""
    keep = state_dir(root, cmd, slug)
    shutil.rmtree(keep, ignore_errors=True)
    os.makedirs(keep)
    os.makedirs(state_dir(root, 'race'), exist_ok=True)
    for name in os.listdir(state_dir(root, 'race')):
        if name.startswith('run-') and name[4:].isdigit() and not _alive(int(name[4:])):
            _drop_run(root, state_dir(root, 'race', name))
    return keep


def _prompt(o, cfg, fixed):
    return RACE_PROMPT % dict(outcome=o.get('outcome'), proof=o.get('proof'), ins=o.get('in'), fixed=', '.join(fixed),
                              slug=o.slug) + METHOD.replace('{trivial}', str(cfg['trivial_lines']))


def _worktree(root, run, name, head, fixed):
    """A working tree of `head` at run/name, under the git directory, with `fixed` (the outcome and its proof as
    they are in the user's tree) copied in and committed as its start. Returns its path. It is a clone that reads
    the user's objects (--shared) but has its own config, hooks, refs and index, not a linked worktree, which would
    share the user's config and hooks: a `git config` or a hook an attempt writes goes with it. No remote is kept.
    Its config as made here is saved beside it (run/name.config) for _settle()."""
    wt = os.path.join(run, name)
    os.makedirs(run, exist_ok=True)
    git(root, 'clone', '--quiet', '--shared', '--no-checkout', '--no-tags', root, wt)
    git(wt, 'remote', 'remove', 'origin')
    _exclude(root, wt)
    git(wt, 'checkout', '--quiet', '--detach', head)
    for p in fixed:
        os.makedirs(os.path.dirname(os.path.join(wt, p)), exist_ok=True)
        shutil.copy2(os.path.join(root, p), os.path.join(wt, p))
    git(wt, 'add', '-f', '--', *fixed)
    git(wt, '-c', 'user.name=odd', '-c', 'user.email=odd@localhost', '-c', 'commit.gpgsign=false', 'commit',
        '--quiet', '--no-verify', '--allow-empty', '-m', 'odd: the outcome and its proof')
    shutil.copyfile(os.path.join(wt, '.git', 'config'), wt + '.config')
    return wt


def _launch(at, timeout, done):
    """Start the agent command `at['cmd']` in `at['wt']` in its own process group, the prompt as {prompt_file} or on
    stdin, output to `at['log']`; `at` goes on the queue `done` when it ends or is killed at the timeout."""
    named = '{prompt_file}' in at['cmd']
    with open(at['log'], 'wb') as log, open(at['prompt'], 'rb') as prompt:
        p = subprocess.Popen(at['cmd'].replace('{prompt_file}', shlex.quote(at['prompt'])), shell=True,
                             cwd=at['wt'], stdin=subprocess.DEVNULL if named else prompt, stdout=log,
                             stderr=subprocess.STDOUT, start_new_session=True,
                             env=dict(os.environ, ODD_ATTEMPT=at['wt'] + os.sep))  # the mark _sweep() finds it by
    at['t0'] = time.time()
    threading.Thread(target=_wait_agent, args=(at, p, timeout, done), daemon=True).start()
    return p


def _next(done):
    while True:
        try:
            return done.get(timeout=0.5)  # a timeout, so a signal is handled while waiting
        except queue.Empty:
            pass


def _attempts(root, cfg, o, base, head, fixed, cmds, keep, text, names):
    """One attempt per command in `cmds`, the agents in parallel, each in a detached worktree of `head` under the git
    directory with `fixed` copied in as the start; each checked by _judge when its agent ends. Returns (attempts,
    ranked verified attempts, the best one's patch, seconds of setup and clean-up). The worktrees are removed before
    it returns, also on an exception or a signal; the user's working tree is not touched."""
    t0 = time.time()
    run, attempts, procs, done = state_dir(root, 'race', 'run-%d' % os.getpid()), [], [], queue.Queue()
    try:
        for i, (cmd, name) in enumerate(zip(cmds, names), 1):
            wt = _worktree(root, run, str(i), head, fixed)
            at = dict(n=i, name=name, wt=wt, start=rev(wt, 'HEAD'), cmd=cmd, lines=0, res=None,
                      prompt=os.path.join(keep, 'prompt-%s.md' % name), log=os.path.join(keep, 'agent-%s.log' % name))
            with open(at['prompt'], 'w', encoding='utf-8') as f:
                f.write(text)
            attempts.append(at)
        setup = time.time() - t0
        for at in attempts:
            procs.append(_launch(at, cfg['race_timeout'], done))
        for _ in attempts:
            at = _next(done)
            print('  attempt %s: the agent ended after %ss (%s); verifying' % (
                at['name'], at['agent_s'], 'killed at the timeout' if at['rc'] is None else 'exit %d' % at['rc']))
            v0 = time.time()
            at['why'] = _judge(root, cfg, o, base, at, fixed)
            at['verify_s'] = round(time.time() - v0, 1)
        ranked = sorted([x for x in attempts if not x['why']], key=_rank)
        patch = ''
        if ranked:
            w = ranked[0]
            if w['delta']:
                git(w['wt'], 'add', '-A', '--', *w['delta'])
                patch = git(w['wt'], 'diff', '--cached', '--binary', '--no-renames', w['start'], '--', *w['delta'])
        t1 = time.time()
    finally:
        for p in procs:
            _killpg(p)
        _drop_run(root, run)
    return attempts, ranked, patch, setup + time.time() - t1


def _table(attempts, ranked, more=()):
    """One row per attempt: name, any `more` columns (header, function of the attempt), strength, lines, seconds (the
    agent's, then the verification's), and the result."""
    rows = [('#',) + tuple(h for h, _ in more) + ('strength', 'lines', 'seconds', 'result')]
    for at in attempts:
        k, m = _score(at)
        rows.append((at['name'],) + tuple(f(at) for _, f in more) + (
            '%d of %d' % (k, m) if m else '-', str(at['lines']), '%s+%s' % (at['agent_s'], at['verify_s']),
            ('verified' + (', winner' if ranked and at is ranked[0] else '')) if not at['why']
            else 'not verified: ' + at['why']))
    cols = len(rows[0]) - 1
    wide = [max(len(r[c]) for r in rows) for c in range(cols)]
    for r in rows:
        print('  ' + '  '.join(r[c].ljust(wide[c]) for c in range(cols)) + '  ' + r[cols])


def _patch(root, patch, path, apply=True, reverse=False):
    """Write `patch` to `path`; with `apply`, git-apply it (all or nothing) to the user's tree. Returns git's error."""
    with open(path, 'w', encoding='utf-8', errors='surrogateescape') as f:
        f.write(patch)
    r = sh(['git', 'apply', '--binary'] + (['-R'] if reverse else []) + [path], root) if apply and patch else None
    return (r.stderr or r.stdout).strip()[:300] if r is not None and r.returncode != 0 else ''


def _apply(root, o, head, w, patch, keep, hint=True):
    """Apply the verified winner's patch to the user's working tree, only when nothing inside the boundary changed
    there; otherwise leave it as a patch (Fail)."""
    path = os.path.join(keep, 'winner.patch')
    mine = [p for p in changed_files(root, head) if o.covers(p)]
    err = _patch(root, patch, path, apply=not mine)
    if mine:
        raise Fail('not applied: your working tree has changes inside "in: %s" (%s), so the winner was written as a '
                   'patch: %s\n  apply it when ready: git apply %s; then %s done %s'
                   % (o.get('in'), ', '.join(mine[:6]), path, shlex.quote(path), ODD, o.slug))
    if err:
        raise Fail('not applied (git apply: %s), so the winner was written as a patch: %s' % (err, path))
    print('applied to your working tree: %s' % (', '.join(w['delta'][:8]) or 'nothing') + (
        '\nnext: %s done %s, then %s gate (the attempt was verified in its worktree; done records it here)'
        % (ODD, o.slug, ODD) if hint else ''))
    return path


def _agents(cfg, given, what):
    if not given or not all(c.strip() for c in given):
        raise CouldNotRun('no agent to %s: set "agents": ["<command>", ...] in .odd/config.json (each command runs in '
                          'an attempt\'s worktree; {prompt_file} in it becomes the prompt\'s path, else the prompt is on '
                          'stdin), or pass %s' % (what, '--agent "<command>"' if what == 'race' else '--agents "<cmd1>,<cmd2>"'))
    return given


def _none_verified(msg, attempts, a):
    """The Fail of a race or cascade with no verified attempt: `msg`, then the next: block of every attempt's items."""
    items = [('attempt %s %s' % (at['name'], k), v) for at in attempts for k, v in at.get('items', [])]
    return Fail('%s\n%s' % (msg, next_block(items, _rerun(a))), items)


def _race_n(agents, n, flag):
    """How many attempts: `n` as given, else one per configured agent, or 3 for one agent."""
    n = n if n is not None else (len(agents) if len(agents) > 1 else 3)
    if not 1 <= n <= 32:
        raise CouldNotRun('%s must be between 1 and 32' % flag)
    return n


def _race_run(root, cfg, slug, base_arg, agents, n):
    """One race: n attempts (the agents in turn), judged and ranked, the table printed; nothing applied. Shared by race
    and chain. Returns (o, head, attempts, ranked, the winner's patch, keep)."""
    o, head, base, fixed = _race_start(root, cfg, slug, base_arg)
    keep = _keep(root, 'race', o.slug)
    print('%s race %s: %d attempt(s) from %s, agents in parallel; each verified as %s done would, in its own worktree'
          % (ODD, o.slug, n, head[:10], ODD))
    attempts, ranked, patch, overhead = _attempts(root, cfg, o, base, head, fixed,
                                                  [agents[i % len(agents)] for i in range(n)], keep,
                                                  _prompt(o, cfg, fixed), [str(i) for i in range(1, n + 1)])
    _table(attempts, ranked)
    print('setup and clean-up: %s s per attempt (worktree, copies, start commit, removal); prompts and agent logs: %s'
          % (round(overhead / n, 2), keep))
    return o, head, attempts, ranked, patch, keep


def cmd_race(a, root):
    cfg = load_config(root)
    agents = _agents(cfg, [a.agent] if a.agent else cfg['agents'], 'race')
    o, head, attempts, ranked, patch, keep = _race_run(root, cfg, a.slug, a.base, agents, _race_n(agents, a.n, '--n'))
    if not ranked:
        raise _none_verified('no attempt was verified; each one\'s reason is in the table above', attempts, a)
    print('winner: attempt %s, %s' % (ranked[0]['name'], _why_won(ranked)))
    _apply(root, o, head, ranked[0], patch, keep)


# ---------------------------------------------------------------- cascade: the cheapest agent first, escalate on proof

COST = re.compile(r'(?m)^odd-cost:\s*\$?(\d+(?:\.\d+)?)\s*$')
CASCADE_BEFORE = """
Earlier attempts at this outcome, by other agents, were NOT verified. This is what the checks found; do not repeat it:
%s

"""


def _cost(at):
    """The agent's own report of what the attempt cost: the last line "odd-cost: <usd>" it printed, else None."""
    try:
        with open(at['log'], 'rb') as f:
            f.seek(0, 2)
            f.seek(max(0, f.tell() - 65536))
            found = COST.findall(f.read().decode('utf-8', 'replace'))
    except OSError:
        return None
    return float(found[-1]) if found else None


def _short(cmd, width=44):
    cmd = ' '.join(os.path.basename(w) if '/' in w and not w.endswith('/') else w for w in cmd.split())  # paths as names
    return cmd if len(cmd) <= width else cmd[:width // 2 - 2] + '...' + cmd[-(width // 2 - 1):]


def _cascade_run(root, cfg, slug, base_arg, levels, n):
    """One cascade: the levels in order until one has a verified attempt, the table and cascade.json written; nothing
    applied or parked. Shared by cascade and chain. Returns (o, head, attempts, ranked, the winner's patch, keep,
    the path of cascade.json)."""
    o, head, base, fixed = _race_start(root, cfg, slug, base_arg)
    keep = _keep(root, 'cascade', o.slug)
    print('%s cascade %s: %d level(s), %d attempt(s) per level from %s; the next level runs only when no attempt at this '
          'one is verified as %s done would' % (ODD, o.slug, len(levels), n, head[:10], ODD))
    base_text, before, history = _prompt(o, cfg, fixed), [], []
    more = (('agent', lambda at: _short(at['cmd'])),
            ('cost', lambda at: 'not reported' if at['cost'] is None else '$%g' % at['cost']))
    for lv, cmd in enumerate(levels, 1):
        text = base_text + (CASCADE_BEFORE % '\n'.join(before) if before else '')
        print('level %d of %d: %s' % (lv, len(levels), _short(cmd, 80)))
        attempts, ranked, patch, overhead = _attempts(root, cfg, o, base, head, fixed, [cmd] * n, keep, text,
                                                      ['%d' % lv] if n == 1 else ['%d.%d' % (lv, i) for i in range(1, n + 1)])
        for at in attempts:
            at['cost'] = _cost(at)
        history += attempts
        if ranked:
            break
        for at in attempts:
            before.append('- level %d (agent `%s`), attempt %s: %s\n%s' % (lv, cmd, at['name'], (at.get('detail') or at['why'])[:1500],
                                                                       next_block(at.get('items', []), '%s done %s' % (ODD, o.slug))))
    _table(history, ranked, more)
    costs = [at['cost'] for at in history if at['cost'] is not None]
    print('cost reported by the agents: %s; prompts and agent logs: %s' % (
        '$%g over %d of %d attempt(s)' % (round(sum(costs), 6), len(costs), len(history)) if costs else 'none', keep))
    record_path = os.path.join(keep, 'cascade.json')
    write_json(record_path, {'slug': o.slug, 'head': head, 'levels': levels, 'attempts': [
        {k: at.get(k) for k in ('name', 'cmd', 'why', 'detail', 'items', 'lines', 'agent_s', 'verify_s', 'cost')} for at in history]})
    return o, head, history, ranked, patch, keep, record_path


def _levels(cfg, agents):
    return _agents(cfg, [c for c in agents.split(',') if c.strip()] if agents else cfg['agents'], 'cascade')


def cmd_cascade(a, root):
    cfg = load_config(root)
    levels = _levels(cfg, a.agents)
    n = a.race if a.race is not None else 1
    if not 1 <= n <= 32:
        raise CouldNotRun('--race must be between 1 and 32')
    o, head, history, ranked, patch, keep, record_path = _cascade_run(root, cfg, a.slug, a.base, levels, n)
    if not ranked:
        o.f['parked'] = ' '.join(('odd cascade: no level verified (%s): %s' % (now()[:10], '; '.join(
            'level %s (%s): %s' % (at['name'], _short(at['cmd']), at['why']) for at in history))).split())
        o.save()
        raise _none_verified('parked %s after the last level: no attempt was verified; each one\'s reason is in the table '
                             'above, in the "parked:" line of %s and in %s. Nothing was applied. To try again, delete the '
                             '"parked:" line.' % (o.slug, o.rel, record_path), history, a)
    print('verified at level %s: %s' % (ranked[0]['name'].split('.')[0], _why_won(ranked)))
    _apply(root, o, head, ranked[0], patch, keep)



# ---------------------------------------------------------------- chain: a long task as a sequence of proven outcomes

CHECKPOINT = 'odd: %s proven'


def _chain(root, ticket):
    """(the chain file's path relative to root, its slugs in order): .odd/chains/<ticket>.md holds one outcome slug
    per line; blank lines, # comments and a leading "- " or "* " are allowed. Every slug must name an outcome."""
    rel = '.odd/chains/%s.md' % ticket
    if '/' in ticket or not os.path.isfile(os.path.join(root, rel)):
        raise CouldNotRun('no chain %s: write %s with one outcome slug per line, in order' % (ticket, rel))
    slugs = [re.sub(r'^[-*]\s+', '', line.strip()) for line in read_text(os.path.join(root, rel)).splitlines()]
    slugs = [x for x in slugs if x and not x.startswith('#')]
    if not slugs or len(set(slugs)) != len(slugs):
        raise CouldNotRun('%s must list each outcome slug once, one per line' % rel)
    for x in slugs:
        try:
            Outcome.load(root, x)
        except Fail as e:
            raise CouldNotRun('%s: %s' % (rel, e))
    return rel, slugs


def _checkpoint(root, slug):
    """The short hash of the newest commit in HEAD's history whose subject is exactly "odd: <slug> proven", or None,
    also when a newer commit reverts it (git revert's subject: Revert "odd: <slug> proven")."""
    want = CHECKPOINT % slug
    for line in git(root, 'log', '--format=%h %s', '-F', '--grep=' + want, 'HEAD').splitlines():
        h, _, subject = line.partition(' ')
        if subject in (want, 'Revert "%s"' % want):
            return h if subject == want else None
    return None


def _dirty(root):
    """Every path that differs from HEAD in the working tree or the index, plus untracked files."""
    return set(zlist(root, *DIFF, '--name-only', 'HEAD')) | set(zlist(root, 'ls-files', '--others', '--exclude-standard', '-z'))


def _chain_step(root, cfg, a, slug, agents, n, rel):
    """One outcome of a chain: race (or cascade) it, apply the winner, verify it here as done would, and commit the
    checkpoint: the winner's files, the outcome file, the chain file and the test files its proof names or its seal
    holds. Any failure after the winner was applied reverses the winner's patch, so the tree is back at the last
    checkpoint with the user's other files as they were."""
    if a.cascade:
        o, head, attempts, ranked, patch, keep, _ = _cascade_run(root, cfg, slug, a.base, agents, n)
    else:
        o, head, attempts, ranked, patch, keep = _race_run(root, cfg, slug, a.base, agents, n)
    if not ranked:
        e = _none_verified('no attempt at %s was verified' % slug, attempts, a)
        e.why = '; '.join('attempt %s: %s' % (at['name'], at['why']) for at in attempts)
        raise e
    path = _apply(root, o, head, ranked[0], patch, keep, hint=False)
    try:
        s = survey(root, a.base)
        res = prove(root, o, s)
        _verified(root, o, s, res)
        sealed = [e.rsplit('@', 1)[0] for e in o.get('sealed').split(', ')[1:]] if o.get('sealed') else []
        dirty = sorted(_dirty(root))
        paths = sorted(set(dirty) & (set(ranked[0]['delta']) | {o.rel, rel} | set(sealed) |
                                     set(proof_runs(o.get('proof'), dirty))))
        if paths:
            git(root, 'add', '--', *paths)
        git(root, 'commit', '-q', '--only', '--allow-empty', '-m', CHECKPOINT % slug, '--', *paths)
    except BaseException:
        err = _patch(root, patch, path, reverse=True)
        if err:
            print('odd: the rollback failed (git apply -R: %s); the winner\'s patch is %s' % (err, path), file=sys.stderr)
        raise
    print('%s: verified and committed as the checkpoint %s. %s' % (slug, rev(root, 'HEAD')[:7], _describe(o, res)))


def cmd_chain(a, root):
    cfg = load_config(root)
    rel, slugs = _chain(root, a.ticket)
    if a.cascade:
        agents, n = _levels(cfg, a.agents), a.race if a.race is not None else 1
        _race_n(agents, n, '--race')
    else:
        agents = _agents(cfg, [c for c in a.agents.split(',') if c.strip()] if a.agents else cfg['agents'], 'chain')
        n = _race_n(agents, a.race, '--race')
    if not rev(root, 'HEAD'):
        raise CouldNotRun('each checkpoint is a commit on top of one: commit first')
    dirty = _dirty(root)
    other = sorted(dirty - {rel} - {Outcome(root, x).rel for x in slugs} - set(classify(sorted(dirty), cfg)[2]))
    if other:
        raise CouldNotRun('your working tree has changes outside the chain\'s outcomes and their proofs: %s%s. Commit or '
                          'stash them first, so a rollback to the last checkpoint can never touch your work'
                          % (', '.join(other[:6]), ', ...' if len(other) > 6 else ''))
    status, stop = collections.OrderedDict(), None
    for i, slug in enumerate(slugs, 1):
        cp = _checkpoint(root, slug)
        if cp or stop:
            status[slug] = 'proven (%s)' % cp if cp else 'not started'
            continue
        print('%s chain %s: outcome %d of %d: %s' % (ODD, a.ticket, i, len(slugs), slug))
        try:
            _chain_step(root, cfg, a, slug, agents, n, rel)
            status[slug] = 'proven (%s)' % rev(root, 'HEAD')[:7]
        except Fail as e:
            o = Outcome.load(root, slug)
            o.f['parked'] = ' '.join(('odd chain %s (%s): %s' % (a.ticket, now()[:10], getattr(e, 'why', '') or
                                                                str(e).strip().split('\n')[0])).split())
            o.save()
            status[slug], stop = 'parked: %s' % o.parked, (slug, e, 'parked; the reasons are in the "parked:" line of ' + o.rel)
        except CouldNotRun as e:
            status[slug], stop = 'stopped: could not run: %s' % str(e).split('\n')[0][:160], (slug, e, 'stopped, not parked')
    wide = max(len(x) for x in slugs)
    lines = ['chain %s:' % a.ticket] + ['  %s  %s' % (x.ljust(wide), status[x][:200]) for x in slugs]
    if not stop:
        print('\n'.join(lines))
        return 0
    slug, e, what = stop
    head = ('the chain stopped at %s, %s. The working tree is at the last checkpoint; a rerun continues from the first '
            'unproven outcome.' % (slug, what))
    if isinstance(e, CouldNotRun):
        raise CouldNotRun('%s\n%s\n%s' % (str(e), head, '\n'.join(lines)))
    raise Fail('%s\n%s\n%s' % (head, '\n'.join(lines), next_block(e.items, _rerun(a))), e.items)


# ---------------------------------------------------------------- spec: another agent writes the proof, sealed red

SPEC_PROMPT = """You write the PROOF for one outcome, and ONLY the proof: a test that another agent's code must later
make pass. You work in your own copy of the repository (the current directory); odd brings back only your test files.

Outcome: %(outcome)s
Proof command (it must exit 0 only when the outcome holds): %(proof)s
The code will change files inside: %(ins)s. Do NOT change them, and do not write the implementation.
Write the test files the proof command runs, under a test path (%(tests)s).

The proof must FAIL now, before the code exists, and fail because the outcome does not hold yet (not because of a typo
or a missing import of the test framework). Test what the outcome sentence says a person observes, not one way of
building it. odd runs the proof command here when you exit: if it passes, or does not run, your proof is refused.
Do not commit, push or run odd here.
"""
SPEC_BEFORE = """
Earlier proofs for this outcome were refused. Do not repeat this:
%s
"""
SECRET = re.compile(r'(?i)key|token|secret|passw|auth|cred')


def _who(cmd):
    """The proof author's name for the outcome file: the command, without environment assignments, the values of
    options that look like credentials, or {prompt_file}; shortened."""
    try:
        words = shlex.split(cmd)
    except ValueError:
        words = cmd.split()
    out, skip = [], False
    for w in words:
        if skip or re.match(r'^[A-Za-z_]\w*=', w) or w == '{prompt_file}':
            skip = False
            continue
        if w.startswith('-') and SECRET.search(w.split('=')[0]):
            skip = '=' not in w
            continue
        out.append(w)
    return _short(' '.join(out)) or 'an agent'


def _proof_check(root, cfg, o, at, fixed):
    """Why the proof an author wrote in its worktree is refused, or '' with at['tests'] set: test files only, nothing
    it must leave alone, and the proof runs and fails there (red first)."""
    wt, start = at['wt'], at['start']
    if at['rc'] is None:
        return 'timed out after %ss (killed with its process group)' % cfg['race_timeout']
    why = _settle(root, at)
    if why:
        return why
    control, _, tests, product = classify(changed_files(wt, start), cfg)
    moved = sorted(set(zlist(wt, *DIFF, '--name-only', start, '--', *fixed)) | set(control))
    if moved or product:
        return 'changed %s; the proof author writes test files only' % ', '.join((moved + product)[:6])
    if not tests:
        return 'wrote no test file under a test path (%s)' % ', '.join(cfg['test_globs'][:4])
    rc, tail, _ = run_proof(wt, o.get('proof'), cfg['proof_timeout'])
    if unrunnable(rc):
        return 'the proof did not run to completion (%s), so it is not red:\n%s' % (
            'timeout' if rc is None else 'exit %d' % rc, _indent(tail))
    if rc == 0:
        return 'the proof passes before the code, so it cannot show the code is needed: %s' % o.get('proof')
    at['tests'], at['red'] = tests, says(tail)
    return ''


def cmd_spec(a, root):
    cfg = load_config(root)
    tries = a.tries if a.tries is not None else cfg['proof_tries']
    if not 1 <= tries <= 32:
        raise CouldNotRun('--tries must be between 1 and 32')
    if not a.proof_by.strip():
        raise CouldNotRun('--proof-by needs the proof author\'s command ({prompt_file} in it becomes the prompt\'s '
                          'path, else the prompt is on stdin)')
    try:
        o = Outcome.load(root, a.slug)
    except Fail as e:
        raise CouldNotRun(str(e))
    if o.get('sealed'):
        raise CouldNotRun('%s is sealed already; to have the proof written again, delete its "sealed:" line and its '
                          'test files first' % o.rel)
    head = rev(root, 'HEAD')
    if not head:
        raise CouldNotRun('the proof author works from a commit and there is none yet: commit first')
    fixed = [o.rel] + (['.odd/config.json'] if os.path.isfile(odd_dir(root, 'config.json')) else [])
    keep = _keep(root, 'spec', o.slug)
    who = _who(a.proof_by)
    text = SPEC_PROMPT % dict(outcome=o.get('outcome'), proof=o.get('proof'), ins=o.get('in'), slug=o.slug,
                              tests=', '.join(cfg['test_globs']))
    print('%s spec %s: %s writes the proof in its own worktree (at most %d tries); it must fail before the code'
          % (ODD, o.slug, who, tries))
    run, reasons, patch, done, p = state_dir(root, 'race', 'run-%d' % os.getpid()), [], '', queue.Queue(), None
    try:
        for i in range(1, tries + 1):
            at = dict(cmd=a.proof_by, wt=_worktree(root, run, str(i), head, fixed), prompt=os.path.join(
                keep, 'prompt-%d.md' % i), log=os.path.join(keep, 'agent-%d.log' % i))
            at['start'] = rev(at['wt'], 'HEAD')
            with open(at['prompt'], 'w', encoding='utf-8') as f:
                f.write(text + (SPEC_BEFORE % '\n'.join(reasons) if reasons else ''))
            p = _launch(at, cfg['race_timeout'], done)
            _next(done)
            why = _proof_check(root, cfg, o, at, fixed)
            print('  try %d: the author ended after %ss; %s' % (i, at['agent_s'], ('refused: ' + why.split('\n')[0])
                                                                  if why else 'red: ' + at['red']))
            if not why:
                git(at['wt'], 'add', '-A', '--', *at['tests'])
                patch = git(at['wt'], 'diff', '--cached', '--binary', '--no-renames', at['start'], '--', *at['tests'])
                break
            reasons.append('- try %d: %s' % (i, why[:1500]))
    finally:
        if p is not None:
            _killpg(p)
        _drop_run(root, run)
    if not patch:
        o.f['parked'] = ' '.join(('odd spec: no proof that fails before the code after %d tries by %s (%s): %s' % (
            tries, who, now()[:10], '; '.join(r[2:].split('\n')[0] for r in reasons))).split())
        o.save()
        record(root, o.slug, ok=False, why=o.f['parked'][:300])
        raise Fail('parked %s: %s wrote no proof that fails before the code in %d tries; the reasons are in the '
                   '"parked:" line of %s; prompts and logs: %s. Nothing was brought back.' % (o.slug, who, tries, o.rel, keep))
    path = os.path.join(keep, 'proof.patch')
    err = _patch(root, patch, path)
    if err:
        raise Fail('the proof was not brought back (git apply: %s); it is in %s' % (err, path))
    print('brought back: %s' % ', '.join(at['tests']))
    try:
        cmd_seal(argparse.Namespace(slug=o.slug, base=a.base), root)
    except (Fail, CouldNotRun):
        _patch(root, patch, path, reverse=True)  # the proof goes back out; the user's tree is as it was
        raise
    o = Outcome.load(root, o.slug)
    o.f['proof-by'] = who
    o.save()
    record(root, o.slug, proof_by=who, tries=len(reasons) + 1)
    print('proof-by: %s (recorded in %s). Next: %s race %s or %s cascade %s; an attempt that edits the sealed proof is '
          'refused.' % (who, o.rel, ODD, o.slug, ODD, o.slug))


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
    what the proof said with the change taken out, and its proof strength: k of n small breaks caught."""
    md = [MARKER, '### odd gate: %s' % f['verdict']] + (['%s base %s, %s file(s) changed, %s outcome(s) in this change.' % (
        'Every proof run again (`--recompute`);' if f['recompute'] else 'Recorded local results;',
        _cell((f['base'] or 'none')[:10], True), f['changed'], f['in_play'])] if 'changed' in f else [])
    outs, survived = f.get('outcomes', []), []
    if outs:
        md += ['', '| outcome | proof | with the change taken out | proof strength |', '|---|---|---|---|']
    for o in outs:
        st = o.get('strength')
        if o['state'] == 'ok' and o.get('skip'):
            red = 'not taken out (skip: %s); %s line(s) not verified' % (_cell(o['skip'].split('-', 1)[-1]), o.get('lines'))
        elif o['state'] == 'ok':
            red = 'the proof failed: %s (%s file(s), %s line(s))' % (_cell(o.get('red_says') or '(no output)', True),
                                                                  o.get('files'), o.get('lines'))
        else:
            red = '**%s**: %s' % ({'fail': 'not shown', 'asked': 'waiting for an answer'}.get(o['state'], 'parked'),
                                  _cell(o.get('why', '').split('\n')[0][:200]))
        red += '; **kind changed from bug**' if o.get('kind_was') else ''
        score = '-'
        if st:
            score = '%d of %d' % (st['killed'], st['killed'] + len(st['survivors']))
            score += ''.join('; %d %s' % (len(st[k]), w) for k, w in (('survivors', 'survived'), ('unrun', 'could not run')) if st[k])
            score += '; ' + _cell(lines_run(st)) if st.get('not_run') or st.get('not_measured') else ''
            survived += st['survivors']
        md.append('| **%s**: %s | %s | %s | %s |' % (o['slug'], _cell(o.get('outcome') or ''), _cell(o.get('proof') or '', True),
                                                    red, score))
    if survived:
        md += ['', 'Survived (each a changed line the proof does not depend on):'] + ['- ' + _cell(w, True, False) for w in survived]
    for r in f.get('requirements', []):
        md += ['', '**Requirements %s**: %d of %d covered.' % (_cell(r['ticket'], True, False), len(r['covered']),
                                                               len(r['text']))]
        md += ['- %s: %s, covered by %s' % (k, _cell(v, table=False), ', '.join(r['covered'][k])) if k in r['covered'] else
               '- %s: %s, **not covered**' % (k, _cell(v, table=False)) for k, v in r['text'].items()]
    if f.get('guards'):
        md += ['', '**Guards** (earlier outcomes whose files this change touches; each proof ran again):']
        md += ['- **%s** (proven in %s): %s' % (g['slug'], _cell(g['commit'], True, False), 'passes' if g['state'] == 'ok'
               else '**now fails**: ' + _cell(g.get('why', ''), True, False)) for g in f['guards']]
    if f.get('lane'):
        md += ['', 'Auto-merge lane: ' + ('yes' if f['lane'] == 'auto' else 'no, because ' + '; '.join(
            _cell(r, table=False) for r in f.get('lane_reasons') or ['(no reason recorded)']))]
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


def cmd_ask(a, root):
    q = ' '.join(a.question.split())
    if len(q) < 15 or not q.endswith('?'):
        raise Fail('ask one precise question, ending in "?", that someone can answer without asking you back')
    o = Outcome.load(root, a.slug)
    o.f['asked'] = q
    o.save()
    print('%s: asked, waiting for an answer. Put the question in your report and stop work on this outcome: the gate '
          'reports it as waiting, not failed, and it covers no files until answered. To answer: write the answer into '
          'the outcome (its sentence, proof or notes), then delete the "asked:" line of %s.' % (a.slug, o.rel))


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
    print('%-28s %-8s %9s %8s %8s %-7s %s' % ('outcome', 'state', 'attempts', 'passed', 'escaped', 'sealed', 'proof strength'))
    kind = {}  # slug -> how strong the latest verification recorded here said the proof was
    for o in outs:
        ev = evidence(root, o.slug)
        seals = [e['seal'] for e in ev if e.get('seal')]
        o.sealed_here = 'sealed' if o.get('sealed') and o.get('sealed') in seals else ('unseen' if o.get('sealed') else '-')
        ev = [e for e in ev if 'ok' in e]  # attempts are done runs; a seal is not one
        st = ([e['strength'] for e in ev if e.get('ok') and e.get('strength')] or [None])[-1]
        n = st and st['killed'] + len(st['survivors'])
        kind[o.slug] = 'survived' if n and st['survivors'] else ('caught' if n else '')
        state = 'parked' if o.parked else ('asked' if o.asked else ('skip' if o.skip else ''))
        print('%-28s %-8s %9d %8d %8d %-7s %s' % (o.slug, state, len(ev), sum(1 for e in ev if e.get('ok')), escapes(o),
                                               o.sealed_here, '%d of %d' % (st['killed'], n) if n else '-'))
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
    print('  ' + '; '.join([split('proof strength n of n', lambda o: kind[o.slug] == 'caught'),
                            split('a mutant survived', lambda o: kind[o.slug] == 'survived'),
                            split('not measured here', lambda o: not kind[o.slug])]))


# when parking is the answer: the method, `odd park` and the Stop hook say it in the same words (ImpossibleBench's
# strict stop-and-explain wording plus an abort path cut cheating; docs/evidence/14-research.md section 2.3)
PARK_WHEN = 'the task cannot be done as asked or the proof cannot honestly pass'
METHOD = '''## Outcome-driven development (odd)

Work here is done when a proof says so, not when it looks finished. `odd` below means `python3 .odd/odd.py`.

For any change of more than a few lines, on a branch of its own:

1. State the outcome before writing code: one sentence saying who observes what, a command that exits 0 only when
   that is true, and the files the change may touch. If the outcome cannot be made checkable from the ticket, ask
   one precise question instead of guessing (`odd ask <slug> "<question>"` records it), and stop there. List the ticket's requirements first, one per line, in `.odd/requirements/<ticket>.md`
   (`R1: ...`), and cover each with an outcome (`--covers R1,R2`).
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
                '%s %s' % (o.slug, 'parked' if o.parked else ('waiting for an answer' if o.asked else 'in this change')) for o in (s['inplay'] if s else [])))
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
    s.add_argument('--proof', help='a command that exits 0 only when the outcome holds, or "auto": one picked from the '
                   'test runner the repository uses (required, except with --kind refactor: the whole suite)')
    s.add_argument('--test', metavar='PATH', help='with --proof auto: the test file the proof runs')
    s.add_argument('--in', dest='in_', required=True, action='append', help='globs, comma-separated (may be repeated)')
    s.add_argument('--covers', metavar='IDS', help='the requirements this outcome covers, comma-separated: R1, R3 (from '
                   '.odd/requirements/<ticket>.md), or <ticket>:R1')
    s.add_argument('--kind', choices=KINDS, help='bug: seal and done require the proof to fail at the base revision '
                   '(reproduce first); feature: the proof covers the new behaviour; refactor: the proof defaults to '
                   'the whole suite and the take-out check is skipped. Prints a hint after creation')
    s = sub.add_parser('seal')
    s.add_argument('slug')
    s.add_argument('--base', help='measure from this revision instead of the target branch')
    s = sub.add_parser('done')
    s.add_argument('slug')
    s.add_argument('--base', help='measure from this revision instead of the target branch')
    s = sub.add_parser('race')
    s.add_argument('slug')
    s.add_argument('--n', type=int, help='how many attempts (default: one per configured agent, or 3 for one agent)')
    s.add_argument('--agent', help='the agent command for every attempt, instead of "agents" in .odd/config.json')
    s.add_argument('--base', help='measure from this revision instead of the target branch')
    s = sub.add_parser('cascade')
    s.add_argument('slug')
    s.add_argument('--agents', help='agent commands, cheapest first, comma-separated (default: "agents" in .odd/config.json)')
    s.add_argument('--race', type=int, help='attempts per level, in parallel (default 1)')
    s.add_argument('--base', help='measure from this revision instead of the target branch')
    s = sub.add_parser('chain')
    s.add_argument('ticket')
    s.add_argument('--race', type=int, help='attempts per outcome in parallel (default: as odd race; with --cascade, per '
                   'level, default 1)')
    s.add_argument('--cascade', action='store_true', help='attempt each outcome as odd cascade does: the agents in order')
    s.add_argument('--agents', help='agent commands, comma-separated (default: "agents" in .odd/config.json)')
    s.add_argument('--base', help='measure from this revision instead of the target branch')
    s = sub.add_parser('spec')
    s.add_argument('slug')
    s.add_argument('--proof-by', required=True, metavar='CMD', help='the agent command that writes only the proof '
                   '(in practice a stronger model); {prompt_file} becomes the prompt\'s path, else stdin')
    s.add_argument('--tries', type=int, help='tries for a proof that fails before the code (default: "proof_tries", 3)')
    s.add_argument('--base', help='measure from this revision instead of the target branch')
    s = sub.add_parser('gate')
    s.add_argument('--base')
    s.add_argument('--recompute', action='store_true')
    s.add_argument('--summary', metavar='FILE', help='also write the result as Markdown, for a pull request')
    s.add_argument('--json', metavar='FILE', help='also write the result as JSON')
    s = sub.add_parser('park')
    s.add_argument('slug')
    s.add_argument('reason')
    s = sub.add_parser('ask')
    s.add_argument('slug')
    s.add_argument('question', help='one precise question; delete the "asked:" line once it is answered')
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
        sys.stdout.flush()  # so, with both on one pipe (the MCP server), the next: block is the last thing printed
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
