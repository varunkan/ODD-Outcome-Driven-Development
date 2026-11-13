"""Save a ledger to a JSON file and read it back. The format is described in the README."""
import json

from .ledger import Item, Ledger, Movement

FORMAT_VERSION = 1


def dump(ledger):
    """The ledger as plain data, ready for json.dump."""
    return {
        'version': FORMAT_VERSION,
        'items': [
            {
                'sku': sku,
                'name': ledger.item(sku).name,
                'reorder_level': ledger.item(sku).reorder_level,
                'on_hand': ledger.on_hand(sku),
            }
            for sku in ledger.skus()
        ],
        'history': [
            {'kind': movement.kind, 'sku': movement.sku, 'quantity': movement.quantity, 'note': movement.note}
            for movement in ledger.history()
        ],
    }


def load(data):
    """A Ledger rebuilt from data produced by dump()."""
    version = data.get('version')
    if version != FORMAT_VERSION:
        raise ValueError('unsupported file version: %r' % (version,))
    items = [Item(row['sku'], row['name'], row.get('reorder_level', 0)) for row in data['items']]
    on_hand = {row['sku']: row['on_hand'] for row in data['items']}
    history = [Movement(row['kind'], row['sku'], row['quantity'], row.get('note', ''))
               for row in data.get('history', [])]
    return Ledger.restore(items, on_hand, history)


def save(ledger, path):
    """Write the ledger to ``path`` as JSON."""
    with open(path, 'w', encoding='utf-8') as handle:
        json.dump(dump(ledger), handle, indent=2, sort_keys=True)
        handle.write('\n')


def read(path):
    """The ledger stored at ``path``."""
    with open(path, encoding='utf-8') as handle:
        return load(json.load(handle))
