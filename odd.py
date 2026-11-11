#!/usr/bin/env python3
"""odd: outcome-driven development. "Done" is recomputed from the code, not claimed.

An outcome is one sentence, a proof command and a boundary, kept in .odd/outcomes/<slug>.md. It is done only when the
proof passes on the tree as it is and fails on the same tree with the change taken out. `odd gate` checks that every
change since the base is covered by such an outcome; with --recompute (CI) it trusts nothing recorded.

  odd init [--claude] [--cursor] [--copilot] [--ci] [--hook pre-push|pre-commit]
  odd new <slug> "<outcome>" --proof "<command>" --in "<globs>" [--tests "<globs>"] [--after <slug>] [--real]
  odd red <slug>          the proof fails now, before the change (optional early check)
  odd done <slug>         verify and record; exit 0 only when verified
  odd gate [--base REF] [--recompute]     exit 0 pass, 1 fail, 2 could not run
  odd park|abort <slug> "<reason>"        honest exits: blocked / cannot be done as specified
  odd widen <slug> <glob> "<reason>"      add files to the boundary, on the record
  odd status | odd stats | odd doctor | odd escape <slug> "<what escaped>"

Python 3.8+, standard library only. One file, so a project can vendor it as .odd/odd.py.
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

VERSION = '0.1.0'
DEFAULTS = {
    'trivial_lines': 25,       # changed lines allowed outside any outcome (the small-change lane)
    'exempt': ['.odd/**', '**/*.md', 'LICENSE*', '.gitignore', '.gitattributes'],
    'test_globs': ['tests/**', 'test/**', '**/__tests__/**', '**/test_*.py', '**/*_test.*', '**/*.test.*',
                   '**/*.spec.*', 'spec/**'],  # a proof's own files: allowed for every outcome, never reverted
    'proof_timeout': 900,      # seconds per proof run
    'max_skips': None,         # outcomes allowed to skip the counterfactual check (None: listed, not limited)
    'default_branch': None,    # detected when None
    'guard': 'boundary',       # editor hook: refuse writes outside the open outcome's boundary ('off' disables)
    'stop_gate': True,         # editor hook: at turn end, block when this turn's changes fail the gate
}
CONTROL = ('.odd/config.json', '.odd/odd.py')   # read from the base revision when recomputing
SLUG = re.compile(r'^[a-z0-9][a-z0-9._-]{0,63}$')
BINARY_LINES = 1000  # a binary or unreadable change is never "trivial"


class Fail(Exception):
    """The outcome does not hold (exit 1)."""


class CouldNotRun(Exception):
    """The check could not be performed (exit 2). Never reported as a pass."""


# ---------------------------------------------------------------- git and files

def sh(args, cwd, input=None):
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True, input=input)


def git(root, *args, ok=(0,)):
    r = sh(['git'] + list(args), root)
    if r.returncode not in ok:
        raise CouldNotRun('git %s: %s' % (' '.join(args[:3]), (r.stderr or r.stdout).strip()[:300]))
    return r.stdout


def find_root():
    r = sh(['git', 'rev-parse', '--show-toplevel'], os.getcwd())
    if r.returncode != 0:
        raise CouldNotRun('not inside a git repository (odd uses git to see what changed)')
    return r.stdout.strip()


def odd_dir(root, *p):
    return os.path.join(root, '.odd', *p)


def state_dir(root, *p):
    """Working state (journals, local evidence, editor-hook marks) lives under the git directory: it cannot be
    committed, and a proof looking at the working tree sees nothing of it. One per worktree."""
    d = git(root, 'rev-parse', '--git-dir').strip()
    return os.path.join(d if os.path.isabs(d) else os.path.join(root, d), 'odd', *p)


def zlist(root, *args):
    return [x for x in git(root, *args).split('\0') if x]


def rev(root, ref):
    r = sh(['git', 'rev-parse', '--verify', '--quiet', ref + '^{commit}'], root)
    return r.stdout.strip() if r.returncode == 0 else None


def is_ancestor(root, a, b='HEAD'):
    return sh(['git', 'merge-base', '--is-ancestor', a, b], root).returncode == 0


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
    path = path.replace(os.sep, '/')
    return any(glob_re(g).match(path) for g in globs if g.strip())


def split_globs(s):
    return [g.strip() for g in (s or '').split(',') if g.strip()]


def load_config(root, base=None):
    """The project's settings. When recomputing, they come from the base revision, so a change cannot loosen its own
    gate; a project adopting odd in this very change gets the defaults."""
    cfg = dict(DEFAULTS)
    try:
        if base:
            r = sh(['git', 'show', '%s:.odd/config.json' % base], root)
            text = r.stdout if r.returncode == 0 else '{}'
        else:
            with open(odd_dir(root, 'config.json')) as f:
                text = f.read()
        cfg.update(json.loads(text))
    except (OSError, ValueError):
        pass
    return cfg


def default_branch(root, cfg):
    if cfg.get('default_branch'):
        return cfg['default_branch']
    r = sh(['git', 'symbolic-ref', '--short', 'refs/remotes/origin/HEAD'], root)
    if r.returncode == 0 and r.stdout.strip():
        return r.stdout.strip().split('/', 1)[-1]
    for name in ('main', 'master'):
        if rev(root, 'origin/' + name) or rev(root, name):
            return name
    return None


def gate_base(root, cfg, arg=None):
    """The revision changes are measured from: --base, $ODD_BASE, else where this branch left the default branch."""
    ref = arg or os.environ.get('ODD_BASE')
    if ref:
        sha = rev(root, ref)
        if not sha:
            raise CouldNotRun('base revision %r not found (in CI, fetch full history: fetch-depth: 0)' % ref)
        mb = sh(['git', 'merge-base', 'HEAD', sha], root)
        return mb.stdout.strip() if mb.returncode == 0 and mb.stdout.strip() else sha
    head = rev(root, 'HEAD')
    if not head:
        return None  # no commits yet: everything is new
    d = default_branch(root, cfg)
    for cand in (('origin/' + d) if d else None, d):
        if cand and rev(root, cand):
            mb = sh(['git', 'merge-base', 'HEAD', cand], root)
            if mb.returncode == 0 and mb.stdout.strip():
                return mb.stdout.strip()
    return head


EMPTY_TREE = '4b825dc642cb6eb9a060e54bf8d69288fbee4904'


def changed_files(root, base):
    """Every path that differs from base in the working tree (committed, staged or not) plus untracked files.
    Computed from git, so files written through a shell are seen like any other."""
    names = set(zlist(root, 'diff', '--name-only', '--no-renames', '-z', base or EMPTY_TREE))
    names |= set(zlist(root, 'ls-files', '--others', '--exclude-standard', '-z'))
    return sorted(names)


def changed_lines(root, base, path):
    r = sh(['git', 'diff', '--numstat', '--no-renames', base or EMPTY_TREE, '--', path], root)
    line = r.stdout.strip().splitlines()[0] if r.stdout.strip() else ''
    if line:
        a, d = line.split('\t')[:2]
        n = BINARY_LINES if '-' in (a, d) else int(a) + int(d)
        return n or BINARY_LINES  # a mode-only, link or submodule change has no lines and is not "small"
    try:  # untracked
        with open(os.path.join(root, path), 'rb') as f:
            data = f.read()
        return BINARY_LINES if b'\0' in data[:8000] else data.count(b'\n') + (1 if data and not data.endswith(b'\n') else 0)
    except OSError:
        return BINARY_LINES


# ---------------------------------------------------------------- outcome files

class Outcome:
    """`.odd/outcomes/<slug>.md`: front matter of `key: value` lines (an indented line continues the value above),
    then free notes."""

    def __init__(self, root, slug):
        self.root, self.slug = root, slug
        self.path = odd_dir(root, 'outcomes', slug + '.md')
        self.f, self.notes = collections.OrderedDict(), ''

    @classmethod
    def load(cls, root, slug):
        o = cls(root, slug)
        if not os.path.isfile(o.path):
            raise Fail('no outcome %r (odd status lists them; odd new creates one)' % slug)
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
        o.f.setdefault('status', 'open')
        return o

    @property
    def rel(self):
        return '.odd/outcomes/%s.md' % self.slug

    def get(self, k, d=''):
        return self.f.get(k, d)

    @property
    def status(self):
        return self.get('status', 'open')

    @property
    def skip(self):
        v = self.get('counterfactual')
        return v if v.lower().startswith('skip') else ''

    def save(self):
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.path, 'w', encoding='utf-8') as f:
            f.write('---\n' + ''.join('%s: %s\n' % kv for kv in self.f.items()) + '---\n' + self.notes)

    def note(self, text):
        self.notes = self.notes.rstrip('\n') + ('\n' if self.notes.strip() else '') + text + '\n'


def all_outcomes(root):
    d = odd_dir(root, 'outcomes')
    out = []
    for name in sorted(os.listdir(d)) if os.path.isdir(d) else []:
        if name.endswith('.md'):
            out.append(Outcome.load(root, name[:-3]))
    return out


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds')


def record(root, slug, kind, **data):
    """Evidence is a log for people and for `odd stats`. CI never trusts it."""
    os.makedirs(odd_dir(root, 'evidence'), exist_ok=True)
    with open(odd_dir(root, 'evidence', slug + '.jsonl'), 'a') as f:
        f.write(json.dumps(dict(ts=now(), kind=kind, **data)) + '\n')


def evidence(root, slug):
    p, out = odd_dir(root, 'evidence', slug + '.jsonl'), []
    if os.path.isfile(p):
        with open(p) as f:
            for line in f:
                try:
                    out.append(json.loads(line))
                except ValueError:
                    pass
    return out


def proof_globs(o, cfg):
    return split_globs(o.get('tests')) + list(cfg['test_globs'])


def covers(o, cfg, path):
    return matches(path, split_globs(o.get('in'))) or matches(path, proof_globs(o, cfg))


def content_hash(root, cfg, o, changed):
    """Identity of what was verified: the proof, the boundary and the bytes of every file the outcome covers.
    A commit, or an edit to a file outside it, leaves the hash unchanged."""
    h = hashlib.sha256()
    for k in ('proof', 'in', 'tests', 'counterfactual'):
        h.update((k + '=' + o.get(k) + '\n').encode())
    listed = set(zlist(root, 'ls-files', '-c', '-o', '--exclude-standard', '-z'))
    own = split_globs(o.get('in')) + split_globs(o.get('tests'))
    for path in sorted(p for p in listed if matches(p, own) or (p in changed and matches(p, cfg['test_globs']))):
        try:
            with open(os.path.join(root, path), 'rb') as f:
                h.update(path.encode() + b'\0' + hashlib.sha256(f.read()).digest())
        except OSError:
            h.update(path.encode() + b'\0gone')
    return h.hexdigest()[:20]


# ---------------------------------------------------------------- proofs and the counterfactual

def run_proof(root, cmd, timeout):
    """(exit code or None on timeout, last lines of output). No environment variable marks the run, so a proof has
    nothing from the tool to tell the counterfactual run apart."""
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
        return p.returncode, '\n'.join(out.strip().splitlines()[-20:])[-2000:]
    except subprocess.TimeoutExpired:
        kill()
        p.communicate()
        return None, 'timed out after %ss' % timeout
    except BaseException:  # interrupted: do not leave the proof running while the tree is put back
        kill()
        raise


def pid_alive(pid):
    if os.name != 'posix':
        import ctypes
        h = ctypes.windll.kernel32.OpenProcess(0x1000, False, int(pid))
        if h:
            ctypes.windll.kernel32.CloseHandle(h)
        return bool(h)
    try:
        os.kill(int(pid), 0)
        return True
    except (OSError, ValueError):
        return False


def _state(path):
    """What is at a path right now: None (nothing), ('link', target) or ('file', sha256)."""
    if os.path.islink(path):
        return ['link', os.readlink(path)]
    if os.path.isfile(path):
        with open(path, 'rb') as f:
            return ['file', hashlib.sha256(f.read()).hexdigest()]
    return None


def _bump(path, after):
    """Give the path an mtime two seconds past anything this run saw, so caches keyed on mtime (Python bytecode,
    make) notice both the revert and the restore even when size and second are unchanged."""
    t = max(time.time(), after or 0) + 2
    try:
        os.utime(path, (t, t), follow_symlinks=False)
    except (OSError, NotImplementedError):
        pass
    return t


def restore(jdir):
    """Put back what a counterfactual run took out. A path is restored only if it still holds exactly what the run
    left there; if someone edited it meanwhile, their version stays and the saved one is kept beside the journal.
    Returns (restored, displaced paths)."""
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
            if e['saved'] is not None:
                keep = os.path.join(os.path.dirname(jdir), 'displaced', os.path.basename(jdir), e['path'])
                os.makedirs(os.path.dirname(keep), exist_ok=True)
                shutil.copyfile(os.path.join(jdir, e['saved']), keep) if e['kind'] == 'file' else open(keep, 'w').write(e['link'])
                displaced.append('%s (your earlier version: %s)' % (e['path'], keep))
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
    """A check that was killed mid-run leaves a journal; restore from it unless that check is still running.
    Returns a message when something was restored, so the caller can stop and let the user look."""
    sd = state_dir(root)
    msgs = []
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
        n, displaced = restore(jdir)
        msgs.append('an earlier check was interrupted while the change was taken out; %d file(s) were put back%s'
                    % (n, ('. Edited meanwhile and left as they are: ' + '; '.join(displaced)) if displaced else ''))
    return ' '.join(msgs)


def counterfactual(root, cfg, o, base, changed):
    """Run the proof with this outcome's product change taken out, in place, then put the change back.
    Returns (exit code or None on timeout, output tail, the paths taken out)."""
    ins, tests = split_globs(o.get('in')), proof_globs(o, cfg)
    targets = [p for p in changed if matches(p, ins) and not matches(p, tests) and not p.startswith('.odd/')]
    if not targets:
        raise Fail('nothing inside "in: %s" changed since %s (other than the proof\'s own files), so the proof cannot be '
                   'shown to depend on the change. Fix "in", or add "counterfactual: skip - <reason>" when nothing can '
                   'fail first (a pure refactor, a dependency bump).' % (o.get('in'), (base or 'the start')[:10]))
    ran = set()  # the command word of each step of the proof: `./check.sh && pytest x` runs ./check.sh and pytest
    for step in re.split(r'&&|\|\||[;|\n]', o.get('proof')):
        words = [w for w in step.split() if not re.match(r'^[A-Za-z_][A-Za-z0-9_]*=', w)]
        if words:
            ran.add(words[0][2:] if words[0].startswith('./') else words[0])
    named = [p for p in targets if p in ran]
    if named:
        raise Fail('the proof runs %s, which is part of the change and would be taken out by the check, so any '
                   'failure would count. Keep what the proof runs outside "in" (a test path).' % ', '.join(named))
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
            e.update(kind='link', link=os.readlink(full), saved='link')
        elif os.path.isfile(full):
            shutil.copyfile(full, os.path.join(jdir, str(n)))
            st = os.stat(full)
            e.update(kind='file', saved=str(n), mode=st.st_mode & 0o7777, mtime=st.st_mtime)
        elif os.path.isdir(full):
            shutil.rmtree(jdir, ignore_errors=True)
            raise CouldNotRun('%s is a directory entry (a submodule?); verify inside it, or use "counterfactual: skip - '
                              '<reason>"' % p)
        entries.append(e)
    journal = {'root': root, 'pid': os.getpid(), 'started': time.time(), 'files': entries}

    def save():
        with open(os.path.join(jdir, 'journal.json'), 'w') as f:
            json.dump(journal, f)
            f.flush()
            os.fsync(f.fileno())

    save()  # everything needed to undo is on disk before the first file is touched
    before = git(root, 'status', '--porcelain', '-z', '--untracked-files=no')
    displaced = []
    try:
        try:
            for e in entries:  # removals first, then git writes the earlier versions (content, mode, links, filters)
                if e['path'] not in at_base and os.path.lexists(os.path.join(root, e['path'])):
                    os.remove(os.path.join(root, e['path']))
            back = [e['path'] for e in entries if e['path'] in at_base]
            if back:
                r = sh(['git', 'restore', '--source=' + base, '--worktree', '--'] + back, root)
                if r.returncode != 0:
                    raise CouldNotRun('git could not write the earlier versions (git 2.23 or newer is needed): %s'
                                      % r.stderr.strip()[:200])
            for e in entries:
                full = os.path.join(root, e['path'])
                e['left'] = _state(full)
                if e['left']:
                    e['touched'] = _bump(full, e.get('mtime'))
            save()
        except OSError as err:  # never run a proof on a half-reverted tree
            raise CouldNotRun('could not take the change out (%s); nothing was verified' % err)
        rc, tail = run_proof(root, o.get('proof'), cfg['proof_timeout'])
    finally:
        _, displaced = restore(jdir)
    if displaced:
        raise CouldNotRun('files changed while the check was running and were left as they are: ' + '; '.join(displaced))
    if git(root, 'status', '--porcelain', '-z', '--untracked-files=no') != before:
        raise CouldNotRun('the working tree is not as it was before the check (the proof may write tracked files); '
                          'compare with: git status')
    return rc, tail, targets


def verify(root, cfg, o, base, changed):
    """The proof passes on the tree as it is, and fails on the same tree with the change taken out.
    Returns a result dict; raises Fail (the outcome is not shown) or CouldNotRun (nothing was established)."""
    t0 = time.time()
    rc, tail = run_proof(root, o.get('proof'), cfg['proof_timeout'])
    if rc is None:
        raise CouldNotRun('the proof timed out (%ss): %s' % (cfg['proof_timeout'], o.get('proof')))
    if rc != 0:
        raise Fail('the proof fails (exit %d): %s\n%s' % (rc, o.get('proof'), _indent(tail)))
    res = {'green': rc, 'counterfactual': 'skip', 'out': [], 'red_says': ''}
    if not o.skip:
        crc, ctail, out = counterfactual(root, cfg, o, base, changed)
        if crc == 0:
            raise Fail('the proof still passes with the change taken out, so it does not depend on the change.\n'
                       '  taken out: %s\n  usual causes: the proof asserts nothing the change does; the result comes '
                       'from an installed dependency or a cache rather than these files; the test lives in a file '
                       'that was taken out.' % ', '.join(out[:8]))
        if crc is None or crc in (126, 127) or crc >= 128 or crc < 0:
            raise CouldNotRun('with the change taken out the proof did not fail, it could not run (%s). A proof must '
                              'run to completion and exit non-zero.\n%s'
                              % ('timeout' if crc is None else 'exit %d' % crc, _indent(ctail)))
        res.update(counterfactual=crc, out=out, red_says=(ctail.strip().splitlines() or [''])[-1][:160])
    res['seconds'] = round(time.time() - t0, 1)
    return res


def _untracked_hint(root, paths):
    """Build output the proof itself wrote (caches, compiled files) shows up as an uncovered change when the project
    does not ignore it. Say so, instead of leaving the reader to guess."""
    un = set(zlist(root, 'ls-files', '--others', '--exclude-standard', '-z'))
    hit = [p for p in paths if p in un]
    return (' Untracked: %s. If that is build output, add it to .gitignore.' % ', '.join(hit[:4])) if hit else ''


def _indent(text):
    return '\n'.join('    ' + l for l in (text or '').splitlines()[-12:])


# ---------------------------------------------------------------- the gate

def gate(root, base_arg=None, recompute=False, mode='gate'):
    """(exit code, report lines). mode 'stop' is the editor's turn-end check: parked and aborted outcomes have been
    acknowledged, so their files do not block."""
    cfg0 = load_config(root)
    base = gate_base(root, cfg0, base_arg)
    cfg = load_config(root, base) if recompute and base else cfg0
    changed = changed_files(root, base)
    lines, problems = [], []
    control = [p for p in changed if p in CONTROL or p.startswith('.github/workflows/odd')]
    if recompute and control:
        lines.append('CONTROL FILES CHANGED (settings and tool are read from the base revision; a person must review): '
                     + ', '.join(control))
    work = [p for p in changed if not matches(p, cfg['exempt'])]
    inplay = [o for o in all_outcomes(root) if o.rel in changed]
    verified, skips = [], []
    for o in inplay:
        if o.status != 'done':
            lines.append('  %-9s %s: %s%s' % (o.status.upper(), o.slug, o.get('outcome')[:90],
                                              (' [%s]' % o.get('reason')) if o.get('reason') else ''))
            continue
        try:
            if recompute:
                res = verify(root, cfg, o, base, changed)
                how = 'recomputed in %ss' % res['seconds']
            else:
                ev = [e for e in evidence(root, o.slug) if e.get('kind') == 'done' and e.get('ok')]
                if not ev or ev[-1].get('hash') != content_hash(root, cfg, o, changed):
                    raise Fail('its files changed since it was verified; run: odd done %s' % o.slug)
                how = 'verified %s' % ev[-1]['ts']
            verified.append(o)
            if o.skip:
                skips.append(o)
            lines.append('  %-9s %s: %s (%s; proof: %s)' % ('PROVEN' if o.get('real') == 'yes' else 'DONE', o.slug,
                                                           o.get('outcome')[:90], how, o.get('proof')[:60]))
        except Fail as e:
            problems.append('%s: %s' % (o.slug, e))
    acknowledged = [o for o in inplay if o.status in ('parked', 'aborted')] if mode == 'stop' else []
    uncovered = [p for p in work if not any(covers(o, cfg, p) for o in verified + acknowledged)]
    n = sum(changed_lines(root, base, p) for p in uncovered)
    if uncovered and n > cfg['trivial_lines']:
        open_ = [o.slug for o in inplay if o.status == 'open']
        problems.append('%d changed line(s) in %d file(s) are not covered by a verified outcome (up to %d lines need none): %s%s'
                        % (n, len(uncovered), cfg['trivial_lines'], ', '.join(uncovered[:8]),
                           ', ...' if len(uncovered) > 8 else '') + _untracked_hint(root, uncovered))
        problems.append('  next: ' + ('odd done %s' % open_[0] if open_ else 'odd new <slug> "<outcome>" --proof "<command>" --in "<globs>"')
                        + ', or odd widen <slug> <glob> "<reason>" if a file belongs to an existing outcome')
    elif uncovered:
        lines.append('  note: %d line(s) changed outside any outcome (%s): allowed, the small-change lane is %d lines'
                     % (n, ', '.join(uncovered[:5]), cfg['trivial_lines']))
    if skips:
        lines.append('  note: %d outcome(s) skip the counterfactual check: %s' % (
            len(skips), '; '.join('%s (%s)' % (o.slug, o.skip) for o in skips)))
        if cfg.get('max_skips') is not None and len(skips) > cfg['max_skips']:
            problems.append('%d outcome(s) skip the counterfactual check; this project allows %d' % (len(skips), cfg['max_skips']))
    head = 'odd gate%s: base %s, %d file(s) changed, %d outcome(s) in this change' % (
        ' --recompute' if recompute else '', (base or 'none')[:10], len(changed), len(inplay))
    if problems:
        return 1, [head] + lines + ['FAIL'] + ['  ' + p for p in problems]
    return 0, [head] + lines + ['PASS']


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
    o.f.update([('outcome', sentence), ('proof', a.proof.strip()), ('in', ', '.join(split_globs(a.in_))),
                ('tests', ', '.join(split_globs(a.tests))), ('real', 'yes' if a.real else 'no'),
                ('base', (rev(root, 'HEAD') or '')[:12]), ('status', 'open')])
    if a.after:
        o.f['after'] = a.after
    if a.skip_counterfactual:
        o.f['counterfactual'] = 'skip - ' + a.skip_counterfactual
    o.notes = '\n'
    o.save()
    record(root, a.slug, 'new')
    print('%s created.\nnext: write the proof and see it fail (odd red %s), make the change inside "%s", then: odd done %s'
          % (o.rel, a.slug, o.get('in'), a.slug))


def cmd_red(a, root):
    o, cfg = Outcome.load(root, a.slug), load_config(root)
    rc, tail = run_proof(root, o.get('proof'), cfg['proof_timeout'])
    record(root, a.slug, 'red', rc=rc)
    if rc is None:
        raise CouldNotRun('proof timed out')
    if rc == 0:
        raise Fail('the proof already passes before the change, so it cannot show the change worked. Sharpen it.')
    print('red (exit %d): the proof fails before the change, as it should.\n%s' % (rc, _indent(tail)))


def cmd_done(a, root):
    o, cfg = Outcome.load(root, a.slug), load_config(root)
    if o.status in ('parked', 'aborted'):
        o.f['status'] = 'open'
        o.f.pop('reason', None)
    base = gate_base(root, cfg)
    changed = changed_files(root, base)
    inplay = [o] + [x for x in all_outcomes(root) if x.slug != o.slug and x.rel in changed]

    def stay_inside():  # checked before the proof (fail fast) and after it (a proof can write files too)
        now_changed = changed_files(root, base)
        strays = [p for p in now_changed if not matches(p, cfg['exempt']) and not any(covers(x, cfg, p) for x in inplay)]
        n = sum(changed_lines(root, base, p) for p in strays)
        if n > cfg['trivial_lines']:
            raise Fail('%d changed line(s) are outside every outcome\'s boundary: %s%s. If they belong to this outcome: '
                       'odd widen %s <glob> "<reason>". If they are separate work, they need their own outcome.'
                       % (n, ', '.join(strays[:8]), ', ...' if len(strays) > 8 else '', o.slug) + _untracked_hint(root, strays))

    try:
        stay_inside()
        res = verify(root, cfg, o, base, changed)
        stay_inside()
    except Fail as e:
        record(root, a.slug, 'done', ok=False, why=str(e)[:300])
        raise
    o.f['status'] = 'done'
    o.save()
    record(root, a.slug, 'done', ok=True, hash=content_hash(root, cfg, o, changed_files(root, base)),
           lines=sum(changed_lines(root, base, p) for p in changed if covers(o, cfg, p) and not p.startswith('.odd/')), **res)
    word = 'PROVEN on the real system' if o.get('real') == 'yes' else 'DONE (the proof is a simulation; not yet proven on the real system)'
    cf = 'counterfactual skipped: ' + o.skip if o.skip else (
        'fails with the change taken out (%d file(s)); there it said: %s' % (len(res['out']), res['red_says'] or '(no output)'))
    print('%s: %s\n  proof passes; %s; %ss' % (a.slug, word, cf, res['seconds']))
    still = [x.slug for x in inplay[1:] if x.status == 'open']
    if still:
        print('  still open in this change: ' + ', '.join(still))


def cmd_gate(a, root):
    code, lines = gate(root, a.base, a.recompute)
    print('\n'.join(lines))
    return code


def _exit(a, root, status):
    if len(a.reason.strip()) < 10:
        raise Fail('give a reason someone else can act on')
    o = Outcome.load(root, a.slug)
    o.f['status'], o.f['reason'] = status, ' '.join(a.reason.split())
    o.save()
    record(root, a.slug, status, reason=o.f['reason'])
    print('%s: %s. This is a valid result; say so plainly in your report.' % (a.slug, status))


def cmd_park(a, root):
    _exit(a, root, 'parked')


def cmd_abort(a, root):
    _exit(a, root, 'aborted')


def cmd_widen(a, root):
    if len(a.reason.strip()) < 10:
        raise Fail('give the reason the boundary must grow')
    o = Outcome.load(root, a.slug)
    o.f['in'] = ', '.join(split_globs(o.get('in')) + split_globs(a.glob))
    o.note('- widened: %s (%s) %s' % (a.glob, ' '.join(a.reason.split()), now()[:10]))
    o.save()
    record(root, a.slug, 'widen', glob=a.glob, reason=a.reason)
    print('%s may now change: %s' % (a.slug, o.get('in')))


def cmd_status(a, root):
    cfg = load_config(root)
    outs = all_outcomes(root)
    changed = changed_files(root, gate_base(root, cfg)) if outs else []
    for o in outs:
        st = o.status
        if st == 'done':
            ev = [e for e in evidence(root, o.slug) if e.get('kind') == 'done' and e.get('ok')]
            if o.rel in changed and (not ev or ev[-1].get('hash') != content_hash(root, cfg, o, changed)):
                st = 'stale'
        print('%-8s %-24s %s%s' % (st, o.slug, o.get('outcome')[:80], (' [%s]' % o.get('reason')) if o.get('reason') else ''))
    if not outs:
        print('no outcomes yet: odd new <slug> "<outcome>" --proof "<command>" --in "<globs>"')


def cmd_escape(a, root):
    Outcome.load(root, a.slug)
    record(root, a.slug, 'escape', what=' '.join(a.what.split()))
    print('recorded. Next: a new outcome whose proof reproduces this defect, so it cannot return unnoticed.')


def cmd_stats(a, root):
    rows, tot = [], collections.Counter()
    for o in all_outcomes(root):
        ev = evidence(root, o.slug)
        tries = [e for e in ev if e.get('kind') == 'done']
        okd = [e for e in tries if e.get('ok')]
        born = next((e['ts'] for e in ev if e.get('kind') == 'new'), None)
        mins = None
        if born and okd:
            mins = round((datetime.datetime.fromisoformat(okd[0]['ts']) - datetime.datetime.fromisoformat(born)).total_seconds() / 60, 1)
        esc = sum(1 for e in ev if e.get('kind') == 'escape')
        tot[o.status] += 1
        tot['escapes'] += esc
        tot['skips'] += 1 if o.skip else 0
        tot['real'] += 1 if o.get('real') == 'yes' and o.status == 'done' else 0
        tot['rework'] += 1 if len(tries) > 1 and okd else 0
        rows.append((o.slug, o.status, mins, len(tries), okd[-1].get('lines') if okd else None, esc))
    print('%-24s %-8s %10s %9s %7s %8s' % ('outcome', 'status', 'minutes', 'attempts', 'lines', 'escapes'))
    for r in rows:
        print('%-24s %-8s %10s %9s %7s %8s' % tuple('-' if v is None else v for v in r))
    done = tot['done']
    print('\n%d done (%d proven on the real system), %d open, %d parked, %d aborted; %d needed more than one attempt; '
          '%d skip the counterfactual check; %d escaped defect(s)' % (done, tot['real'], tot['open'], tot['parked'],
                                                                     tot['aborted'], tot['rework'], tot['skips'], tot['escapes']))
    if a.json:
        print(json.dumps({'totals': dict(tot), 'outcomes': rows}))


METHOD = '''## Outcome-driven development (odd)

Work here is done when a proof says so, not when it looks finished. `odd` below means `python3 .odd/odd.py`.

For any change larger than a few lines:

1. State the outcome before writing code: one sentence saying who observes what, and a command that exits 0 only
   when that is true. If the request is unclear, ask (at most five questions) instead of guessing.
   `odd new <slug> "<outcome>" --proof "<command>" --in "<files this may change>"`
2. Write the proof, usually a test, and see it fail: `odd red <slug>`.
3. Make the change, staying inside the files the outcome names. If more are needed:
   `odd widen <slug> <glob> "<why>"`.
4. Finish with `odd done <slug>`. It passes only when the proof passes now and fails with your change taken out.
   Do not report the work as done until it exits 0, and report exactly what it printed.
5. If it cannot be done as specified, say so: `odd abort <slug> "<why>"`. If you are blocked:
   `odd park <slug> "<why>"`. Both are acceptable results. Weakening or deleting a test to get a pass is not.

Small edits (up to {trivial} changed lines) need no outcome. Work one outcome at a time; anything else you notice
is a note for a later outcome. If a command can answer a question, run the command. Decisions only the owner can
make (credentials, billing, deploys, releases, deleting data, relaxing a check) go to the owner; decide the rest
yourself and note why in the outcome file. Do not edit `.odd/evidence/`, `.odd/config.json` or `.odd/odd.py`.
'''
BEGIN, END = '<!-- odd:begin -->', '<!-- odd:end -->'


def _section(path, body):
    """Write `body` between the odd markers of a text file, creating the file or replacing an earlier section."""
    old = ''
    if os.path.isfile(path):
        with open(path, encoding='utf-8') as f:
            old = f.read()
    block = BEGIN + '\n' + body.rstrip('\n') + '\n' + END
    if BEGIN in old and END in old:
        new = old[:old.index(BEGIN)] + block + old[old.index(END) + len(END):]
    else:
        new = (old.rstrip('\n') + '\n\n' if old.strip() else '') + block + '\n'
    os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(new)


CI_YML = '''name: odd gate
on: pull_request
jobs:
  gate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with: {fetch-depth: 0}
      # Install what your proofs need here (language toolchain, dependencies), as in your test job.
      - name: Every change is covered by an outcome whose proof passes now and fails with the change taken out
        run: |
          # The tool and its settings come from the base branch, so a pull request cannot loosen its own gate.
          git show "origin/${{ github.base_ref }}:.odd/odd.py" > "$RUNNER_TEMP/odd.py" 2>/dev/null || cp .odd/odd.py "$RUNNER_TEMP/odd.py"
          python3 "$RUNNER_TEMP/odd.py" gate --recompute --base "origin/${{ github.base_ref }}"
'''
HOOK_MARK = '# odd gate'


def cmd_init(a, root):
    for d in ('outcomes', 'evidence', 'tmp'):
        os.makedirs(odd_dir(root, d), exist_ok=True)
    cp = odd_dir(root, 'config.json')
    if not os.path.isfile(cp):
        with open(cp, 'w') as f:
            json.dump(DEFAULTS, f, indent=1)
            f.write('\n')
    with open(odd_dir(root, '.gitignore'), 'w') as f:
        f.write('tmp/\n')
    me = os.path.abspath(__file__)
    if me != os.path.abspath(odd_dir(root, 'odd.py')):
        shutil.copyfile(me, odd_dir(root, 'odd.py'))
    cfg = load_config(root)
    body = METHOD.replace('{trivial}', str(cfg['trivial_lines']))
    did = ['.odd/ (settings, the tool itself, outcomes, evidence)']
    _section(os.path.join(root, 'AGENTS.md'), body)
    did.append('AGENTS.md (the method; read by most coding agents)')
    none = not (a.claude or a.cursor or a.copilot)
    if a.claude or (none and (os.path.isdir(os.path.join(root, '.claude')) or os.path.isfile(os.path.join(root, 'CLAUDE.md')))):
        p = os.path.join(root, 'CLAUDE.md')
        text = open(p, encoding='utf-8').read() if os.path.isfile(p) else ''
        if '@AGENTS.md' not in text:
            with open(p, 'w', encoding='utf-8') as f:
                f.write(text.rstrip('\n') + ('\n\n' if text.strip() else '') + '@AGENTS.md\n')
        sp = os.path.join(root, '.claude', 'settings.json')
        s = json.load(open(sp)) if os.path.isfile(sp) else {}
        hooks = s.setdefault('hooks', {})
        run = 'python3 "$CLAUDE_PROJECT_DIR/.odd/odd.py" hook '
        for event, matcher, arg in (('PreToolUse', 'Write|Edit|MultiEdit|NotebookEdit', 'pre-tool'), ('Stop', None, 'stop'),
                                    ('SessionStart', None, 'session-start')):
            entries = [e for e in hooks.get(event, []) if '.odd/odd.py' not in json.dumps(e)]
            entry = {'hooks': [{'type': 'command', 'command': run + arg, 'timeout': 120}]}
            if matcher:
                entry['matcher'] = matcher
            hooks[event] = entries + [entry]
        os.makedirs(os.path.dirname(sp), exist_ok=True)
        with open(sp, 'w') as f:
            json.dump(s, f, indent=2)
            f.write('\n')
        did.append('CLAUDE.md imports AGENTS.md; .claude/settings.json hooks (boundary guard, turn-end check, session status)')
    if a.cursor or (none and os.path.isdir(os.path.join(root, '.cursor'))):
        p = os.path.join(root, '.cursor', 'rules', 'odd.mdc')
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, 'w', encoding='utf-8') as f:
            f.write('---\ndescription: Outcome-driven development: work is done when its proof says so\nalwaysApply: true\n---\n\n' + body)
        did.append('.cursor/rules/odd.mdc')
    if a.copilot or (none and os.path.isfile(os.path.join(root, '.github', 'copilot-instructions.md'))):
        _section(os.path.join(root, '.github', 'copilot-instructions.md'), body)
        did.append('.github/copilot-instructions.md')
    if a.ci:
        p = os.path.join(root, '.github', 'workflows', 'odd.yml')
        os.makedirs(os.path.dirname(p), exist_ok=True)
        if not os.path.isfile(p):
            with open(p, 'w') as f:
                f.write(CI_YML)
        did.append('.github/workflows/odd.yml (add the steps that install what your proofs need)')
    if a.hook:
        hp = os.path.join(root, git(root, 'rev-parse', '--git-path', 'hooks').strip(), a.hook)
        old = open(hp).read() if os.path.isfile(hp) else '#!/bin/sh\n'
        if HOOK_MARK not in old:
            line = 'python3 "$(git rev-parse --show-toplevel)/.odd/odd.py" gate%s || exit 1  %s\n' % (
                ' --recompute' if a.hook == 'pre-push' else '', HOOK_MARK)
            os.makedirs(os.path.dirname(hp), exist_ok=True)
            with open(hp, 'w') as f:
                f.write(old.rstrip('\n') + '\n' + line)
            os.chmod(hp, 0o755)
        did.append('git %s hook' % a.hook)
    print('odd %s set up:\n  ' % VERSION + '\n  '.join(did))
    if not a.ci and not a.hook:
        print('enforcement of record is not installed yet: add --ci (pull requests) or --hook pre-push (this machine).')
    print('start: odd new <slug> "<outcome>" --proof "<command>" --in "<globs>"')


def cmd_doctor(a, root):
    cfg, bad, good = load_config(root), [], []
    msg = recover(root, cfg['proof_timeout'])
    if msg:
        bad.append(msg)
    if not os.path.isfile(odd_dir(root, 'config.json')):
        bad.append('.odd/ is not set up: run odd init')
    v = odd_dir(root, 'odd.py')
    if os.path.isfile(v):
        same = open(v, 'rb').read() == open(os.path.abspath(__file__), 'rb').read()
        (good if same else bad).append('vendored .odd/odd.py %s the tool you are running' % ('matches' if same else 'differs from'))
    hooks_dir = os.path.join(root, git(root, 'rev-parse', '--git-path', 'hooks').strip())
    hooked = [h for h in ('pre-push', 'pre-commit') if os.path.isfile(os.path.join(hooks_dir, h))
              and HOOK_MARK in open(os.path.join(hooks_dir, h)).read()]
    ci = os.path.isfile(os.path.join(root, '.github', 'workflows', 'odd.yml'))
    if hooked or ci:
        good.append('enforcement of record: %s' % ', '.join(['git ' + h for h in hooked] + (['CI workflow'] if ci else [])))
    else:
        bad.append('no enforcement of record: nothing recomputes the gate (odd init --ci, or --hook pre-push)')
    sp = os.path.join(root, '.claude', 'settings.json')
    if os.path.isfile(sp) and '.odd/odd.py' in open(sp).read():
        good.append('Claude Code hooks installed (early feedback)')
    log = state_dir(root, 'hook-errors.log')
    if os.path.isfile(log) and os.path.getsize(log):
        bad.append('editor hooks have failed open %d time(s): see .odd/tmp/hook-errors.log' % sum(1 for _ in open(log)))
    for line in good:
        print('ok   ' + line)
    for line in bad:
        print('WARN ' + line)
    return 1 if bad else 0


# ---------------------------------------------------------------- editor hooks (optional early feedback)

def _fingerprint(root):
    h = hashlib.sha256(git(root, 'status', '--porcelain').encode())
    h.update(sh(['git', 'diff', 'HEAD'], root).stdout.encode())
    return h.hexdigest()


def cmd_hook(a, root):
    """Claude Code hook events on stdin. Any error fails open and is logged for `odd doctor`."""
    try:
        ev = json.load(sys.stdin)
    except ValueError:
        ev = {}
    cfg = load_config(root)
    fp_path = state_dir(root, 'turn-%s.fp' % re.sub(r'[^A-Za-z0-9_-]', '', str(ev.get('session_id', 'x')))[:64])
    os.makedirs(state_dir(root), exist_ok=True)
    msg = recover(root, cfg['proof_timeout'])
    if msg:  # say it once, at the next thing the agent does, instead of letting it rediscover the tree by itself
        if a.event == 'pre-tool':
            print(json.dumps({'hookSpecificOutput': {'hookEventName': 'PreToolUse', 'permissionDecision': 'deny',
                                                     'permissionDecisionReason': 'odd: ' + msg + '. Check the working tree, then retry.'}}))
        elif a.event == 'stop':
            print(json.dumps({'decision': 'block', 'reason': 'odd: ' + msg + '. Check the working tree before ending the turn.'}))
        else:
            print('odd: ' + msg)
        return 0
    if a.event == 'session-start':
        with open(fp_path, 'w') as f:
            f.write(_fingerprint(root))
        outs = collections.Counter(o.status for o in all_outcomes(root))
        if outs:
            print('odd: %s. `python3 .odd/odd.py status` for detail.' % ', '.join('%d %s' % (n, s) for s, n in sorted(outs.items())))
        return 0
    if a.event == 'pre-tool':
        target = (ev.get('tool_input') or {}).get('file_path') or (ev.get('tool_input') or {}).get('notebook_path') or ''
        if not target:
            return 0
        full = os.path.realpath(target if os.path.isabs(target) else os.path.join(ev.get('cwd') or root, target))
        relp = os.path.relpath(full, os.path.realpath(root)).replace(os.sep, '/')
        why = None
        if relp in CONTROL or relp.startswith('.odd/evidence/'):
            why = '%s is written only by the odd tool (settings changes are for a person to make and review).' % relp
        elif cfg.get('guard') == 'boundary' and not relp.startswith('..') and not matches(relp, cfg['exempt']):
            open_ = [o for o in all_outcomes(root) if o.status == 'open']
            if open_ and not any(covers(o, cfg, relp) for o in open_):
                why = ('%s is outside the open outcome%s (%s). Stay inside the boundary, or record why it must grow: '
                       'python3 .odd/odd.py widen %s "%s" "<reason>". Unrelated work is a later outcome.'
                       % (relp, 's' if len(open_) > 1 else '', '; '.join('%s: %s' % (o.slug, o.get('in')) for o in open_),
                          open_[0].slug, relp))
        if why:
            print(json.dumps({'hookSpecificOutput': {'hookEventName': 'PreToolUse', 'permissionDecision': 'deny',
                                                     'permissionDecisionReason': 'odd: ' + why}}))
        return 0
    if a.event == 'stop':
        if ev.get('stop_hook_active') or not cfg.get('stop_gate'):
            return 0
        fp = _fingerprint(root)
        before = open(fp_path).read() if os.path.isfile(fp_path) else None
        with open(fp_path, 'w') as f:
            f.write(fp)
        if before == fp:
            return 0  # this turn changed no files: a question or a discussion is never blocked
        code, lines = gate(root, mode='stop')
        if code == 1:
            print(json.dumps({'decision': 'block', 'reason': 'odd: this turn changed files and the work is not proven yet.\n'
                              + '\n'.join(lines[-6:]) + '\nFinish with `python3 .odd/odd.py done <slug>`, or end honestly '
                              'with `odd park <slug> "<why>"` or `odd abort <slug> "<why>"`.'}))
        return 0
    return 0


def main(argv=None):
    p = argparse.ArgumentParser(prog='odd', description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--version', action='version', version='odd ' + VERSION)
    sub = p.add_subparsers(dest='cmd', required=True)
    s = sub.add_parser('init')
    for flag in ('claude', 'cursor', 'copilot', 'ci'):
        s.add_argument('--' + flag, action='store_true')
    s.add_argument('--hook', choices=['pre-push', 'pre-commit'])
    s = sub.add_parser('new')
    s.add_argument('slug')
    s.add_argument('outcome')
    s.add_argument('--proof', required=True)
    s.add_argument('--in', dest='in_', required=True)
    s.add_argument('--tests', default='')
    s.add_argument('--after')
    s.add_argument('--real', action='store_true')
    s.add_argument('--skip-counterfactual', metavar='REASON')
    for name in ('red', 'done'):
        sub.add_parser(name).add_argument('slug')
    s = sub.add_parser('gate')
    s.add_argument('--base')
    s.add_argument('--recompute', action='store_true')
    for name in ('park', 'abort'):
        s = sub.add_parser(name)
        s.add_argument('slug')
        s.add_argument('reason')
    s = sub.add_parser('widen')
    s.add_argument('slug')
    s.add_argument('glob')
    s.add_argument('reason')
    sub.add_parser('status')
    sub.add_parser('stats').add_argument('--json', action='store_true')
    sub.add_parser('doctor')
    s = sub.add_parser('escape')
    s.add_argument('slug')
    s.add_argument('what')
    sub.add_parser('hook').add_argument('event', choices=['pre-tool', 'stop', 'session-start'])
    a = p.parse_args(argv)
    if a.cmd == 'hook':  # an editor hook must never strand a session: any error passes, and doctor reports it
        root = None
        try:
            root = find_root()
            return cmd_hook(a, root) or 0
        except Exception as e:
            try:
                os.makedirs(state_dir(root), exist_ok=True)
                with open(state_dir(root, 'hook-errors.log'), 'a') as f:
                    f.write('%s %s %r\n' % (now(), a.event, e))
            except Exception:  # nowhere to log (not a repository): still pass
                pass
            return 0
    for name in ('SIGTERM', 'SIGHUP'):  # so an interrupted check still puts the change back before exiting
        if hasattr(signal, name):
            signal.signal(getattr(signal, name), lambda *_: sys.exit(143))
    try:
        root = find_root()
        msg = recover(root, load_config(root)['proof_timeout'])
        if msg and a.cmd != 'doctor':
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
