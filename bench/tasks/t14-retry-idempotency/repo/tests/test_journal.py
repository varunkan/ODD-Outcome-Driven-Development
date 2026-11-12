import json

from jobrun import Journal

from helpers import TempDirTest


class JournalTest(TempDirTest):
    def test_missing_file_has_no_records(self):
        self.assertEqual(Journal(self.path()).records(), [])

    def test_records_come_back_in_order(self):
        journal = Journal(self.path())
        journal.append({'job': 'a', 'event': 'submitted', 'kind': 'notify', 'payload': {}})
        journal.append({'job': 'a', 'event': 'started'})
        journal.append({'job': 'a', 'event': 'done', 'output': {'message': 'm-1'}})
        self.assertEqual([r['event'] for r in journal.records()], ['submitted', 'started', 'done'])
        self.assertEqual(len(journal), 3)

    def test_one_json_object_per_line(self):
        journal = Journal(self.path())
        journal.append({'job': 'a', 'event': 'started', 'at': 5.0})
        with open(self.path()) as f:
            lines = f.read().splitlines()
        self.assertEqual([json.loads(line) for line in lines], [{'job': 'a', 'event': 'started', 'at': 5.0}])

    def test_unknown_event_is_refused(self):
        with self.assertRaises(ValueError):
            Journal(self.path()).append({'job': 'a', 'event': 'paused'})

    def test_a_last_line_cut_short_is_skipped(self):
        journal = Journal(self.path())
        journal.append({'job': 'a', 'event': 'submitted', 'kind': 'notify', 'payload': {}})
        with open(self.path(), 'a') as f:
            f.write('{"job": "a", "ev')
        self.assertEqual([r['event'] for r in journal.records()], ['submitted'])

    def test_a_bad_line_in_the_middle_raises(self):
        with open(self.path(), 'w') as f:
            f.write('nonsense\n{"job": "a", "event": "started"}\n')
        with self.assertRaises(ValueError):
            Journal(self.path()).records()

    def test_unknown_keys_are_kept(self):
        with open(self.path(), 'w') as f:
            f.write('{"job": "a", "event": "started", "till": 4}\n')
        self.assertEqual(Journal(self.path()).records()[0]['till'], 4)
