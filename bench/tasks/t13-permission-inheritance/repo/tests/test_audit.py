import io
import os
import shutil
import tempfile
import unittest

from rolegate import AuditEntry, Policy, Resolver, audit_all, audit_user, format_audit, save, who_can
from rolegate.cli import main


def sample():
    policy = Policy()
    policy.add_role('staff')
    policy.add_rule('staff', 'allow', 'read', 'wiki/**')
    policy.add_role('editor', ['staff'])
    policy.add_rule('editor', 'allow', 'write', 'wiki/drafts/**')
    policy.add_rule('editor', 'deny', 'write', 'wiki/policies/**')
    policy.add_role('finance')
    policy.add_rule('finance', 'allow', 'read', 'billing/**')
    policy.assign('ann', 'editor')
    policy.assign('bob', 'staff')
    policy.assign('bob', 'finance')
    return policy


class AuditTest(unittest.TestCase):
    def test_entries_own_and_inherited(self):
        self.assertEqual(audit_user(sample(), 'ann'), [
            AuditEntry('read', 'wiki/**', 'allow', 'staff'),
            AuditEntry('write', 'wiki/drafts/**', 'allow', 'editor'),
            AuditEntry('write', 'wiki/policies/**', 'deny', 'editor'),
        ])

    def test_several_assigned_roles(self):
        self.assertEqual([(e.pattern, e.role) for e in audit_user(sample(), 'bob')],
                         [('billing/**', 'finance'), ('wiki/**', 'staff')])

    def test_user_without_roles(self):
        self.assertEqual(audit_user(sample(), 'nobody'), [])
        self.assertEqual(format_audit('nobody', []), 'nobody: no rules')

    def test_audit_all(self):
        self.assertEqual(sorted(audit_all(sample())), ['ann', 'bob'])

    def test_sheet(self):
        text = format_audit('ann', audit_user(sample(), 'ann'))
        self.assertIn('deny ', text)
        self.assertIn('from editor', text)
        self.assertTrue(text.startswith('ann:'))

    def test_who_can(self):
        resolver = Resolver(sample())
        self.assertEqual(who_can(resolver, 'read', 'wiki/home'), ['ann', 'bob'])
        self.assertEqual(who_can(resolver, 'write', 'wiki/drafts/menu'), ['ann'])
        self.assertEqual(who_can(resolver, 'write', 'wiki/home'), [])
        self.assertEqual(who_can(resolver, 'write', 'wiki/policies/leave'), [])


class CommandLineTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix='rolegate-')
        self.addCleanup(shutil.rmtree, self.dir, True)
        self.path = os.path.join(self.dir, 'policy.json')
        save(sample(), self.path)

    def run_cli(self, *argv):
        out = io.StringIO()
        status = main([self.path] + list(argv), out=out)
        return status, out.getvalue()

    def test_check(self):
        self.assertEqual(self.run_cli('check', 'ann', 'write', 'wiki/drafts/menu'), (0, 'allowed\n'))
        self.assertEqual(self.run_cli('check', 'ann', 'write', 'wiki/policies/leave'), (1, 'refused\n'))

    def test_explain(self):
        status, text = self.run_cli('explain', 'ann', 'read', 'wiki/home')
        self.assertEqual(status, 0)
        self.assertIn("'staff'", text)

    def test_audit(self):
        status, text = self.run_cli('audit', 'bob')
        self.assertEqual(status, 0)
        self.assertIn('from finance', text)
        self.assertNotIn('ann', text)

    def test_who_can(self):
        self.assertEqual(self.run_cli('who-can', 'read', 'billing/2026'), (0, 'bob\n'))
