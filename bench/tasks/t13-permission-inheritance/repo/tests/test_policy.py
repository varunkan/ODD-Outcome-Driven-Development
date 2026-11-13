import os
import shutil
import tempfile
import unittest

from rolegate import Policy, Rule, UnknownRole, load, save


def sample():
    policy = Policy()
    policy.add_role('staff')
    policy.add_rule('staff', 'allow', 'read', 'wiki/**')
    policy.add_role('editor', ['staff'])
    policy.add_rule('editor', 'allow', 'write', 'wiki/drafts/**')
    policy.add_rule('editor', 'deny', 'write', 'wiki/policies/**')
    policy.assign('ann', 'editor')
    policy.assign('bob', 'staff')
    return policy


class PolicyTest(unittest.TestCase):
    def test_rules_are_the_roles_own(self):
        policy = sample()
        self.assertEqual(policy.rules('staff'), [Rule('allow', 'read', 'wiki/**')])
        self.assertEqual(len(policy.rules('editor')), 2)

    def test_adding_a_rule_twice_keeps_one(self):
        policy = sample()
        policy.add_rule('staff', 'allow', 'read', 'wiki/**')
        self.assertEqual(len(policy.rules('staff')), 1)

    def test_bad_rules(self):
        policy = sample()
        for effect, action, pattern in (('maybe', 'read', 'x'), ('allow', '', 'x'), ('allow', 'read', '/x')):
            with self.subTest(effect=effect, action=action, pattern=pattern), self.assertRaises(ValueError):
                policy.add_rule('staff', effect, action, pattern)
        with self.assertRaises(UnknownRole):
            policy.add_rule('nope', 'allow', 'read', 'x')

    def test_remove_rule(self):
        policy = sample()
        policy.remove_rule('editor', Rule('deny', 'write', 'wiki/policies/**'))
        self.assertEqual(policy.rules('editor'), [Rule('allow', 'write', 'wiki/drafts/**')])
        with self.assertRaises(KeyError):
            policy.remove_rule('editor', Rule('deny', 'write', 'wiki/policies/**'))

    def test_users(self):
        policy = sample()
        policy.assign('ann', 'staff')
        self.assertEqual(policy.roles_of('ann'), ['editor', 'staff'])
        self.assertEqual(policy.users_with('staff'), ['ann', 'bob'])
        policy.unassign('bob', 'staff')
        self.assertEqual(policy.users(), ['ann'])
        self.assertEqual(policy.roles_of('bob'), [])

    def test_a_held_role_cannot_be_removed(self):
        policy = sample()
        with self.assertRaises(ValueError):
            policy.remove_role('editor')

    def test_subscribers_hear_every_change(self):
        policy = Policy()
        heard = []
        policy.subscribe(lambda kind, role=None, user=None: heard.append((kind, role, user)))
        policy.add_role('a')
        policy.add_role('b')
        policy.add_rule('a', 'allow', 'read', 'x')
        policy.set_parents('b', ['a'])
        policy.assign('u', 'b')
        self.assertEqual(heard, [('role', 'a', None), ('role', 'b', None), ('rule', 'a', None),
                                 ('parents', 'b', None), ('user', None, 'u')])

    def test_round_trip_through_a_dict(self):
        policy = sample()
        again = Policy.from_dict(policy.to_dict())
        self.assertEqual(again.to_dict(), policy.to_dict())
        self.assertEqual(again.graph.parents('editor'), ('staff',))


class StorageTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix='rolegate-')
        self.addCleanup(shutil.rmtree, self.dir, True)

    def test_save_and_load(self):
        path = os.path.join(self.dir, 'policy.json')
        save(sample(), path)
        self.assertEqual(load(path).to_dict(), sample().to_dict())
        self.assertEqual(os.listdir(self.dir), ['policy.json'])

    def test_unknown_format(self):
        path = os.path.join(self.dir, 'policy.json')
        with open(path, 'w') as f:
            f.write('{"format": 2, "roles": {}}')
        with self.assertRaises(ValueError):
            load(path)
