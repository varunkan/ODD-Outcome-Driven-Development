#!/usr/bin/env python3
"""odd: outcome-driven development. "Done" is recomputed from the code, not claimed.

An outcome is one sentence, a proof command and a boundary, kept in .odd/outcomes/<slug>.md. It is verified when the
proof passes on the tree as it is, fails on the same tree with the change taken out, and passes again once the
change is put back. `odd gate` checks that every changed product file is inside the boundary of one verified
outcome; with --recompute (CI) it trusts nothing recorded.

  odd init [--claude-hooks]                               install or repair
  odd new <slug> "<outcome>" --proof "<command>" --in "<globs>"
  odd done <slug>                                         exit 0 verified, 1 not shown, 2 could not run
  odd gate [--base REF] [--recompute]                     exit 0 pass, 1 fail, 2 could not run
  odd park <slug> "<reason>"                              blocked, or cannot be done as specified
  odd stats                                               counts (self-reported)

Needs a POSIX shell, git 2.23+ and Python 3.8+. One file, standard library only, so a project vendors it as
.odd/odd.py. Design and limits: DESIGN.md.
"""
import argparse
import collections
import datetime
import hashlib
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import time

VERSION = '0.2.0'
DEFAULTS = {
    'trivial_lines': 25,   # product lines that may change outside any outcome (a per-change budget)
    'exempt': ['.odd/outcomes/**', '**/*.md', 'LICENSE*', '.gitignore', '.gitattributes',
               '**/*.lock', '**/package-lock.json', '**/pnpm-lock.yaml', '**/go.sum'],
    'test_globs': ['**/tests/**', '**/test/**', '**/spec/**', '**/__tests__/**', '**/test_*.py', '**/*_test.*',
                   '**/*.test.*', '**/*.spec.*'],   # a proof's own files: never taken out, need no outcome
    'proof_timeout': 900,  # seconds per proof run
    'default_branch': None,
}
CONTROL = ('.odd/odd.py', '.odd/config.json')   # no outcome needed; always reported; read from the base in CI
FIELDS = ('outcome', 'proof', 'in', 'counterfactual', 'parked', 'escaped')
SLUG = re.compile(r'^[a-z0-9][a-z0-9._-]{0,63}$')
BIG = 10 ** 6  # a binary file or submodule pointer is never a "small change"
ODD = 'odd'    # how the tool was invoked, for messages a reader can paste


class Fail(Exception):
    """The outcome is not shown (exit 1)."""


class CouldNotRun(Exception):
    """Nothing was established (exit 2). Never reported as a pass."""


# ---------------------------------------------------------------- git, paths, settings

def sh(args, cwd, **kw):
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True, **kw)


def git(root, *args):
    r = sh(['git'] + list(args), root)
    if r.returncode != 0:
        raise CouldNotRun('git %s: %s' % (' '.join(args[:3]), (r.stderr or r.stdout).strip()[:300]))
    return r.stdout


def zlist(root, *args):
    return [x for x in git(root, *args).split('\0') if x]


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


def glob_re(pat):
    """Globs are relative to the repository root: * and ? stay inside one path segment, ** crosses segments, and a
    pattern that names a directory covers everything under it."""
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
    return re.compile('^' + out + '(?:/.*)?$')


def matches(path, globs):
    return any(glob_re(g).match(path) for g in globs if g.strip())


def split_globs(s):
    return [g.strip() for g in (s or '').split(',') if g.strip()]


def load_config(root, base=None):
    """Settings. When recomputing they come from the base revision, so a change cannot loosen its own gate; a
    project adopting odd in this very change gets the defaults."""
    cfg = dict(DEFAULTS)
    try:
        if base:
            r = sh(['git', 'show', '%s:.odd/config.json' % base], root)
            text = r.stdout if r.returncode == 0 else '{}'
        else:
            with open(odd_dir(root, 'config.json')) as f:
                text = f.read()
        cfg.update({k: v for k, v in json.loads(text).items() if k in DEFAULTS})
    except (OSError, ValueError):
        pass
    return cfg


def find_base(root, cfg, arg=None):
    """The one revision everything is measured from: where this branch left the target branch."""
    if not rev(root, 'HEAD'):
        return None  # no commits yet: everything is new
    ref = arg or os.environ.get('ODD_BASE')
    if ref:
        cands = [ref]
    else:
        d = cfg.get('default_branch')
        if not d:
            r = sh(['git', 'symbolic-ref', '--short', 'refs/remotes/origin/HEAD'], root)
            d = r.stdout.strip().split('/', 1)[-1] if r.returncode == 0 and r.stdout.strip() else None
        names = [d] if d else ['main', 'master']
        cands = ['origin/' + n for n in names] + names
    for c in cands:
        if rev(root, c):
            mb = sh(['git', 'merge-base', 'HEAD', c], root)
            if mb.returncode == 0 and mb.stdout.strip():
                return mb.stdout.strip()
            raise CouldNotRun('HEAD and %s share no history here (a shallow clone?). Fetch it: git fetch --unshallow '
                              '(in CI: a full-history checkout, fetch-depth: 0)' % c)
    if ref:
        raise CouldNotRun('base revision %r not found. Fetch it: git fetch origin %s' % (ref, ref.split('/')[-1]))
    raise CouldNotRun('cannot tell which branch this work leaves from (no main, master or origin/HEAD): pass --base '
                      '<branch>, or set "default_branch" in .odd/config.json')


