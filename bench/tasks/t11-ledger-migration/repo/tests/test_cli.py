import io
import os
import tempfile
import unittest

from ledgerbook import load
from ledgerbook.cli import main


class CommandLineTest(unittest.TestCase):
    def run_cli(self, *argv):
        out = io.StringIO()
        code = main(list(argv), out=out)
        return code, out.getvalue()

    def test_init_add_balance_report(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, 'shop.ledger')
            self.assertEqual(self.run_cli('init', path), (0, ''))
            self.assertEqual(self.run_cli('add', path, '2024-03-01', 'checking', 'salary', '2,500.00', 'pay'),
                             (0, '1\n'))
            self.assertEqual(self.run_cli('add', path, '2024-03-02', 'checking', 'groceries', '-45.99'), (0, '2\n'))
            code, out = self.run_cli('balance', path)
            self.assertEqual(code, 0)
            self.assertIn('2,454.01', out)
            code, out = self.run_cli('report', path, '2024-03')
            self.assertIn('Report for 2024-03 (2 entries)', out)
            code, out = self.run_cli('over', path, '2024-03', 'groceries=40.00')
            self.assertEqual(out, 'groceries: spent 45.99 of 40.00\n')
            self.assertEqual(len(load(path)), 2)
