"""The stock ledger: how many units of each item are on hand, and the movements that got them there."""
from collections import namedtuple

from .errors import InsufficientStock, UnknownSku

Item = namedtuple('Item', 'sku name reorder_level')
Movement = namedtuple('Movement', 'kind sku quantity note')


def whole_positive(quantity):
    """Return ``quantity`` when it is a positive whole number; raise ValueError otherwise."""
    if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity <= 0:
        raise ValueError('quantity must be a positive whole number, got %r' % (quantity,))
    return quantity


class Ledger:
    """Items, their stock on hand and the history of movements."""

    def __init__(self):
        self._items = {}
        self._on_hand = {}
        self._history = []

    @classmethod
    def restore(cls, items, on_hand, history=()):
        """Rebuild a ledger from saved state, without replaying the movements.

        ``items`` are Item tuples, ``on_hand`` maps SKU to units, ``history`` is a sequence of Movement tuples.
        """
        ledger = cls()
        for item in items:
            ledger._items[item.sku] = item
            ledger._on_hand[item.sku] = on_hand.get(item.sku, 0)
        ledger._history = list(history)
        return ledger

    def add_item(self, sku, name, reorder_level=0):
        """Register an item. It starts with nothing on hand."""
        if sku in self._items:
            raise ValueError('item %s already exists' % (sku,))
        if isinstance(reorder_level, bool) or not isinstance(reorder_level, int) or reorder_level < 0:
            raise ValueError('reorder level must be a whole number, zero or more')
        self._items[sku] = Item(sku, name, reorder_level)
        self._on_hand[sku] = 0
        return self._items[sku]

    def item(self, sku):
        """The Item registered under this SKU."""
        try:
            return self._items[sku]
        except KeyError:
            raise UnknownSku(sku) from None

    def skus(self):
        """Every registered SKU, sorted."""
        return sorted(self._items)

    def on_hand(self, sku):
        """Units physically in stock."""
        self.item(sku)
        return self._on_hand[sku]

    def receive(self, sku, quantity, note=''):
        """Book goods in."""
        self.item(sku)
        whole_positive(quantity)
        self._on_hand[sku] += quantity
        self._record('receive', sku, quantity, note)

    def ship(self, sku, quantity, note=''):
        """Book goods out. Refused when there is not enough stock."""
        self.item(sku)
        whole_positive(quantity)
        if quantity > self._on_hand[sku]:
            raise InsufficientStock(sku, quantity, self._on_hand[sku])
        self._on_hand[sku] -= quantity
        self._record('ship', sku, quantity, note)

    def adjust(self, sku, counted, note=''):
        """Set the stock to a counted figure. Returns the difference, positive when stock was found."""
        self.item(sku)
        if isinstance(counted, bool) or not isinstance(counted, int) or counted < 0:
            raise ValueError('a stock count must be a whole number, zero or more')
        difference = counted - self._on_hand[sku]
        if difference:
            self._on_hand[sku] = counted
            self._record('adjust', sku, difference, note)
        return difference

    def history(self, sku=None):
        """Movements in the order they were booked, for one SKU or for all."""
        if sku is None:
            return list(self._history)
        self.item(sku)
        return [movement for movement in self._history if movement.sku == sku]

    def _record(self, kind, sku, quantity, note):
        self._history.append(Movement(kind, sku, quantity, note))
