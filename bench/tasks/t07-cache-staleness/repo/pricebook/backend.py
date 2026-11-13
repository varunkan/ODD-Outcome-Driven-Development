"""The source of truth for product records.

In production this is a database that takes a noticeable time to answer. MemoryBackend keeps the records in a
dictionary and counts every query, so the number of round trips a piece of code makes can be seen.
"""

FIELDS = ('sku', 'name', 'category', 'price')


class MemoryBackend:
    """Product records by sku. `reads` and `writes` count the queries made so far."""

    def __init__(self):
        self._records = {}
        self.reads = 0
        self.writes = 0

    def exists(self, sku):
        """True when a record with this sku is stored. One query."""
        self.reads += 1
        return sku in self._records

    def load(self, sku):
        """The record with this sku. One query. Raises KeyError when there is none."""
        self.reads += 1
        return dict(self._records[sku])

    def load_many(self, skus):
        """{sku: record} for the given skus, in one query. Skus that are not stored are left out."""
        self.reads += 1
        return {sku: dict(self._records[sku]) for sku in skus if sku in self._records}

    def find_by_category(self, category):
        """Every record in the category, in no particular order. One query."""
        self.reads += 1
        return [dict(record) for record in self._records.values() if record['category'] == category]

    def save(self, record):
        """Store the record, replacing any record with the same sku. One query."""
        missing = [field for field in FIELDS if field not in record]
        if missing:
            raise ValueError('record is missing %s' % ', '.join(missing))
        self.writes += 1
        self._records[record['sku']] = {field: record[field] for field in FIELDS}
