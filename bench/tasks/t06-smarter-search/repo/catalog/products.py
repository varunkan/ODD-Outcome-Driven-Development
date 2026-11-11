"""Products and the catalog that holds them."""


class Product:
    """One thing we sell. `price` is in whole cents. Tags are kept in lower case."""

    def __init__(self, sku, name, price, tags=()):
        if not isinstance(sku, str) or not sku.strip():
            raise ValueError('a product needs a SKU')
        if not isinstance(name, str) or not name.strip():
            raise ValueError('a product needs a name')
        if isinstance(price, bool) or not isinstance(price, int) or price < 0:
            raise ValueError('price must be a whole number of cents, zero or more')
        self.sku = sku.strip()
        self.name = name.strip()
        self.price = price
        self.tags = tuple(sorted({tag.strip().lower() for tag in tags if tag.strip()}))

    def __eq__(self, other):
        if not isinstance(other, Product):
            return NotImplemented
        return (self.sku, self.name, self.price, self.tags) == (other.sku, other.name, other.price, other.tags)

    def __hash__(self):
        return hash(self.sku)

    def __repr__(self):
        return 'Product(%r, %r, %r, %r)' % (self.sku, self.name, self.price, self.tags)


class Catalog:
    """The products on sale, by SKU. Products are kept in the order they were added."""

    def __init__(self):
        self._products = {}

    def add(self, product):
        if product.sku in self._products:
            raise ValueError('SKU already in the catalog: %s' % product.sku)
        self._products[product.sku] = product
        return product

    def get(self, sku):
        """The product with that SKU; KeyError when there is none."""
        return self._products[sku]

    def remove(self, sku):
        """Take a product out and return it; KeyError when there is none."""
        return self._products.pop(sku)

    def products(self):
        """Every product, in the order they were added."""
        return list(self._products.values())

    def __contains__(self, sku):
        return sku in self._products

    def __iter__(self):
        return iter(self.products())

    def __len__(self):
        return len(self._products)
