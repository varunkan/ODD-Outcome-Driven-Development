"""The book of issued documents, kept in one JSON file. Numbers are INV-0001, INV-0002, ... and CRN-0001, ..."""
import json
import os
import tempfile

from .document import Document, Line
from .tax import line_tax

FORMAT = 1


class RefundError(ValueError):
    """A refund that cannot be made: unknown invoice or line, or more units than are left to refund."""


class Book:
    def __init__(self, path=None):
        """A book stored at `path` (created on the first issue), or kept only in memory when `path` is None."""
        self.path = path
        self._documents = {}
        if path is not None and os.path.exists(path):
            with open(path, encoding='utf-8') as handle:
                data = json.load(handle)
            if data.get('format') != FORMAT:
                raise ValueError('%s: not an invoicing book this version can read' % path)
            for item in data['documents']:
                document = Document.from_dict(item)
                self._documents[document.number] = document

    # reading

    def get(self, number):
        try:
            return self._documents[number]
        except KeyError:
            raise KeyError('no document %r' % (number,)) from None

    def documents(self, kind=None):
        """Every document in the order it was issued, optionally only invoices or only credit notes."""
        return [document for document in self._documents.values() if kind is None or document.kind == kind]

    def credit_notes_for(self, number):
        return [document for document in self.documents('credit') if document.refers_to == number]

    def refunded(self, number, index):
        """How many units of line `index` (0-based) of invoice `number` have been refunded so far."""
        units = 0
        for note in self.credit_notes_for(number):
            for line, origin in zip(note.lines, note.origins):
                if origin == index:
                    units -= line.quantity
        return units

    # issuing

    def issue_invoice(self, customer, date, lines):
        """Issue an invoice for `lines` (Line objects without tax) and return it. The tax is worked out here."""
        if not lines:
            raise ValueError('an invoice needs at least one line')
        priced = []
        for line in lines:
            if line.quantity < 0:
                raise ValueError('an invoice line has a positive quantity; refunds are credit notes')
            priced.append(Line(line.description, line.quantity, line.unit_price, line.rate,
                               line_tax(line.net, line.rate)))
        document = Document(self._next_number('INV'), 'invoice', customer, date, priced)
        self._add(document)
        return document

    def refund(self, number, date, quantities=None):
        """Issue a credit note against invoice `number` and return it.

        `quantities` is {line index (0-based): units to refund}; None refunds everything not yet refunded.
        """
        invoice = self.get(number)
        if invoice.kind != 'invoice':
            raise RefundError('%s is not an invoice' % number)
        if quantities is None:
            quantities = {index: line.quantity - self.refunded(number, index)
                          for index, line in enumerate(invoice.lines)}
            quantities = {index: units for index, units in quantities.items() if units}
        if not quantities:
            raise RefundError('nothing left to refund on %s' % number)
        credit_lines = []
        origins = []
        for index in sorted(quantities):
            units = quantities[index]
            if not isinstance(index, int) or not 0 <= index < len(invoice.lines):
                raise RefundError('%s has no line %r' % (number, index))
            if isinstance(units, bool) or not isinstance(units, int) or units <= 0:
                raise RefundError('units to refund must be a positive whole number, got %r' % (units,))
            line = invoice.lines[index]
            left = line.quantity - self.refunded(number, index)
            if units > left:
                raise RefundError('line %d of %s has %d units left to refund, not %d' % (index, number, left, units))
            net = -units * line.unit_price
            credit_lines.append(Line(line.description, -units, line.unit_price, line.rate, line_tax(net, line.rate)))
            origins.append(index)
        note = Document(self._next_number('CRN'), 'credit', invoice.customer, date, credit_lines, refers_to=number,
                        origins=origins)
        self._add(note)
        return note

    # internals

    def _next_number(self, prefix):
        taken = [int(number[4:]) for number in self._documents if number.startswith(prefix + '-')]
        return '%s-%04d' % (prefix, max(taken, default=0) + 1)

    def _add(self, document):
        self._documents[document.number] = document
        self._save()

    def _save(self):
        if self.path is None:
            return
        data = {'format': FORMAT, 'documents': [document.to_dict() for document in self._documents.values()]}
        directory = os.path.dirname(os.path.abspath(self.path))
        descriptor, temporary = tempfile.mkstemp(prefix='.book-', dir=directory)
        try:
            with os.fdopen(descriptor, 'w', encoding='utf-8') as handle:
                json.dump(data, handle, indent=1, sort_keys=True)
                handle.write('\n')
            os.replace(temporary, self.path)
        except BaseException:
            if os.path.exists(temporary):
                os.unlink(temporary)
            raise