EMPTY_TREE = '4b825dc642cb6eb9a060e54bf8d69288fbee4904'


def changed_files(root, base):
    """Every path that differs from the base in the working tree (committed, staged or not), plus untracked files.
    A rename is a delete and an add. Computed from git, so files written through a shell are seen like any other."""
    names = set(zlist(root, 'diff', '--name-only', '--no-renames', '-z', base or EMPTY_TREE))
    names |= set(zlist(root, 'ls-files', '--others', '--exclude-standard', '-z'))
    return sorted(names)


def changed_lines(root, base, path):
    if os.path.isdir(os.path.join(root, path)):
        return BIG  # a submodule pointer
    r = sh(['git', 'diff', '--numstat', '--no-renames', base or EMPTY_TREE, '--', path], root)
    line = r.stdout.strip().splitlines()[0] if r.stdout.strip() else ''
    if line:
        a, d = line.split('\t')[:2]
        return BIG if '-' in (a, d) else int(a) + int(d)
    try:  # untracked
        with open(os.path.join(root, path), 'rb') as f:
            data = f.read()
        return BIG if b'\0' in data[:8000] else data.count(b'\n') + (1 if data and not data.endswith(b'\n') else 0)
    except OSError:
        return BIG


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
        with open(o.path, encoding='utf-8') as f:
            lines = f.read().split('\n')
        if not lines or lines[0].strip() != '---':
            raise Fail('%s: must start with a --- line' % o.rel)
        key, n = None, 1
        while n < len(lines) and lines[n].strip() != '---':
            line = lines[n]
            m = re.match(r'^([a-z_]+):\s?(.*)$', line)
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

    @property
    def parked(self):
        return self.get('parked')

    @property
    def skip(self):
        v = self.get('counterfactual')
        return v if v.lower().startswith('skip') else ''

    def save(self):
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.path, 'w', encoding='utf-8') as f:
            f.write('---\n' + ''.join('%s: %s\n' % kv for kv in self.f.items()) + '---\n' + self.notes)


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


def content_hash(root, cfg, o, changed):
    """Identity of what was verified: the proof, the boundary, the bytes of every file inside it and of every
    changed test file. A commit, or an edit to a file outside it, leaves the hash unchanged."""
    h = hashlib.sha256()
    for k in ('proof', 'in', 'counterfactual'):
        h.update((k + '=' + o.get(k) + '\n').encode())
    listed = zlist(root, 'ls-files', '-c', '-o', '--exclude-standard', '-z')
    for path in sorted(p for p in set(listed) if matches(p, o.ins) or (p in changed and matches(p, cfg['test_globs']))):
        try:
            with open(os.path.join(root, path), 'rb') as f:
                h.update(path.encode() + b'\0' + hashlib.sha256(f.read()).digest())
        except OSError:
            h.update(path.encode() + b'\0gone')
    return h.hexdigest()[:20]


def last_ok(root, slug):
    ev = [e for e in evidence(root, slug) if e.get('ok')]
    return ev[-1] if ev else None


# ---------------------------------------------------------------- proofs, and taking the change out

def run_proof(root, cmd, timeout):
    """(exit code or None on timeout, last lines of output, seconds). No environment variable marks the run."""
    t0 = time.time()
    kw = {'start_new_session': True} if os.name == 'posix' else {}
    p = subprocess.Popen(cmd, shell=True, cwd=root, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                         errors='replace', **kw)

    def kill():
        try:
            os.killpg(p.pid, signal.SIGKILL) if os.name == 'posix' else p.kill()
        except OSError:
            pass
    try:
        out, _ = p.communicate(timeout=timeout)
        return p.returncode, '\n'.join(out.strip().splitlines()[-20:])[-2000:], round(time.time() - t0, 1)
    except subprocess.TimeoutExpired:
        kill()
        p.communicate()
        return None, 'timed out after %ss' % timeout, round(time.time() - t0, 1)
    except BaseException:  # interrupted: do not leave the proof running while the tree is put back
        kill()
        raise


def pid_alive(pid):
    if os.name != 'posix':
        return True  # cannot ask safely there; the journal's age decides
    try:
        os.kill(int(pid), 0)
        return True
    except (OSError, ValueError):
        return False


