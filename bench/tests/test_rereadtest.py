"""bench/rereadtest.py: the host list and the bands are the ruling's (docs/evidence/data/real/ruling-6.md)."""
import collections
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import rereadtest  # noqa: E402


class RereadTest(unittest.TestCase):
    def test_the_core_is_24_hosts_13_wrong_on_five_tasks_and_the_extension_8_right(self):
        core = [h for h in rereadtest.HOSTS if h[4] == 'core']
        self.assertEqual((len(core), sum(h[3] == 'W' for h in core)), (24, 13))
        self.assertEqual(len({h[0] for h in core if h[3] == 'W'}), 5)
        ext = [h for h in rereadtest.HOSTS if h[4] == 'extension']
        self.assertEqual((len(ext), {h[3] for h in ext}), (8, {'R'}))
        self.assertEqual(max(collections.Counter(h[:3] for h in rereadtest.HOSTS).values()), 1, 'a host is listed once')

    def test_the_comparisons_the_core_allows_are_52_wrong_and_30_right(self):
        core = [h for h in rereadtest.HOSTS if h[4] == 'core']
        per = collections.Counter(h[0] for h in core)
        self.assertEqual(sum(per[h[0]] for h in core if h[3] == 'W'), 52)
        self.assertEqual(sum(per[h[0]] for h in core if h[3] == 'R'), 30)

    def test_the_bands(self):
        band = rereadtest.band
        self.assertEqual(band(0.60, 0.15, 40, 30, 0.1, 0, 4), 'BETTER')
        self.assertEqual(band(0.60, 0.15, 40, 30, 0.1, 0, 3), 'LIKE')
        self.assertEqual(band(0.40, 0.25, 40, 30, 0.1, 0, 3), 'LIKE')
        self.assertEqual(band(0.40, 0.26, 40, 30, 0.1, 0, 3), 'WORSE', 'A - B under 15 points')
        self.assertEqual(band(0.39, 0.0, 40, 30, 0.1, 0, 5), 'WORSE')
        self.assertEqual(band(0.9, 0.41, 40, 30, 0.1, 0, 5), 'WORSE')
        for args in ((0.9, 0.0, 25, 30, 0.1, 0, 5), (0.9, 0.0, 40, 14, 0.1, 0, 5), (0.9, 0.0, 40, 30, 0.34, 0, 5),
                     (0.9, 0.0, 40, 30, 0.1, 3, 5)):
            self.assertEqual(band(*args), 'NOT TESTED', args)

    def test_the_commands_words_are_read_as_its_verdict(self):
        self.assertEqual(rereadtest.verdict(0, 'x\ntwo readings agree.'), 'agree')
        self.assertEqual(rereadtest.verdict(1, 'odd: ... one of the two readings is wrong, and'), 'disagree')
        self.assertEqual(rereadtest.verdict(0, 'not compared: no proof'), 'not compared')
        self.assertEqual(rereadtest.verdict(2, 'odd: could not run: x'), 'could not run (exit 2)')


if __name__ == '__main__':
    unittest.main()
