"""Errors raised by the inventory package."""


class InventoryError(Exception):
    """Base class for every error this package raises on purpose."""


class UnknownSku(InventoryError):
    """The ledger has no item with this SKU."""

    def __init__(self, sku):
        self.sku = sku
        super().__init__('unknown SKU: %s' % (sku,))


class InsufficientStock(InventoryError):
    """More units were asked for than can be taken."""

    def __init__(self, sku, requested, available):
        self.sku = sku
        self.requested = requested
        self.available = available
        super().__init__('cannot take %s of %s: only %s can be taken' % (requested, sku, available))
