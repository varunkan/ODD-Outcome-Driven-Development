import io
import os
import shutil
import tempfile
import unittest

from rolegate import AuditEntry, Policy, Resolver, Rule, audit_user, save, who_can
from rolegate.cli import main

FINANCE = 'docs/finance/q3.pdf'
DENY_FINANCE = Rule('deny', 'read', 'docs/finance/**')


def reported(parents=('staff', 'restricted')):
    policy = Policy()
    policy.add_role('staff')
    policy.add_rule('staff', 'allow', 'read', 'docs/**')
    policy.add_role('restricted')
    policy.add_rule('restricted', 'deny', 'read', 'docs/finance/**')
    policy.add_role('contractor', parents=list(parents))
    policy.assign('dana', 'contractor')
    return policy


def deep():
    """base (deny finance) <- external <- vendor <- contractor (allow docs/**), and staff (allow docs/**) beside it."""
    policy = Policy()
    policy.add_role('staff')
    policy.add_rule('staff', 'allow', 'read', 'docs/**')
    policy.add_role('base')
    policy.add_rule('base', 'deny', 'read', 'docs/finance/**')
    policy.add_role('external', parents=['base'])
    policy.add_role('vendor', parents=['external'])
    policy.add_role('contractor', parents=['staff', 'vendor'])
    policy.add_rule('contractor', 'allow', 'read', 'docs/**')
    policy.assign('dana', 'contractor')
    policy.add_role('employee', parents=['staff'])
    policy.assign('erin', 'employee')
    return policy


class ReportedCaseTest(unittest.TestCase):
    def test_reported_case(self):
        self.assertFalse(Resolver(reported()).check('dana', 'read', FINANCE))

    def test_parent_order_does_not_matter(self):
        for parents in (('staff', 'restricted'), ('restricted', 'staff')):
            with self.subTest(parents=parents):
                resolver = Resolver(reported(parents))
                self.assertFalse(resolver.check('dana', 'read', FINANCE))
                self.assertFalse(resolver.check('dana', 'read', 'docs/finance/2026/budget.xlsx'))
                self.assertTrue(resolver.check('dana', 'read', 'docs/handbook/leave.md'))

    def test_deny_three_levels_up_beats_an_allow_on_the_assigned_role(self):
        resolver = Resolver(deep())
        self.assertFalse(resolver.check('dana', 'read', FINANCE))
        self.assertTrue(resolver.check('dana', 'read', 'docs/menu.pdf'))
        self.assertTrue(resolver.check('erin', 'read', FINANCE))

    def test_assigned_role_order_does_not_matter(self):
        for order in (('staff', 'restricted'), ('restricted', 'staff')):
            with self.subTest(order=order):
                policy = reported()
                for role in order:
                    policy.assign('finn', role)
                self.assertFalse(Resolver(policy).check('finn', 'read', FINANCE))

    def test_deny_for_every_action_beats_a_specific_allow(self):
        policy = reported()
        policy.add_role('frozen')
        policy.add_rule('frozen', 'deny', '*', 'docs/archive/**')
        policy.set_parents('contractor', ['staff', 'restricted', 'frozen'])
        resolver = Resolver(policy)
        self.assertFalse(resolver.check('dana', 'read', 'docs/archive/2019.pdf'))
        self.assertTrue(resolver.check('dana', 'read', 'docs/current.pdf'))

    def test_allow_and_deny_on_one_role_allow_added_first(self):
        policy = Policy()
        policy.add_role('editor')
        policy.add_rule('editor', 'allow', 'write', 'wiki/**')
        policy.add_rule('editor', 'deny', 'write', 'wiki/policies/**')
        policy.assign('ann', 'editor')
        resolver = Resolver(policy)
        self.assertFalse(resolver.check('ann', 'write', 'wiki/policies/leave'))
        self.assertTrue(resolver.check('ann', 'write', 'wiki/home'))


