"""Invoices and credit notes. Both are a Document: a numbered list of lines with their net and tax fixed."""
from .money import format_cents
from .rates import check_rate, rate_order

KINDS = ('invoice', 'credit')


class Line:
    """One line of a document. `net` is quantity x unit_price in cents; `tax` is the tax charged on it, in cents.

    On a credit note the quantity, and so the net and the tax, are negative.
    """

    __slots__ = ('description', 'quantity', 'unit_price', 'rate', 'tax')

    def __init__(self, description, quantity, unit_price, rate, tax=None):
        if not isinstance(description, str) or not description.strip():
            raise ValueError('a line needs a description')
        for name, value in (('quantity', quantity), ('unit_price', unit_price)):
            if isinstance(value, bool) or not isinstance(value, int):
                raise ValueError('%s must be a whole number, got %r' % (name, value))
        if quantity == 0:
            raise ValueError('a line of quantity 0 is not a line')
        if unit_price < 0:
            raise ValueError('unit_price must not be negative; refunds are credit notes')
        if tax is not None and (isinstance(tax, bool) or not isinstance(tax, int)):
            raise ValueError('tax must be a whole number of cents, got %r' % (tax,))
        self.description = description
        self.quantity = quantity
        self.unit_price = unit_price
        self.rate = check_rate(rate)
        self.tax = tax

    @property
    def net(self):
        return self.quantity * self.unit_price

    @property
    def gross(self):
        return self.net + self.tax

    def to_dict(self):
        return {'description': self.description, 'quantity': self.quantity, 'unit_price': self.unit_price,
                'rate': self.rate, 'net': self.net, 'tax': self.tax}

    @classmethod
    def from_dict(cls, data):
        line = cls(data['description'], data['quantity'], data['unit_price'], data['rate'], data['tax'])
        if data.get('net', line.net) != line.net:
            raise ValueError('stored net %r is not quantity x unit_price' % (data['net'],))
        return line

    def __repr__(self):
        return 'Line(%r, %r, %r, %r, tax=%r)' % (self.description, self.quantity, self.unit_price, self.rate, self.tax)


class Document:
    """An issued invoice or credit note. Its figures were fixed when it was issued and never change."""

    def __init__(self, number, kind, customer, date, lines, refers_to=None, origins=None):
        if kind not in KINDS:
            raise ValueError('kind must be one of %s' % ', '.join(KINDS))
        if not lines:
            raise ValueError('a document needs at least one line')
        if any(line.tax is None for line in lines):
            raise ValueError('every line of an issued document has its tax worked out')
        self.number = number
        self.kind = kind
        self.customer = customer
        self.date = date
        self.lines = list(lines)
        self.refers_to = refers_to
        # On a credit note: for each line, the index of the line of invoice `refers_to` that it refunds.
        self.origins = list(origins) if origins is not None else None
        if kind == 'credit' and (refers_to is None or self.origins is None or len(self.origins) != len(self.lines)):
            raise ValueError('a credit note names its invoice and the invoice line of each of its lines')

    @property
    def net(self):
        return sum(line.net for line in self.lines)

    @property
    def tax(self):
        return sum(line.tax for line in self.lines)

    @property
    def total(self):
        return self.net + self.tax

    def tax_by_rate(self):
        """{rate: {'net': cents, 'tax': cents, 'gross': cents}}, highest rate first: the summary under the lines."""
        summary = {}
        for line in sorted(self.lines, key=lambda line: rate_order(line.rate)):
            row = summary.setdefault(line.rate, {'net': 0, 'tax': 0, 'gross': 0})
            row['net'] += line.net
            row['tax'] += line.tax
            row['gross'] += line.gross
        return summary

    def to_dict(self):
        data = {'number': self.number, 'kind': self.kind, 'customer': self.customer, 'date': self.date,
                'lines': [line.to_dict() for line in self.lines]}
        if self.refers_to is not None:
            data['refers_to'] = self.refers_to
        if self.origins is not None:
            data['origin_lines'] = list(self.origins)
        return data

    @classmethod
    def from_dict(cls, data):
        return cls(data['number'], data['kind'], data['customer'], data['date'],
                   [Line.from_dict(line) for line in data['lines']], data.get('refers_to'), data.get('origin_lines'))

    def render(self):
        """The document as printed."""
        title = 'INVOICE' if self.kind == 'invoice' else 'CREDIT NOTE'
        out = ['%s %s' % (title, self.number), 'Date: %s' % self.date, 'Customer: %s' % self.customer]
        if self.refers_to:
            out.append('Refers to invoice %s' % self.refers_to)
        out.append('')
        for line in self.lines:
            out.append('%-30s %5d x %9s %6s%% %10s' % (line.description[:30], line.quantity,
                                                       format_cents(line.unit_price), line.rate,
                                                       format_cents(line.net)))
        out.append('')
        for rate, row in self.tax_by_rate().items():
            out.append('Tax at %s%% on %s: %s' % (rate, format_cents(row['net']), format_cents(row['tax'])))
        out.append('Net   %12s' % format_cents(self.net))
        out.append('Tax   %12s' % format_cents(self.tax))
        out.append('Total %12s' % format_cents(self.total))
        return '\n'.join(out) + '\n'
