"""Writing lists of values as delimited text."""


def format_line(fields, delimiter=','):
    """Join `fields` into one line of delimited text, without a line ending.

    Every value is written with str(). A value that contains the delimiter or a
    double quote is wrapped in double quotes, with each double quote inside it doubled.
    """
    out = []
    for value in fields:
        text = str(value)
        if delimiter in text or '"' in text:
            text = '"' + text.replace('"', '""') + '"'
        out.append(text)
    return delimiter.join(out)


def write_rows(rows, delimiter=','):
    """Format every row and join them with newlines. Ends with a newline unless empty."""
    lines = [format_line(row, delimiter) for row in rows]
    if not lines:
        return ''
    return '\n'.join(lines) + '\n'