def _state(path):
    """What is at a path right now: None, ['link', target] or ['file', sha256]."""
    if os.path.islink(path):
        return ['link', os.readlink(path)]
    if os.path.isfile(path):
        with open(path, 'rb') as f:
            return ['file', hashlib.sha256(f.read()).hexdigest()]
    return None


def _bump(path, after):
    """A modification time two seconds past anything this run saw, so caches keyed on it (Python bytecode, make)
    notice both the revert and the restore even when size and second are unchanged."""
    t = max(time.time(), after or 0) + 2
    try:
        os.utime(path, (t, t), follow_symlinks=False)
    except (OSError, NotImplementedError):
        pass
    return t


def put_back(jdir):
    """Undo a take-out from its journal. A path is put back only if it still holds exactly what the check left
    there; an edit made meanwhile stays, and the earlier version is kept beside the journal.
    Returns (paths put back, descriptions of displaced versions)."""
    jp = os.path.join(jdir, 'journal.json')
    if not os.path.isfile(jp):
        shutil.rmtree(jdir, ignore_errors=True)
        return 0, []
    with open(jp) as f:
        j = json.load(f)
    done, displaced = 0, []
    for e in j['files']:
        path = os.path.join(j['root'], e['path'])
        if 'left' in e and _state(path) != e['left']:
            if e['kind'] != 'none':
                keep = os.path.join(os.path.dirname(jdir), 'displaced-' + os.path.basename(jdir), e['path'])
                os.makedirs(os.path.dirname(keep), exist_ok=True)
                if e['kind'] == 'file':
                    shutil.copyfile(os.path.join(jdir, e['saved']), keep)
                else:
                    with open(keep, 'w') as f:
                        f.write(e['link'])
                displaced.append('%s (your earlier version is at %s)' % (e['path'], keep))
            continue
        if os.path.lexists(path):
            os.remove(path)
        if e['kind'] == 'file':
            os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
            shutil.copyfile(os.path.join(jdir, e['saved']), path)
            os.chmod(path, e['mode'])
            _bump(path, e.get('touched'))
        elif e['kind'] == 'link':
            os.symlink(e['link'], path)
        done += 1
    shutil.rmtree(jdir, ignore_errors=True)
    return done, displaced


def recover(root, timeout):
    """A check that was killed mid-run leaves a journal. Put the change back unless that check is still running.
    Returns a message when something was put back, so the caller stops and the tree can be looked at."""
    sd, msgs = state_dir(root), []
    for name in sorted(os.listdir(sd)) if os.path.isdir(sd) else []:
        jdir = os.path.join(sd, name)
        jp = os.path.join(jdir, 'journal.json')
        if not name.startswith('cf-') or not os.path.isfile(jp):
            continue
        try:
            with open(jp) as f:
                j = json.load(f)
        except ValueError:
            continue
        if pid_alive(j.get('pid', -1)) and time.time() - j.get('started', 0) < 3 * timeout + 120:
            continue
        n, displaced = put_back(jdir)
        msgs.append('an earlier check was interrupted while the change was taken out; %d file(s) were put back%s'
                    % (n, ('. Edited meanwhile and left as they are: ' + '; '.join(displaced)) if displaced else ''))
    return ' '.join(msgs)


