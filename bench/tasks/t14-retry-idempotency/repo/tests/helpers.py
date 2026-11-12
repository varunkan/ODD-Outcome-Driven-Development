import os
import shutil
import tempfile
import unittest


class TempDirTest(unittest.TestCase):
    """A test with its own directory for journal files."""

    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix='jobrun-')
        self.addCleanup(shutil.rmtree, self.dir, True)

    def path(self, name='journal.jsonl'):
        return os.path.join(self.dir, name)


class Clock:
    def __init__(self, start=1000.0):
        self.now = start

    def __call__(self):
        self.now += 1.0
        return self.now
