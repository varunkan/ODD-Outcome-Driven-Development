"""Tests for bench/realtasks.py and for how run.py puts a session and its grade in a task's own environment
(BACKLOG item 42). No network, no model: uv and git are replaced where a test would reach them.

    python3 -m unittest discover -s bench/tests
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import unittest.mock

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_bench import build_fixture, module, read, run_py, write  # noqa: E402

ROW = {'instance_id': 'demo__demo-1', 'repo': 'sphinx-doc/sphinx', 'base_commit': 'abcdef0123456789', 'version': '3.3',
       'created_at': '2020-10-03T00:00:00Z', 'problem_statement': 'add subtracts\n', 'FAIL_TO_PASS': '["test_sum"]',
       'patch': 'diff --git a/calc.py b/calc.py\n--- a/calc.py\n+++ b/calc.py\n@@ -1,2 +1,2 @@\n def add(a, b):\n'
                '-    return a - b\n+    return a + b\n',
       # a test file below the top of the test tree, reading data from beside its folder
       'test_patch': 'diff --git a/tests/unit/test_calc.py b/tests/unit/test_calc.py\n--- a/tests/unit/test_calc.py\n'
                     '+++ b/tests/unit/test_calc.py\n@@ -1,2 +1,6 @@\n from calc import add\n assert add(0, 0) == 0\n'
                     '+\n+def test_sum():\n'
                     '+    five = open(__import__("os").path.dirname(__file__) + "/../data/five.txt").read()\n'
                     '+    assert add(2, 3) == int(five)\n'}


class SpecTest(unittest.TestCase):
    def setUp(self):
        self.mod = module('realtasks')

    def test_spec_names_the_python_and_the_test_needs_of_each_project(self):
        spec = self.mod.spec_for
        for repo in ('pytest-dev/pytest', 'psf/requests', 'pylint-dev/pylint', 'sphinx-doc/sphinx', 'sympy/sympy'):
            self.assertEqual(spec({'repo': repo, 'version': '1.0'}, 'spec')['python'], '3.9', repo)
        self.assertEqual(spec({'repo': 'sphinx-doc/sphinx', 'version': '3.3'}, 'spec')['extras'], 'test')
        self.assertEqual(spec({'repo': 'pylint-dev/pylint', 'version': '2.9'}, 'spec')['requirements'],
                         ['requirements_test.txt'])

    def test_a_version_given_on_the_command_line_replaces_only_the_python(self):
        got = self.mod.spec_for({'repo': 'sphinx-doc/sphinx', 'version': '3.3'}, '3.11')
        self.assertEqual((got['python'], got['extras']), ('3.11', 'test'))
        self.assertEqual(self.mod.spec_for({'repo': 'someone/else'}, '3.12')['python'], '3.12')
        self.assertEqual(self.mod.SPECS['sphinx-doc/sphinx']['python'], '3.9')  # the table itself is not written to

    def test_the_hidden_test_brings_its_test_tree_or_else_its_own_folder(self):
        self.assertEqual(self.mod.test_folder('tests/lint/unittest_lint.py'), 'tests')
        self.assertEqual(self.mod.test_folder('testing/logging/test_fixture.py'), 'testing')
        self.assertEqual(self.mod.test_folder('tests/test_utils.py'), 'tests')
        self.assertEqual(self.mod.test_folder('sympy/core/tests/test_basic.py'), 'sympy/core/tests')  # not the package
        self.assertEqual(self.mod.test_folder('test_requests.py'), '')

    def test_a_project_without_a_spec_is_refused_not_guessed(self):
        with self.assertRaises(RuntimeError) as e:
            self.mod.spec_for({'repo': 'someone/else'}, 'spec')
        self.assertIn('someone/else', str(e.exception))

    def test_requirement_files_are_read_through_and_never_install_the_project(self):
        with tempfile.TemporaryDirectory() as repo:
            write(os.path.join(repo, 'requirements_test.txt'), '-r requirements_min.txt\ncoverage~=5.5  # why\n\n')
            write(os.path.join(repo, 'requirements_min.txt'), '-e .\n.[testutils]\n# a comment\nastroid==2.6.0 # pin\n')
            self.assertEqual(self.mod.requirements(repo, ['requirements_test.txt', 'absent.txt']),
                             ['astroid==2.6.0', 'coverage~=5.5'])


class EnvironTest(unittest.TestCase):
    def setUp(self):
        self.mod = module('realtasks')
        self.work = tempfile.mkdtemp(prefix='realtasks-test-')
        self.addCleanup(shutil.rmtree, self.work, ignore_errors=True)
        self.task = os.path.join(self.work, 'tasks', 't')
        os.makedirs(os.path.join(self.task, 'repo'))

    def test_a_task_without_an_environment_changes_nothing(self):
        self.assertEqual(self.mod.task_environ(self.task, {'PATH': '/bin'}, '/somewhere'), {'PATH': '/bin'})

    def test_the_tree_the_command_runs_in_is_the_code_under_test_from_any_directory(self):
        os.makedirs(os.path.join(self.task, 'env', 'bin'))
        tree = os.path.join(self.work, 'copy')
        env = self.mod.task_environ(self.task, {'PATH': '/bin', 'PYTHONPATH': '/x'}, tree)
        self.assertEqual(env['PATH'], os.path.join(self.task, 'env', 'bin') + os.pathsep + '/bin')
        self.assertEqual(env['VIRTUAL_ENV'], os.path.join(self.task, 'env'))
        self.assertEqual(env['PYTHONPATH'], tree + os.pathsep + '/x')  # absolute: a test's subprocess starts elsewhere
        os.makedirs(os.path.join(self.task, 'repo', 'src'))
        env = self.mod.task_environ(self.task, {'PATH': '/bin'}, tree)
        self.assertEqual(env['PYTHONPATH'], os.path.join(tree, 'src'))

    def test_a_copy_of_the_environment_is_used_in_place_of_the_tasks_own(self):
        os.makedirs(os.path.join(self.task, 'env', 'bin'))
        own = os.path.join(self.work, 'session', 'env')
        env = self.mod.task_environ(self.task, {'PATH': '/bin'}, '/tree', own)
        self.assertEqual((env['PATH'], env['VIRTUAL_ENV']), (os.path.join(own, 'bin') + os.pathsep + '/bin', own))
        self.assertNotIn(self.task, json.dumps(env))  # nothing in it names the task directory, where hidden/ is

    def test_the_grade_does_not_see_the_machines_proxy_settings(self):
        machine = {'PATH': '/bin', 'HTTPS_PROXY': 'http://127.0.0.1:1', 'no_proxy': 'localhost', 'ALL_PROXY': 'x',
                   'PROXY_HOST': 'kept: not a proxy setting'}
        self.assertEqual(self.mod.grade_environ(self.task, machine, '/tree'), machine)  # no environment: as it was
        os.makedirs(os.path.join(self.task, 'env', 'bin'))
        env = self.mod.grade_environ(self.task, machine, '/tree')
        self.assertEqual(sorted(env), ['PATH', 'PROXY_HOST', 'PYTHONPATH', 'VIRTUAL_ENV'])
        self.assertEqual(env['PYTHONPATH'], '/tree')
        self.assertIn('HTTPS_PROXY', self.mod.task_environ(self.task, machine, '/tree'))  # a session keeps its network


class MakeEnvTest(unittest.TestCase):
    def setUp(self):
        self.mod = module('realtasks')
        self.work = tempfile.mkdtemp(prefix='realtasks-test-')
        self.addCleanup(shutil.rmtree, self.work, ignore_errors=True)
        self.task = os.path.join(self.work, 'tasks', 't')
        self.repo = os.path.join(self.task, 'repo')
        write(os.path.join(self.repo, 'requirements_test.txt'), '-e .\nastroid==2.6.0\n')
        self.calls = []

        def sh(cmd, cwd, check=True, **kw):
            self.calls.append((cmd, kw))
            if cmd[:3] == ['uv', 'pip', 'install'] and self.repo in ' '.join(cmd):
                write(os.path.join(self.repo, 'demo.egg-info', 'PKG-INFO'), 'x\n')  # what a build leaves behind
            return subprocess.CompletedProcess(cmd, 0, 'demo\n' if cmd[0].endswith('python') else '', '')
        patch = unittest.mock.patch.object(self.mod, 'sh', sh)
        patch.start()
        self.addCleanup(patch.stop)

    def installs(self):
        return [(c, kw) for c, kw in self.calls if c[:3] == ['uv', 'pip', 'install']]

    def test_the_environment_can_be_copied_and_is_built_as_the_spec_says(self):
        spec = {'python': '3.9', 'extras': 'test', 'requirements': ['requirements_test.txt'], 'pins': ['mpmath==1.3.0']}
        self.mod.make_env(self.task, spec, '2020-12-03T00:00:00Z', '3.3')
        venv = self.calls[0][0]
        self.assertEqual(venv[:2], ['uv', 'venv'])
        self.assertIn('--relocatable', venv)  # run.py gives every session a copy of its own
        self.assertEqual(venv[venv.index('--python') + 1], '3.9')
        project = [(c, kw) for c, kw in self.installs() if any(x.startswith(self.repo) for x in c)]
        self.assertEqual(len(project), 1)
        cmd, kw = project[0]
        self.assertIn(self.repo + '[test]', cmd)
        self.assertIn('astroid==2.6.0', cmd)  # the project's own test requirements, resolved with it
        self.assertNotIn('-e', cmd)
        self.assertEqual(cmd[cmd.index('--exclude-newer') + 1], '2020-12-03T00:00:00Z')
        self.assertEqual(kw['env']['SETUPTOOLS_SCM_PRETEND_VERSION'], '3.3')  # the version the row names
        pins = [c for c, _ in self.installs() if 'mpmath==1.3.0' in c]
        self.assertEqual(len(pins), 1)
        self.assertNotIn('--exclude-newer', pins[0])  # a pin is a decision, whatever its date
        self.assertEqual(self.installs()[-1][0], pins[0])

    def test_one_package_may_be_resolved_as_of_a_later_day_for_the_project_install(self):
        spec = {'python': '3.9', 'newer': {'setuptools': '2023-01-01T00:00:00Z'}}
        self.mod.make_env(self.task, spec, '2020-12-03T00:00:00Z')
        first, project = [c for c, _ in self.installs()]
        self.assertNotIn('--exclude-newer-package', first)
        # pip is the environment's own: a session's "pip install" lands in its copy, never in the machine's Python
        self.assertEqual(first[-3:], ['pytest', 'setuptools<81', 'pip'])
        self.assertEqual(project[project.index('--exclude-newer-package') + 1], 'setuptools=2023-01-01T00:00:00Z')
        self.assertTrue(any(c[:3] == ['uv', 'pip', 'uninstall'] and 'demo' in c for c, _ in self.calls))
        self.assertEqual(sorted(os.listdir(self.repo)), ['requirements_test.txt'])  # the build's leftovers are gone

    def test_nothing_is_resolved_as_of_a_day_before_the_python_existed(self):
        self.mod.make_env(self.task, {'python': '3.9'}, '2018-01-10T07:00:58Z')
        for cmd, _ in self.installs():
            self.assertEqual(cmd[cmd.index('--exclude-newer') + 1], self.mod.PYTHON_RELEASED['3.9'])
        self.assertGreater(self.mod.PYTHON_RELEASED['3.9'], '2020-10-05')
        self.calls.clear()
        self.mod.make_env(self.task, {'python': '3.9'}, '2022-01-04T00:00:00Z')
        self.assertEqual({c[c.index('--exclude-newer') + 1] for c, _ in self.installs()}, {'2022-01-04T00:00:00Z'})

    def test_a_bare_spec_installs_the_project_alone(self):
        self.mod.make_env(self.task, {'python': '3.11'})
        cmd, kw = [(c, kw) for c, kw in self.installs() if self.repo in c][0]
        self.assertNotIn('--exclude-newer', cmd)
        self.assertEqual(kw['env']['SETUPTOOLS_SCM_PRETEND_VERSION'], '0.0.0')
        self.assertEqual(len(self.installs()), 2)  # pytest and setuptools, then the project: no third, empty, install


class BuildTest(unittest.TestCase):
    """build() end to end on a tiny project, with the fetch and the environment replaced."""

    def setUp(self):
        self.mod = module('realtasks')
        self.work = tempfile.mkdtemp(prefix='realtasks-test-')
        self.addCleanup(shutil.rmtree, self.work, ignore_errors=True)
        self.made = []

        self.committed = '2020-11-20T10:00:00Z'

        def checkout(repo, commit, dest):
            write(os.path.join(dest, 'calc.py'), 'def add(a, b):\n    return a - b\n')
            write(os.path.join(dest, 'tests', 'unit', 'test_calc.py'), 'from calc import add\nassert add(0, 0) == 0\n')
            write(os.path.join(dest, 'tests', 'data', 'five.txt'), '5\n')
            # a test folder inside the package, whose fixtures come from the package's conftest.py above it
            write(os.path.join(dest, 'pkg', 'conftest.py'),
                  'import pytest\n\n\n@pytest.fixture\ndef five():\n    return 5\n')
            write(os.path.join(dest, 'pkg', 'sub', 'tests', 'test_calc.py'), 'from calc import add\n')
            write(os.path.join(dest, 'pkg', 'sub', 'tests', 'other.py'), '')
            write(os.path.join(dest, 'pkg', 'sub', 'code.py'), 'SECRET = 1\n')
            return self.committed

        def make_env(task_dir, spec, before=None, version=None):
            self.made.append((spec, before, version))
            # a stand-in for a project's own environment: its python3 says so, then runs the tests
            write(os.path.join(task_dir, 'env', 'bin', 'python3'),
                  '#!/bin/sh\necho "$PYTHONPATH$HTTPS_PROXY" > "$(dirname "$0")/../seen"\nexec %s "$@"\n'
                  % sys.executable)
            os.chmod(os.path.join(task_dir, 'env', 'bin', 'python3'), 0o755)
        for name, fake in (('checkout', checkout), ('make_env', make_env)):
            patch = unittest.mock.patch.object(self.mod, name, fake)
            patch.start()
            self.addCleanup(patch.stop)

    def needs_pytest(self):
        """These tests run a real grade, and a grade is a pytest run; CI installs pytest so they are not skipped there."""
        try:
            import pytest  # noqa: F401
        except ImportError:
            self.skipTest('pytest is needed to run the grade')

    @unittest.skipUnless(shutil.which('git'), 'git is needed to apply the patches')
    def test_a_task_is_built_and_graded_in_the_environment_its_spec_names(self):
        self.needs_pytest()
        with unittest.mock.patch.dict(os.environ, HTTPS_PROXY='http://127.0.0.1:1'):
            why = self.mod.build(dict(ROW), self.work, strict=True, python='spec')
        self.assertEqual(why, '')
        # dependencies as of the commit's day when that is after the issue's: the commit may pin what came between
        self.assertEqual(self.made, [(dict(self.mod.SPECS['sphinx-doc/sphinx']), self.committed, '3.3')])
        self.committed = '2019-01-01T00:00:00Z'
        self.assertEqual(self.mod.build(dict(ROW), self.work, strict=True, python='spec'), '')
        self.assertEqual(self.made[-1][1], ROW['created_at'])
        task_dir = os.path.join(self.work, 'tasks', ROW['instance_id'])
        task = read(os.path.join(task_dir, 'task.json'))
        self.assertEqual(task['python'], '3.9')  # the record says which Python the task was checked on
        self.assertTrue(0 <= task['grade_seconds'] < 60, task)  # how long the grade took here, for run.py's limit
        # the whole test tree is the hidden test's surroundings: its data and conftest files are where it looks
        self.assertTrue(os.path.isfile(os.path.join(task_dir, 'hidden', 'tests_hidden', 'unit', 'test_calc.py')))
        self.assertTrue(os.path.isfile(os.path.join(task_dir, 'hidden', 'tests_hidden', 'data', 'five.txt')))
        self.assertTrue(task['grade'].endswith(' tests_hidden/unit/test_calc.py'), task['grade'])
        # the grade ran through the environment's python3, with the graded copy itself as the code under test
        seen = read(os.path.join(task_dir, 'env', 'seen')).strip()
        self.assertTrue(os.path.isabs(seen) and os.path.basename(seen) == 'p', seen)
        self.assertNotEqual(os.path.dirname(seen), task_dir)

    @unittest.skipUnless(shutil.which('git'), 'git is needed to apply the patches')
    def test_a_test_folder_inside_the_package_keeps_the_conftest_files_above_it(self):
        self.needs_pytest()
        row = dict(ROW, test_patch='diff --git a/pkg/sub/tests/test_calc.py b/pkg/sub/tests/test_calc.py\n'
                   '--- a/pkg/sub/tests/test_calc.py\n+++ b/pkg/sub/tests/test_calc.py\n@@ -1 +1,4 @@\n'
                   ' from calc import add\n+\n+def test_sum(five):\n+    assert add(2, 3) == five\n')
        self.assertEqual(self.mod.build(row, self.work, strict=True, python='spec'), '')
        task_dir = os.path.join(self.work, 'tasks', ROW['instance_id'])
        hidden = os.path.join(task_dir, 'hidden', 'tests_hidden')
        found = sorted(os.path.relpath(os.path.join(b, f), hidden) for b, _, fs in os.walk(hidden) for f in fs)
        self.assertEqual(found, ['pkg/conftest.py', 'pkg/sub/tests/other.py', 'pkg/sub/tests/test_calc.py'])
        self.assertTrue(read(os.path.join(task_dir, 'task.json'))['grade'].endswith(
            ' tests_hidden/pkg/sub/tests/test_calc.py'))

    @unittest.skipUnless(shutil.which('git'), 'git is needed to apply the patches')
    def test_a_refused_task_says_how_its_grade_ended_and_can_be_kept_aside(self):
        self.needs_pytest()
        rows = os.path.join(self.work, 'rows')
        broken = ROW['test_patch'].replace('+def test_sum', '+import no_such_package_xyz\n+def test_sum') \
            .replace('@@ -1,2 +1,5 @@', '@@ -1,2 +1,6 @@')
        write(os.path.join(rows, 'rows0.json'), json.dumps({'rows': [{'row': dict(ROW, test_patch=broken)}]}))
        out = os.path.join(self.work, 'root')
        args = ['--rows', rows, '--out', out, '--strict', '--python', 'spec', ROW['instance_id']]
        with unittest.mock.patch('builtins.print') as said:
            self.assertEqual(self.mod.main(args), 1)
        self.assertIn('no_such_package_xyz', said.call_args[0][0])
        self.assertEqual(os.listdir(os.path.join(out, 'tasks')), [])
        self.assertFalse(os.path.exists(os.path.join(out, 'refused')))
        with unittest.mock.patch('builtins.print'):
            self.assertEqual(self.mod.main(args + ['--keep-refused']), 1)
        self.assertEqual(os.listdir(os.path.join(out, 'tasks')), [])  # never where run.py would find it
        self.assertTrue(os.path.isdir(os.path.join(out, 'refused', ROW['instance_id'], 'repo')))

    def test_main_refuses_a_project_without_a_spec_and_names_why(self):
        rows = os.path.join(self.work, 'rows')
        write(os.path.join(rows, 'rows0.json'), json.dumps({'rows': [{'row': dict(ROW, repo='someone/else')}]}))
        out = os.path.join(self.work, 'root')
        with unittest.mock.patch('builtins.print') as said:
            status = self.mod.main(['--rows', rows, '--out', out, '--strict', '--python', 'spec', ROW['instance_id']])
        self.assertEqual(status, 1)
        self.assertIn('someone/else', said.call_args[0][0])
        self.assertFalse(os.path.exists(os.path.join(out, 'tasks', ROW['instance_id'])))


class GradeTimeTest(unittest.TestCase):
    @unittest.skipUnless(os.path.isdir('/proc/self'), 'needs Linux /proc')
    def test_a_command_stopped_at_its_time_limit_leaves_nothing_running(self):
        mod = module('realtasks')
        work = tempfile.mkdtemp(prefix='realtasks-test-')
        self.addCleanup(shutil.rmtree, work, ignore_errors=True)
        with self.assertRaises(subprocess.TimeoutExpired):  # a grade is a shell line: its pytest is the shell's child
            mod.sh('sleep 60 & echo $! > pid; wait', work, timeout=1)
        pid = read(os.path.join(work, 'pid')).strip()
        self.addCleanup(subprocess.run, ['kill', '-9', pid], capture_output=True)
        try:
            with open('/proc/%s/stat' % pid) as f:
                state = f.read().rsplit(')', 1)[1].split()[0]
        except OSError:
            state = 'gone'
        self.assertIn(state, ('gone', 'Z'))

    def test_a_slow_whole_file_grade_gets_the_time_it_was_measured_to_need(self):
        mod = module('run')
        work = tempfile.mkdtemp(prefix='bench-env-test-')
        self.addCleanup(shutil.rmtree, work, ignore_errors=True)
        task_dir, copy = os.path.join(work, 'task'), os.path.join(work, 'copy')
        write(os.path.join(task_dir, 'hidden', 'tests_hidden', 'present.txt'), 'x\n')
        os.makedirs(os.path.join(task_dir, 'repo'))
        os.makedirs(copy)
        for seconds, limit in ((None, mod.GRADE_TIMEOUT), (20, mod.GRADE_TIMEOUT), (400, 1200)):
            task = dict({'dir': task_dir, 'grade': 'true'}, **({'grade_seconds': seconds} if seconds else {}))
            with unittest.mock.patch.object(mod, 'run', return_value=(0, '', '')) as ran:
                mod.grade(task, copy, {'PATH': os.environ['PATH']}, {'final': '', 'claim': 'none', 'claim_reason': '',
                                                                      'warnings': []}, [])
            self.assertEqual(ran.call_args[0][0], 'true')
            self.assertEqual(ran.call_args[0][3], limit, seconds)


ENV_AGENT = r'''
import json, os, shutil, subprocess
tool = shutil.which('envtool')
seen = {'tool': tool, 'venv': os.environ.get('VIRTUAL_ENV'), 'pythonpath': os.environ.get('PYTHONPATH'),
        'cwd': os.getcwd(), 'said': subprocess.run(['envtool'], capture_output=True, text=True).stdout.strip(),
        'setup': open('setup-saw.txt').read().strip()}
with open(tool, 'a') as f:  # a session may break its own environment: a pip install, an edit
    f.write('echo changed-by-the-session\n')
with open(os.path.join(os.environ['FAKE_LOG_DIR'], 'env.json'), 'w') as f:
    json.dump(seen, f)
print(json.dumps({'result': 'ran %s\nRESULT: DONE' % tool}))
'''


class SessionEnvironmentTest(unittest.TestCase):
    """run.py with a fake agent: the session, the arm's scripts and the grade all run in the task's environment."""

    def setUp(self):
        self.work = tempfile.mkdtemp(prefix='bench-env-test-')
        self.addCleanup(shutil.rmtree, self.work, ignore_errors=True)
        self.root = build_fixture(os.path.join(self.work, 'root'))
        self.task = os.path.join(self.root, 'tasks', 'tiny-add')
        self.tool = os.path.join(self.task, 'env', 'bin', 'envtool')
        write(self.tool, '#!/bin/sh\necho task-env\n')
        os.chmod(self.tool, 0o755)
        task = read(os.path.join(self.task, 'task.json'))
        # passes only with the task's own, unchanged environment and the graded tree as the code under test
        # real paths (pwd -P): macOS reaches its temporary folder through a link, and a shell reports the real one
        task['grade'] = ('test "$(envtool)" = task-env && test "$(cd "$PYTHONPATH" && pwd -P)" = "$(pwd -P)"'
                         ' && test -d tests_hidden && test -z "$HTTPS_PROXY"')
        write(os.path.join(self.task, 'task.json'), json.dumps(task))
        arm = os.path.join(self.root, 'arms', 'envarm')
        write(os.path.join(arm, 'setup.sh'), '#!/usr/bin/env bash\nset -euo pipefail\nenvtool > setup-saw.txt\n')
        write(os.path.join(arm, 'prompt.md'), '{ticket}\n')
        write(os.path.join(arm, 'post.sh'),
              '#!/usr/bin/env bash\nenvtool | grep -q task-env && test "$(cd "$PYTHONPATH" && pwd -P)" = "$(pwd -P)"\n')
        write(os.path.join(self.root, 'env_agent.py'), ENV_AGENT)

    def test_session_arm_scripts_and_grade_run_in_the_tasks_environment(self):
        out = os.path.join(self.work, 'out')
        r = run_py(self.work, ['--root', self.root, '--tasks', 'tiny-add', '--arms', 'envarm', '--out', out],
                   fake='%s %s' % (sys.executable, os.path.join(self.root, 'env_agent.py')),
                   HTTPS_PROXY='http://127.0.0.1:1')
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        rec = read(os.path.join(out, 'tiny-add.envarm.1.json'))
        seen = read(os.path.join(self.work, 'seen', 'env.json'))
        self.assertIsNone(rec['error'])
        self.assertEqual((seen['said'], seen['setup']), ('task-env', 'task-env'))
        # the session's environment is a copy of its own, outside the bench root (where hidden/ sits beside env/)
        self.assertFalse(seen['tool'].startswith(self.root), seen['tool'])
        self.assertEqual(seen['venv'], os.path.dirname(os.path.dirname(seen['tool'])))
        # real paths: on macOS the temporary folder is reached through a link, and a process reports its real cwd
        self.assertEqual(os.path.realpath(os.path.dirname(seen['venv'])),
                         os.path.realpath(os.path.dirname(os.path.dirname(seen['cwd']))))
        self.assertEqual(os.path.realpath(seen['pythonpath']), os.path.realpath(seen['cwd']))
        self.assertFalse(rec['contaminated'], rec['contaminated_by'])  # its path is in the transcript, and is its own
        self.assertIn('VIRTUAL_ENV', rec['env_passed'])
        self.assertEqual(rec['arm_check'], 0)
        # what the session did to its copy reached neither the task nor the grade
        self.assertEqual(read(self.tool), '#!/bin/sh\necho task-env\n')
        self.assertTrue(rec['passed'], rec)
        self.assertFalse(os.path.exists(seen['venv']))  # removed with the session

    def test_a_task_without_an_environment_runs_as_before(self):
        shutil.rmtree(os.path.join(self.task, 'env'))
        out = os.path.join(self.work, 'out')
        r = run_py(self.work, ['--root', self.root, '--tasks', 'tiny-add', '--arms', 'honest', '--out', out],
                   fake='%s %s' % (sys.executable, os.path.join(self.root, 'fake_agent.py')))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        rec = read(os.path.join(out, 'tiny-add.honest.1.json'))
        self.assertNotIn('VIRTUAL_ENV', rec['env_passed'])
        self.assertNotIn('PYTHONPATH', rec['env_passed'])


if __name__ == '__main__':
    unittest.main()