def without_change(root, cfg, o, base, targets):
    """Run the proof with `targets` (this outcome's changed product files) taken out, in place, then put them back.
    Returns (exit code or None on timeout, output tail, seconds)."""
    ran = set()  # the command word of each step of the proof: `./check.sh && pytest x` runs ./check.sh and pytest
    for step in re.split(r'&&|\|\||[;|\n]', o.get('proof')):
        words = [w for w in step.split() if not re.match(r'^[A-Za-z_][A-Za-z0-9_]*=', w)]
        if words:
            ran.add(words[0][2:] if words[0].startswith('./') else words[0])
    named = [p for p in targets if p in ran]
    if named:
        raise CouldNotRun('the proof runs %s, which is part of the change and would be taken out by the check. Keep '
                          'what the proof runs under a test path (for example tests/).' % ', '.join(named))
    sd = state_dir(root)
    os.makedirs(sd, exist_ok=True)
    for name in os.listdir(sd):
        if name.startswith('cf-') and os.path.isfile(os.path.join(sd, name, 'journal.json')):
            raise CouldNotRun('another check is taking a change out of this working tree (%s); retry when it ends' % name)
    at_base = set(zlist(root, 'ls-tree', '-r', '--name-only', '-z', base, '--', *targets)) if base else set()
    jdir = os.path.join(sd, 'cf-%s-%d' % (o.slug, os.getpid()))
    os.makedirs(jdir)
    entries = []
    for n, p in enumerate(targets):
        full = os.path.join(root, p)
        e = {'path': p, 'kind': 'none', 'saved': None}
        if os.path.islink(full):
            e.update(kind='link', link=os.readlink(full))
        elif os.path.isfile(full):
            shutil.copyfile(full, os.path.join(jdir, str(n)))
            st = os.stat(full)
            e.update(kind='file', saved=str(n), mode=st.st_mode & 0o7777, mtime=st.st_mtime)
        elif os.path.isdir(full):
            shutil.rmtree(jdir, ignore_errors=True)
            raise CouldNotRun('%s is a directory entry (a submodule pointer?) and cannot be taken out: add '
                              '"counterfactual: skip - <reason>" to the outcome' % p)
        entries.append(e)
    journal = {'root': root, 'pid': os.getpid(), 'started': time.time(), 'files': entries}

    def save():
        with open(os.path.join(jdir, 'journal.json'), 'w') as f:
            json.dump(journal, f)
            f.flush()
            os.fsync(f.fileno())

    save()  # everything needed to undo is on disk before the first file is touched
    displaced = []
    try:
        try:
            for e in entries:  # removals first, then git writes the base versions (content, mode, links, filters)
                if e['path'] not in at_base and os.path.lexists(os.path.join(root, e['path'])):
                    os.remove(os.path.join(root, e['path']))
            back = [e['path'] for e in entries if e['path'] in at_base]
            if back:
                r = sh(['git', 'restore', '--source=' + base, '--worktree', '--'] + back, root)
                if r.returncode != 0:
                    raise CouldNotRun('git could not write the base versions (git 2.23 or newer is needed): %s'
                                      % r.stderr.strip()[:200])
            for e in entries:
                full = os.path.join(root, e['path'])
                e['left'] = _state(full)
                if e['left']:
                    e['touched'] = _bump(full, e.get('mtime'))
            save()
        except OSError as err:  # never run a proof on a half-reverted tree
            raise CouldNotRun('could not take the change out (%s); nothing was verified' % err)
        rc, tail, secs = run_proof(root, o.get('proof'), cfg['proof_timeout'])
    finally:
        _, displaced = put_back(jdir)
    if displaced:
        raise CouldNotRun('files changed while the check was running and were left as they are: ' + '; '.join(displaced))
    return rc, tail, secs


def verify(root, cfg, o, base, changed, say=lambda s: None):
    """Green, red with the change taken out, green again. Returns a result dict; raises Fail (the outcome is not
    shown) or CouldNotRun (nothing was established)."""
    _, _, _, product = classify(changed, cfg)
    targets = [p for p in product if matches(p, o.ins)]
    lines = sum(changed_lines(root, base, p) for p in targets)
    rc, tail, s1 = run_proof(root, o.get('proof'), cfg['proof_timeout'])
    if rc is None:
        raise CouldNotRun('the proof timed out (%ss): %s' % (cfg['proof_timeout'], o.get('proof')))
    if rc != 0:
        raise Fail('the proof fails (exit %d): %s\n%s' % (rc, o.get('proof'), _indent(tail)))
    res = {'files': len(targets), 'lines': lines, 'seconds': [s1], 'red_says': '', 'skip': o.skip}
    if o.skip:
        return res
    if not targets:
        raise Fail('nothing inside "in: %s" changed since %s, so the proof cannot be shown to depend on the change. '
                   'Paths are relative to the repository root. If this change removes or restructures code and '
                   'nothing can fail first, add the line "counterfactual: skip - <reason>" to %s.'
                   % (o.get('in'), (base or 'the first commit')[:10], o.rel))
    say('  proof passed in %ss; two more runs (without the change, then with it again), about %ss' % (s1, round(2 * s1, 1)))
    crc, ctail, s2 = without_change(root, cfg, o, base, targets)
    if crc == 0:
        raise Fail('the proof still passes with the change taken out, so it does not depend on the change.\n'
                   '  taken out: %s\n  usual causes: the proof asserts nothing the change does; the result comes '
                   'from an installed dependency or a cache rather than these files; the test lives in a file that '
                   'was taken out (keep it under a test path); this change removes or restructures code (then add '
                   '"counterfactual: skip - <reason>").' % ', '.join(targets[:8]))
    if crc is None or crc in (126, 127) or crc >= 128 or crc < 0:
        raise CouldNotRun('with the change taken out the proof did not fail, it could not run (%s). A proof must run '
                          'to completion and exit non-zero.\n%s' % ('timeout' if crc is None else 'exit %d' % crc, _indent(ctail)))
    rc3, tail3, s3 = run_proof(root, o.get('proof'), cfg['proof_timeout'])
    if rc3 != 0:
        raise Fail('the proof passed, failed without the change, and then did not pass again with the change put back '
                   '(%s). A proof must give the same answer each time it runs; this one may leave state behind.\n%s'
                   % ('timeout' if rc3 is None else 'exit %d' % rc3, _indent(tail3)))
    res.update(seconds=[s1, s2, s3], red_says=(ctail.strip().splitlines() or ['(no output)'])[-1][:160])
    return res


