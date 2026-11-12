import unittest

from rolegate import Policy, Resolver, Rule


def setup():
    policy = Policy()
    policy.add_role('staff')
    policy.add_rule('staff', 'allow', 'read', 'wiki/**')
    policy.add_role('editor', ['staff'])
    policy.add_rule('editor', 'allow', 'write', 'wiki/**')
    policy.add_role('owner')
    policy.add_rule('owner', 'allow', '*', 'billing/**')
    policy.add_role('guest')
    policy.add_rule('guest', 'deny', '*', 'billing/**')
    policy.assign('ann', 'editor')
    policy.assign('bob', 'staff')
    return policy, Resolver(policy)


class CheckTest(unittest.TestCase):
    def test_own_and_inherited_allows(self):
        _, resolver = setup()
        self.assertTrue(resolver.check('ann', 'write', 'wiki/home'))
        self.assertTrue(resolver.check('ann', 'read', 'wiki/home'))
        self.assertTrue(resolver.check('bob', 'read', 'wiki/a/b'))
        self.assertFalse(resolver.check('bob', 'write', 'wiki/home'))

    def test_nothing_matches_means_refused(self):
        _, resolver = setup()
        self.assertFalse(resolver.check('ann', 'read', 'billing/2026'))
        self.assertFalse(resolver.check('nobody', 'read', 'wiki/home'))
        self.assertEqual(resolver.explain('ann', 'read', 'billing/2026').rule, None)

    def test_any_action(self):
        policy, resolver = setup()
        policy.assign('cy', 'owner')
        self.assertTrue(resolver.check('cy', 'export', 'billing/2026/q1'))

    def test_deny(self):
        policy, resolver = setup()
        policy.assign('dee', 'guest')
        decision = resolver.explain('dee', 'read', 'billing/2026')
        self.assertFalse(decision.allowed)
        self.assertEqual((decision.effect, decision.role), ('deny', 'guest'))

    def test_explain_names_the_rule_and_role(self):
        _, resolver = setup()
        decision = resolver.explain('ann', 'read', 'wiki/home')
        self.assertEqual(decision.rule, Rule('allow', 'read', 'wiki/**'))
        self.assertEqual(decision.role, 'staff')
        self.assertIn('staff', str(decision))

    def test_bad_resource(self):
        _, resolver = setup()
        with self.assertRaises(ValueError):
            resolver.check('ann', 'read', 'wiki/*')

    def test_roles(self):
        policy, resolver = setup()
        policy.assign('ann', 'guest')
        self.assertEqual(resolver.roles('ann'), ['editor', 'staff', 'guest'])


class FilterTest(unittest.TestCase):
    def test_keeps_order_and_drops_refused(self):
        _, resolver = setup()
        resources = ['wiki/b', 'billing/x', 'wiki/a', 'other']
        self.assertEqual(resolver.filter('ann', 'read', resources), ['wiki/b', 'wiki/a'])
        self.assertEqual(resolver.filter('bob', 'write', resources), [])

    def test_agrees_with_check(self):
        policy, resolver = setup()
        policy.assign('dee', 'guest')
        policy.assign('dee', 'staff')
        resources = ['wiki/a', 'billing/1', 'wiki/b/c', 'x']
        for user in ('ann', 'bob', 'dee'):
            for action in ('read', 'write'):
                with self.subTest(user=user, action=action):
                    expected = [r for r in resources if resolver.check(user, action, r)]
                    self.assertEqual(resolver.filter(user, action, resources), expected)


class CacheTest(unittest.TestCase):
    def test_repeated_checks_are_not_worked_out_again(self):
        _, resolver = setup()
        resolver.check('ann', 'read', 'wiki/home')
        resolver.check('bob', 'read', 'wiki/home')
        before = resolver.computed
        for _ in range(3):
            resolver.check('ann', 'read', 'wiki/home')
            resolver.explain('bob', 'read', 'wiki/home')
        self.assertEqual(resolver.computed, before)

    def test_assigning_a_role_is_seen(self):
        policy, resolver = setup()
        self.assertFalse(resolver.check('bob', 'write', 'wiki/home'))
        policy.assign('bob', 'editor')
        self.assertTrue(resolver.check('bob', 'write', 'wiki/home'))
        policy.unassign('bob', 'editor')
        self.assertFalse(resolver.check('bob', 'write', 'wiki/home'))

    def test_a_rule_on_an_assigned_role_is_seen(self):
        policy, resolver = setup()
        self.assertFalse(resolver.check('ann', 'read', 'specs/a'))
        self.assertEqual(resolver.filter('ann', 'read', ['specs/a']), [])
        policy.add_rule('editor', 'allow', 'read', 'specs/**')
        self.assertTrue(resolver.check('ann', 'read', 'specs/a'))
        self.assertEqual(resolver.filter('ann', 'read', ['specs/a']), ['specs/a'])

    def test_capacity(self):
        policy = Policy()
        policy.add_role('r')
        policy.add_rule('r', 'allow', 'read', '**')
        policy.assign('u', 'r')
        from rolegate import DecisionCache
        resolver = Resolver(policy, cache=DecisionCache(capacity=2))
        for name in ('a', 'b', 'c'):
            resolver.check('u', 'read', name)
        self.assertEqual(len(resolver.cache), 2)
        self.assertNotIn(('u', 'read', 'a'), resolver.cache)