class EveryWayOfAskingTest(unittest.TestCase):
    def test_explain_names_the_deny(self):
        for policy, role in ((reported(), 'restricted'), (reported(('restricted', 'staff')), 'restricted'),
                             (deep(), 'base')):
            with self.subTest(role=role):
                decision = Resolver(policy).explain('dana', 'read', FINANCE)
                self.assertFalse(decision.allowed)
                self.assertEqual(decision.effect, 'deny')
                self.assertEqual(decision.role, role)
                self.assertEqual(decision.rule, DENY_FINANCE)

    def test_explain_of_an_allowed_request(self):
        decision = Resolver(deep()).explain('dana', 'read', 'docs/menu.pdf')
        self.assertTrue(decision.allowed)
        self.assertEqual(decision.effect, 'allow')

    def test_filter(self):
        resources = ['docs/a.md', FINANCE, 'docs/finance/x/y.pdf', 'docs/b/c.md', 'other/z']
        for policy in (reported(), reported(('restricted', 'staff')), deep()):
            with self.subTest(roles=policy.roles()):
                resolver = Resolver(policy)
                self.assertEqual(resolver.filter('dana', 'read', resources), ['docs/a.md', 'docs/b/c.md'])

    def test_filter_agrees_with_check(self):
        policy = deep()
        policy.assign('finn', 'staff')
        policy.assign('finn', 'external')
        resolver = Resolver(policy)
        resources = ['docs/a.md', FINANCE, 'docs/finance', 'docs/financial.md', 'x']
        for user in ('dana', 'erin', 'finn'):
            with self.subTest(user=user):
                self.assertEqual(resolver.filter(user, 'read', resources),
                                 [r for r in resources if resolver.check(user, 'read', r)])

    def test_who_can(self):
        policy = deep()
        policy.assign('finn', 'vendor')
        policy.assign('finn', 'staff')
        resolver = Resolver(policy)
        self.assertEqual(who_can(resolver, 'read', FINANCE), ['erin'])
        self.assertEqual(who_can(resolver, 'read', 'docs/menu.pdf'), ['dana', 'erin', 'finn'])

    def test_command_line(self):
        directory = tempfile.mkdtemp(prefix='rolegate-t-')
        self.addCleanup(shutil.rmtree, directory, True)
        path = os.path.join(directory, 'policy.json')
        save(deep(), path)
        out = io.StringIO()
        self.assertEqual(main([path, 'check', 'dana', 'read', FINANCE], out=out), 1)
        self.assertEqual(out.getvalue(), 'refused\n')
        out = io.StringIO()
        main([path, 'who-can', 'read', FINANCE], out=out)
        self.assertEqual(out.getvalue(), 'erin\n')


class ReviewSheetTest(unittest.TestCase):
    def same_pattern(self, parents):
        policy = Policy()
        policy.add_role('staff')
        policy.add_rule('staff', 'allow', 'read', 'docs/finance/**')
        policy.add_role('restricted')
        policy.add_rule('restricted', 'deny', 'read', 'docs/finance/**')
        policy.add_role('contractor', parents=list(parents))
        policy.assign('dana', 'contractor')
        return policy

    def test_deny_shown_whatever_the_parent_order(self):
        for parents in (('staff', 'restricted'), ('restricted', 'staff')):
            with self.subTest(parents=parents):
                self.assertEqual(audit_user(self.same_pattern(parents), 'dana'),
                                 [AuditEntry('read', 'docs/finance/**', 'deny', 'restricted')])

    def test_deny_far_up_beats_allow_on_the_assigned_role(self):
        policy = deep()
        policy.add_rule('base', 'deny', 'read', 'docs/**')
        entries = audit_user(policy, 'dana')
        self.assertIn(AuditEntry('read', 'docs/**', 'deny', 'base'), entries)
        self.assertEqual(len([e for e in entries if (e.action, e.pattern) == ('read', 'docs/**')]), 1)
        self.assertIn(AuditEntry('read', 'docs/finance/**', 'deny', 'base'), entries)

    def test_deny_on_a_second_assigned_role(self):
        policy = self.same_pattern(('staff',))
        policy.assign('dana', 'restricted')
        self.assertEqual(audit_user(policy, 'dana'), [AuditEntry('read', 'docs/finance/**', 'deny', 'restricted')])

    def test_other_entries_unchanged(self):
        self.assertEqual(audit_user(reported(), 'dana'), [
            AuditEntry('read', 'docs/**', 'allow', 'staff'),
            AuditEntry('read', 'docs/finance/**', 'deny', 'restricted'),
        ])