def _indent(text):
    return '\n'.join('    ' + l for l in (text or '').splitlines()[-12:])


def _describe(o, res):
    if res.get('skip'):
        return 'SKIPPED the take-out check (%s): the proof passes; %d line(s) in %d file(s) not verified' % (
            res['skip'].split('-', 1)[-1].strip() or 'no reason', res['lines'], res['files'])
    return 'took out %d file(s), %d line(s); without them the proof said: %s; %s s' % (
        res['files'], res['lines'], res['red_says'], '+'.join(str(s) for s in res['seconds']))


# ---------------------------------------------------------------- the gate

def survey(root, base_arg=None, recompute=False):
    """Everything the gate and the hooks need to know about the change, computed once."""
    cfg0 = load_config(root)
    base = find_base(root, cfg0, base_arg)
    cfg = load_config(root, base) if recompute and base else cfg0
    changed = changed_files(root, base)
    control, exempt, tests, product = classify(changed, cfg)
    inplay = [o for o in all_outcomes(root) if o.rel in changed]
    active = [o for o in inplay if not o.parked]
    return dict(cfg=cfg, base=base, changed=changed, control=control, exempt=exempt, tests=tests, product=product,
                inplay=inplay, active=active)


def gate(root, base_arg=None, recompute=False, say=lambda s: None):
    """(exit code, report lines). Raises CouldNotRun."""
    s = survey(root, base_arg, recompute)
    cfg, base, changed, product, active = s['cfg'], s['base'], s['changed'], s['product'], s['active']
    lines, problems, skips, verified = [], [], [], []
    for p in product:  # within one change a file belongs to one outcome
        owners = [o.slug for o in active if matches(p, o.ins)]
        if len(owners) > 1:
            problems.append('%s is inside the boundary of %s: within one change a file belongs to one outcome. Make '
                            'them one outcome, or ship them as successive changes.' % (p, ' and '.join(owners)))
    for o in active:
        try:
            if recompute:
                say('%s: %s' % (o.slug, o.get('proof')))
                res = verify(root, cfg, o, base, changed, say)
            else:
                ev = last_ok(root, o.slug)
                if not ev or ev.get('hash') != content_hash(root, cfg, o, changed):
                    raise Fail('run: %s done %s' % (ODD, o.slug))
                res = ev
            verified.append(o)
            if res.get('skip'):
                skips.append('%s - %s, %d line(s)' % (o.slug, res['skip'].split('-', 1)[-1].strip(), res['lines']))
            lines += ['  ok      %s: %s' % (o.slug, o.get('outcome')[:100]), '          ' + _describe(o, res)]
        except Fail as e:
            problems.append('%s: %s' % (o.slug, e))
    for o in s['inplay']:
        if o.parked:
            lines.append('  parked  %s: %s (a parked outcome covers no files)' % (o.slug, o.parked))
    stray = [p for p in product if not any(matches(p, o.ins) for o in active)]
    n = sum(changed_lines(root, base, p) for p in stray)
    if stray and n > cfg['trivial_lines']:
        un = set(zlist(root, 'ls-files', '--others', '--exclude-standard', '-z'))
        hint = [p for p in stray if p in un]
        problems.append(
            '%s changed line(s) in %d file(s) are outside every outcome (up to %d need none): %s%s\n'
            '    state the outcome in .odd/outcomes/<slug>.md, then run %s done <slug>:\n'
            '      ---\n      outcome: <one sentence: who observes what>\n      proof: <a command that exits 0 only when that is true>\n'
            '      in: %s\n      ---%s'
            % ('a binary file or submodule pointer and other' if n >= BIG else n, len(stray), cfg['trivial_lines'],
               ', '.join(stray[:8]), ', ...' if len(stray) > 8 else '', ODD,
               ', '.join(sorted({p.split('/')[0] + '/**' if '/' in p else p for p in stray})[:6]),
               ('\n    untracked: %s. If that is build output, add it to .gitignore instead.' % ', '.join(hint[:4])) if hint else ''))
    elif stray:
        lines.append('  small-change lane: %d line(s) outside any outcome (%s); the budget is %d'
                     % (n, ', '.join(stray[:5]), cfg['trivial_lines']))
    if s['exempt']:
        lines.append('  exempt paths: %d file(s), %s line(s)' % (
            len(s['exempt']), sum(min(changed_lines(root, base, p), 10 ** 5) for p in s['exempt'])))
    if s['tests']:
        old = set(zlist(root, 'ls-tree', '-r', '--name-only', '-z', base, '--', *s['tests'])) if base else set()
        touched = [p for p in s['tests'] if p in old]
        lines.append('  test files: %d changed%s' % (len(s['tests']), ('; existed before and were modified or deleted: '
                                                                    + ', '.join(touched[:8])) if touched else ''))
    if s['control']:
        lines.append('  CONTROL FILES CHANGED (a person must review; in CI the tool and settings are read from the base): '
                     + ', '.join(s['control']))
    head = '%s gate%s: base %s, %d file(s) changed, %d outcome(s) in this change' % (
        ODD, ' --recompute' if recompute else '', (base or 'none')[:10], len(changed), len(s['inplay']))
    tail = ' (%d skipped the take-out check: %s)' % (len(skips), '; '.join(skips)) if skips else ''
    if problems:
        return 1, [head] + lines + ['FAIL' + tail] + ['  ' + p for p in problems]
    return 0, [head] + lines + ['PASS' + tail]


