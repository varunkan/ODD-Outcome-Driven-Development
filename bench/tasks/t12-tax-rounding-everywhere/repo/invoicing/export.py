"""The CSV file the accountant imports every quarter.

One row per document and tax rate, in the order the documents were issued, highest rate first within a document:

    number,kind,date,customer,rate,net,tax,gross
    INV-0001,invoice,2024-05-02,Cafe Rosa,20,100.00,20.00,120.00
    INV-0001,invoice,2024-05-02,Cafe Rosa,5,13.00,0.65,13.65
    CRN-0001,credit,2024-05-09,Cafe Rosa,20,-50.00,-10.00,-60.00
    TOTAL,,,,,63.00,10.65,73.65

Amounts are in currency units with two decimals; credit notes are negative. The last row adds up every row.
"""
import csv
import io

from .money import format_cents
from .rates import rate_order
from .tax import line_tax

COLUMNS = ('number', 'kind', 'date', 'customer', 'rate', 'net', 'tax', 'gross')


def rows(documents):
    """The export as a list of dictionaries with int cents, without the TOTAL row."""
    out = []
    for document in documents:
        nets = {}
        for line in document.lines:
            nets[line.rate] = nets.get(line.rate, 0) + line.net
        for rate in sorted(nets, key=rate_order):
            net = nets[rate]
            tax = line_tax(net, rate)
            out.append({'number': document.number, 'kind': document.kind, 'date': document.date,
                        'customer': document.customer, 'rate': rate, 'net': net, 'tax': tax, 'gross': net + tax})
    return out


def to_csv(documents):
    """The export as CSV text (lines end in \\r\\n, as the accountant's software expects)."""
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(COLUMNS)
    totals = {'net': 0, 'tax': 0, 'gross': 0}
    for row in rows(documents):
        writer.writerow([row['number'], row['kind'], row['date'], row['customer'], row['rate'],
                         format_cents(row['net']), format_cents(row['tax']), format_cents(row['gross'])])
        for key in totals:
            totals[key] += row[key]
    writer.writerow(['TOTAL', '', '', '', '', format_cents(totals['net']), format_cents(totals['tax']),
                     format_cents(totals['gross'])])
    return buffer.getvalue()


def between(documents, start=None, end=None):
    """The documents dated from `start` to `end` inclusive (YYYY-MM-DD strings; None means open)."""
    return [document for document in documents
            if (start is None or document.date >= start) and (end is None or document.date <= end)]