class ChangesSeenAtOnceTest(unittest.TestCase):
    def test_deny_added_to_an_inherited_role_after_a_check(self):
        policy = deep()
        resolver = Resolver(policy)
        self.assertTrue(resolver.check('dana', 'read', 'docs/hr/pay.pdf'))
        self.assertEqual(resolver.filter('dana', 'read', ['docs/hr/pay.pdf']), ['docs/hr/pay.pdf'])
        policy.add_rule('base', 'deny', 'read', 'docs/hr/**')
        self.assertFalse(resolver.check('dana', 'read', 'docs/hr/pay.pdf'))
        self.assertEqual(resolver.explain('dana', 'read', 'docs/hr/pay.pdf').role, 'base')
        self.assertEqual(resolver.filter('dana', 'read', ['docs/hr/pay.pdf']), [])
        self.assertTrue(resolver.check('erin', 'read', 'docs/hr/pay.pdf'))

    def test_deny_removed_from_an_inherited_role(self):
        policy = deep()
        resolver = Resolver(policy)
        self.assertFalse(resolver.check('dana', 'read', FINANCE))
        self.assertEqual(resolver.filter('dana', 'read', [FINANCE]), [])
        policy.remove_rule('base', DENY_FINANCE)
        self.assertTrue(resolver.check('dana', 'read', FINANCE))
        self.assertEqual(resolver.filter('dana', 'read', [FINANCE]), [FINANCE])

    def test_parents_changed_above_the_assigned_role(self):
        policy = deep()
        policy.add_role('restricted')
        policy.add_rule('restricted', 'deny', 'read', 'docs/hr/**')
        resolver = Resolver(policy)
        self.assertTrue(resolver.check('dana', 'read', 'docs/hr/pay.pdf'))
        self.assertEqual(resolver.filter('dana', 'read', ['docs/hr/pay.pdf']), ['docs/hr/pay.pdf'])
        policy.set_parents('vendor', ['external', 'restricted'])
        self.assertFalse(resolver.check('dana', 'read', 'docs/hr/pay.pdf'))
        self.assertEqual(resolver.filter('dana', 'read', ['docs/hr/pay.pdf']), [])
        policy.set_parents('vendor', ['external'])
        self.assertTrue(resolver.check('dana', 'read', 'docs/hr/pay.pdf'))

    def test_parent_removed_takes_the_deny_away(self):
        policy = reported()
        resolver = Resolver(policy)
        self.assertFalse(resolver.check('dana', 'read', FINANCE))
        policy.set_parents('contractor', ['staff'])
        self.assertTrue(resolver.check('dana', 'read', FINANCE))

    def test_assign_and_unassign_a_role_that_inherits_a_deny(self):
        policy = deep()
        resolver = Resolver(policy)
        self.assertTrue(resolver.check('erin', 'read', FINANCE))
        policy.assign('erin', 'vendor')
        self.assertFalse(resolver.check('erin', 'read', FINANCE))
        self.assertEqual(resolver.filter('erin', 'read', [FINANCE]), [])
        policy.unassign('erin', 'vendor')
        self.assertTrue(resolver.check('erin', 'read', FINANCE))

    def test_who_can_after_a_change(self):
        policy = deep()
        resolver = Resolver(policy)
        self.assertEqual(who_can(resolver, 'read', 'docs/hr/pay.pdf'), ['dana', 'erin'])
        policy.add_rule('external', 'deny', 'read', 'docs/hr/**')
        self.assertEqual(who_can(resolver, 'read', 'docs/hr/pay.pdf'), ['erin'])

    def test_allow_added_far_up_is_seen(self):
        policy = deep()
        resolver = Resolver(policy)
        self.assertFalse(resolver.check('dana', 'print', 'docs/menu.pdf'))
        policy.add_rule('base', 'allow', 'print', 'docs/**')
        self.assertTrue(resolver.check('dana', 'print', 'docs/menu.pdf'))


class CacheStaysTest(unittest.TestCase):
    def test_repeated_questions_are_not_worked_out_again(self):
        resolver = Resolver(deep())
        questions = [('dana', 'read', FINANCE), ('dana', 'read', 'docs/menu.pdf'), ('erin', 'read', FINANCE)]
        first = [resolver.explain(*q) for q in questions]
        before = resolver.computed
        for _ in range(3):
            self.assertEqual([resolver.explain(*q) for q in questions], first)
            self.assertEqual([resolver.check(*q) for q in questions], [d.allowed for d in first])
        self.assertEqual(resolver.computed, before)

    def test_cached_again_after_a_change(self):
        policy = deep()
        resolver = Resolver(policy)
        resolver.check('dana', 'read', 'docs/hr/pay.pdf')
        policy.add_rule('base', 'deny', 'read', 'docs/hr/**')
        self.assertFalse(resolver.check('dana', 'read', 'docs/hr/pay.pdf'))
        before = resolver.computed
        self.assertFalse(resolver.check('dana', 'read', 'docs/hr/pay.pdf'))
        self.assertFalse(resolver.explain('dana', 'read', 'docs/hr/pay.pdf').allowed)
        self.assertEqual(resolver.computed, before)


if __name__ == '__main__':
    unittest.main()