# ---------------------------------------------------------------- commands

def cmd_new(a, root):
    if not SLUG.match(a.slug):
        raise Fail('slug: lowercase letters, digits, dot, dash, underscore')
    o = Outcome(root, a.slug)
    if os.path.exists(o.path):
        raise Fail('%s exists' % o.rel)
    sentence = ' '.join(a.outcome.split())
    if len(sentence.split()) < 4 or re.search(r'<[^>]+>', sentence):
        raise Fail('the outcome is one full sentence: who observes what result')
    if not a.proof.strip() or not split_globs(a.in_):
        raise Fail('--proof and --in must not be empty')
    o.f.update([('outcome', sentence), ('proof', a.proof.strip()), ('in', ', '.join(split_globs(a.in_)))])
    o.save()
    print('%s created (paths and the proof are relative to the repository root).\n'
          'next: write the proof under a test path, make the change inside "%s", then: %s done %s'
          % (o.rel, o.get('in'), ODD, a.slug))


def cmd_done(a, root):
    o, cfg = Outcome.load(root, a.slug), load_config(root)
    base = find_base(root, cfg)
    changed = changed_files(root, base)
    try:
        res = verify(root, cfg, o, base, changed, print)
    except Fail as e:
        record(root, a.slug, ok=False, why=str(e)[:300])
        raise
    if o.parked:
        del o.f['parked']
        o.save()
        changed = changed_files(root, base)
    record(root, a.slug, ok=True, hash=content_hash(root, cfg, o, changed), **res)
    print('%s: verified. %s' % (a.slug, _describe(o, res)))
    code, lines = gate(root)
    print('\n'.join(['', 'the change as a whole:'] + lines))


def cmd_gate(a, root):
    code, lines = gate(root, a.base, a.recompute, print)
    print('\n'.join(lines))
    return code


def cmd_park(a, root):
    if len(a.reason.strip()) < 10:
        raise Fail('give a reason someone else can act on')
    o = Outcome.load(root, a.slug)
    o.f['parked'] = ' '.join(a.reason.split())
    o.save()
    print('%s: parked. This is a valid result; say so plainly in your report. A parked outcome covers no files, so '
          'its changes must be removed or the gate fails. To resume, delete the "parked:" line.' % a.slug)


def cmd_stats(a, root):
    outs = all_outcomes(root)
    print('self-reported, from this machine only; not a measurement')
    print('%-28s %-8s %9s %8s' % ('outcome', 'state', 'attempts', 'passed'))
    for o in outs:
        ev = evidence(root, o.slug)
        state = 'parked' if o.parked else ('skip' if o.skip else '')
        print('%-28s %-8s %9d %8d' % (o.slug, state, len(ev), sum(1 for e in ev if e.get('ok'))))
    print('%d outcome(s): %d parked, %d skip the take-out check, %d record an escaped defect' % (
        len(outs), sum(1 for o in outs if o.parked), sum(1 for o in outs if o.skip), sum(1 for o in outs if o.get('escaped'))))


