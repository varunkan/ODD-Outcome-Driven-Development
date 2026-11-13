"""The Spec Kit arm: its prompt offers both processes Spec Kit documents, and setup.sh installs every skill it names."""
import os
import re
import unittest

ARM = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'arms', 'speckit')


def read(name):
    with open(os.path.join(ARM, name), encoding='utf-8') as f:
        return f.read()


class SpeckitArmTest(unittest.TestCase):
    def setUp(self):
        self.prompt, self.setup = read('prompt.md'), read('setup.sh')

    def setup_list(self, var):
        return re.search(r'^%s="([^"]*)"' % var, self.setup, re.M).group(1).split()

    def test_the_prompt_names_exactly_the_skills_setup_installs(self):
        named = set(re.findall(r'/speckit-([a-z-]+)', self.prompt))
        self.assertEqual(named, set(self.setup_list('SKILLS') + self.setup_list('BUG_SKILLS')))
        self.assertIn('extension add bug', self.setup)

    def test_the_prompt_leaves_the_choice_of_process_to_the_agent(self):
        # Naming the task's kind would hand this arm information no other arm gets.
        for word in ('bugfix', 'feature request', 'defect', 'trap', 'vague', 'impossible'):
            self.assertNotIn(word, self.prompt.lower())
        self.assertEqual(self.prompt.count('{ticket}'), 1)

    def test_the_prompt_has_no_hint_the_framework_does_not_tell_a_user_to_write(self):
        self.assertNotIn('existing architecture', self.prompt)

    def test_the_common_ending_is_left_to_run_py(self):
        tail = read(os.path.join('..', 'TAIL.md')).splitlines()
        for line in tail + ['Nobody is available', 'RESULT:']:
            self.assertNotIn(line, self.prompt)

    def test_version_and_the_caveats_to_print(self):
        version = read('VERSION').splitlines()
        self.assertEqual(len(version), 1)
        self.assertIn(re.search(r'^VERSION="([^"]+)"', self.setup, re.M).group(1), version[0])
        notes = read('NOTES.md')
        self.assertIn('\n## To state with the results\n', notes)
        section = notes.split('\n## To state with the results\n', 1)[1].split('\n## ', 1)[0]
        for needle in ('speckit-bug-assess', 'speckit-specify', 'changed_lines_py'):
            self.assertIn(needle, section)


if __name__ == '__main__':
    unittest.main()
