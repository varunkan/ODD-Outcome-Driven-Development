"""Reading delimited text into lists and dictionaries."""


def parse_line(line, delimiter=','):
    """Split one line of delimited text into its fields.

    A field may be wrapped in double quotes; the quotes are not part of the value.
    The line ending, if any, is ignored. `delimiter` is a single character.
    """
    fields = []
    for raw in line.rstrip('\r\n').split(delimiter):
        if len(raw) >= 2 and raw[0] == '"' and raw[-1] == '"':
            raw = raw[1:-1]
        fields.append(raw)
    return fields


def read_rows(text, delimiter=','):
    """Parse every non-blank line of `text`. Returns a list of field lists."""
    return [parse_line(line, delimiter) for line in text.splitlines() if line.strip()]


def read_dicts(text, delimiter=','):
    """Parse `text` whose first non-blank line is a header.

    Returns one dictionary per data row, keyed by the header names. A row shorter
    than the header gets empty strings for the missing columns; extra fields are dropped.
    """
    rows = read_rows(text, delimiter)
    if not rows:
        return []
    header = rows[0]
    records = []
    for row in rows[1:]:
        padded = row + [''] * (len(header) - len(row))
        records.append(dict(zip(header, padded)))
    return records