METHOD = '''## Outcome-driven development (odd)

Work here is done when a proof says so, not when it looks finished. `odd` below means `python3 .odd/odd.py`.

For any change of more than a few lines:

1. State the outcome before writing code: one sentence saying who observes what, a command that exits 0 only when
   that is true, and the files the change may touch. If the request is unclear, ask (at most five questions)
   instead of guessing.
   `odd new <slug> "<outcome>" --proof "<command>" --in "<globs, relative to the repository root>"`
2. Write the proof as a test in a file of its own under a test path (`tests/`). Make it the narrowest command that
   shows the outcome, not the whole suite.
3. Make the change, staying inside the files the outcome names. If more are needed, add them to `in:` in
   `.odd/outcomes/<slug>.md`. Work that is not part of this outcome is a later outcome.
4. Finish with `odd done <slug>`, then `odd gate`. `done` passes only when the proof passes, fails with your change
   taken out, and passes again. Report the work as done only when both exit 0, and report what they printed.
5. If it cannot be done as specified, or you are blocked, say so: `odd park <slug> "<why>"`. That is an acceptable
   result. Weakening or deleting a test to get a pass is not.

Small edits (up to {trivial} changed lines) need no outcome. If a command can answer a question, run the command.
Decisions only the owner can make (credentials, billing, deploys, releases, deleting data, relaxing a check) go to
the owner; decide the rest yourself and note why in the outcome file. Do not edit `.odd/odd.py` or
`.odd/config.json`.
'''
BEGIN, END = '<!-- odd:begin -->', '<!-- odd:end -->'
CI_HELP = '''
To make the gate count, add this as the last step of your existing test job (full history, not a depth-1 checkout):

  git show "origin/$TARGET:.odd/odd.py" > "$TMP/odd.py" 2>/dev/null || cp .odd/odd.py "$TMP/odd.py"
  python3 "$TMP/odd.py" gate --recompute --base "origin/$TARGET"

CI is the authority only when (1) that step is a required check on the target branch, (2) .odd/odd.py,
.odd/config.json and the CI configuration cannot change without a person's review, and (3) the agent cannot merge
or push to the target branch. Otherwise the gate is advice. Without CI, run `%s gate --recompute` before merging.'''
HOOK = 'python3 "$(git rev-parse --show-toplevel 2>/dev/null)/.odd/odd.py" hook %s 2>/dev/null || true'


def cmd_init(a, root):
    os.makedirs(odd_dir(root, 'outcomes'), exist_ok=True)
    cp = odd_dir(root, 'config.json')
    if not os.path.isfile(cp):
        with open(cp, 'w') as f:
            json.dump(DEFAULTS, f, indent=1)
            f.write('\n')
    me, mine = os.path.abspath(__file__), os.path.abspath(odd_dir(root, 'odd.py'))
    if me != mine:
        shutil.copyfile(me, mine)
    cfg = load_config(root)
    did = ['.odd/odd.py and .odd/config.json (control files: changes to them need a person\'s review)']
    agents = os.path.join(root, 'AGENTS.md')
    old = open(agents, encoding='utf-8').read() if os.path.isfile(agents) else ''
    block = BEGIN + '\n' + METHOD.replace('{trivial}', str(cfg['trivial_lines'])).rstrip('\n') + '\n' + END
    if BEGIN in old and END in old:
        new = old[:old.index(BEGIN)] + block + old[old.index(END) + len(END):]
    else:
        new = block + '\n' + ('\n' + old if old.strip() else '')
    with open(agents, 'w', encoding='utf-8') as f:
        f.write(new)
    did.append('AGENTS.md: the method (read by Codex, Cursor, Copilot in VS Code, Claude Code, Junie, Windsurf)')
    for rel in ('CLAUDE.md', os.path.join('.claude', 'CLAUDE.md')):
        p = os.path.join(root, rel)
        if os.path.isfile(p) and os.path.realpath(p) != os.path.realpath(agents):
            text = open(p, encoding='utf-8').read()
            if '@AGENTS.md' not in text:
                with open(p, 'w', encoding='utf-8') as f:
                    f.write(text.rstrip('\n') + '\n\n@AGENTS.md\n')
            did.append('%s imports AGENTS.md' % rel)
    if a.claude_hooks:
        sp = os.path.join(root, '.claude', 'settings.local.json')
        s = json.load(open(sp)) if os.path.isfile(sp) else {}
        hooks = s.setdefault('hooks', {})
        for event, arg in (('Stop', 'stop'), ('SessionStart', 'session-start')):
            keep = [e for e in hooks.get(event, []) if '.odd/odd.py' not in json.dumps(e)]
            hooks[event] = keep + [{'hooks': [{'type': 'command', 'command': HOOK % arg, 'timeout': 60}]}]
        os.makedirs(os.path.dirname(sp), exist_ok=True)
        with open(sp, 'w') as f:
            json.dump(s, f, indent=2)
            f.write('\n')
        ex = os.path.join(root, git(root, 'rev-parse', '--git-path', 'info/exclude').strip())
        have = open(ex).read() if os.path.isfile(ex) else ''
        if '.claude/settings.local.json' not in have:
            os.makedirs(os.path.dirname(ex), exist_ok=True)
            with open(ex, 'a') as f:
                f.write(('' if have.endswith('\n') or not have else '\n') + '.claude/settings.local.json\n')
        did.append('.claude/settings.local.json: two Claude Code hooks for this machine only (not committed)')
    log = state_dir(root, 'hook-errors.log')
    if os.path.isfile(log) and os.path.getsize(log):
        did.append('WARNING: the editor hooks failed %d time(s): see %s' % (sum(1 for _ in open(log)), log))
    print('odd %s is set up:\n  ' % VERSION + '\n  '.join(did))
    print(CI_HELP % ODD)
    print('\nstart: %s new <slug> "<outcome>" --proof "<command>" --in "<globs>"' % ODD)


# ---------------------------------------------------------------- opt-in Claude Code hooks (internal)

def _fingerprint(root):
    h = hashlib.sha256(git(root, 'status', '--porcelain', '-z').encode())
    h.update(sh(['git', 'diff', 'HEAD'], root).stdout.encode())
    return h.hexdigest()


def cmd_hook(a, root):
    try:
        ev = json.load(sys.stdin)
    except ValueError:
        ev = {}
    sid = re.sub(r'[^A-Za-z0-9_-]', '', str(ev.get('session_id') or ev.get('conversation_id') or 'x'))[:64]
    os.makedirs(state_dir(root), exist_ok=True)
    fp_path = state_dir(root, 'turn-%s.fp' % sid)
    msg = recover(root, load_config(root)['proof_timeout'])
    if a.event == 'session-start':
        if ev.get('source') != 'compact':
            with open(fp_path, 'w') as f:
                f.write(_fingerprint(root))
        try:
            inplay = survey(root)['inplay']
        except CouldNotRun:
            inplay = []  # no target branch to measure from: nothing to say
        if msg or inplay:
            print('odd: ' + (msg + '. ' if msg else '') + '; '.join(
                '%s %s' % (o.slug, 'parked' if o.parked else 'in this change') for o in inplay))
        return
    if ev.get('stop_hook_active') or (ev.get('loop_count') or 0) >= 1:
        return
    if msg:
        print(json.dumps({'decision': 'block', 'reason': 'odd: ' + msg + '. Check the working tree before ending the turn.'}))
        return
    fp = _fingerprint(root)
    before = open(fp_path).read() if os.path.isfile(fp_path) else None
    with open(fp_path, 'w') as f:
        f.write(fp)
    if before == fp:
        return  # this turn changed no files: a question or a discussion is never blocked
    try:
        s = survey(root)
    except CouldNotRun:
        return
    cfg, base, changed = s['cfg'], s['base'], s['changed']
    stale = [o.slug for o in s['active'] if last_ok(root, o.slug)
             and last_ok(root, o.slug).get('hash') != content_hash(root, cfg, o, changed)]
    stray = [p for p in s['product'] if not any(matches(p, o.ins) for o in s['active'])]
    n = sum(changed_lines(root, base, p) for p in stray)
    run = 'python3 .odd/odd.py'
    if stale:
        print(json.dumps({'decision': 'block', 'reason': 'odd: %s was verified and its files have changed since. Run `%s '
                          'done %s` again, or park it with a reason.' % (', '.join(stale), run, stale[0])}))
    elif not s['active'] and n > cfg['trivial_lines']:
        print(json.dumps({'decision': 'block', 'reason': 'odd: this turn left %d changed line(s) with no outcome. State '
                          'the outcome (`%s new <slug> "<outcome>" --proof "<command>" --in "<globs>"`) and verify it '
                          '(`%s done <slug>`), or say why it cannot be done (`%s park <slug> "<why>"`).' % (n, run, run, run)}))
    else:
        open_ = [o.slug for o in s['active'] if not last_ok(root, o.slug)]
        if open_:
            print(json.dumps({'systemMessage': 'odd: not verified yet: ' + ', '.join(open_)}))


def main(argv=None):
    global ODD
    p = argparse.ArgumentParser(prog='odd', description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--version', action='version', version='odd ' + VERSION)
    sub = p.add_subparsers(dest='cmd', required=True)
    sub.add_parser('init').add_argument('--claude-hooks', action='store_true')
    s = sub.add_parser('new')
    s.add_argument('slug')
    s.add_argument('outcome')
    s.add_argument('--proof', required=True)
    s.add_argument('--in', dest='in_', required=True)
    sub.add_parser('done').add_argument('slug')
    s = sub.add_parser('gate')
    s.add_argument('--base')
    s.add_argument('--recompute', action='store_true')
    s = sub.add_parser('park')
    s.add_argument('slug')
    s.add_argument('reason')
    sub.add_parser('stats')
    sub.add_parser('hook').add_argument('event', choices=['stop', 'session-start'])
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
        root = find_root()
        msg = recover(root, load_config(root)['proof_timeout'])
        if msg:
            raise CouldNotRun(msg + '. Look at your working tree, then run the command again.')
        return globals()['cmd_' + a.cmd](a, root) or 0
    except Fail as e:
        print('odd: ' + str(e), file=sys.stderr)
        return 1
    except CouldNotRun as e:
        print('odd: could not run: ' + str(e), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
