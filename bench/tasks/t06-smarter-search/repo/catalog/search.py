"""Finding products in a catalog."""


def search(catalog, query):
    """Products whose name contains `query`, in the order they were added. A blank query finds nothing."""
    query = query.strip()
    if not query:
        return []
    return [product for product in catalog.products() if query in product.name]


def by_tag(catalog, tag):
    """Products carrying `tag`, in the order they were added."""
    tag = tag.strip().lower()
    return [product for product in catalog.products() if tag in product.tags]


def in_price_range(catalog, low, high):
    """Products priced from `low` to `high` cents, both included, cheapest first."""
    if low > high:
        raise ValueError('low must not be more than high')
    found = [product for product in catalog.products() if low <= product.price <= high]
    return sorted(found, key=lambda product: (product.price, product.sku))


def tags_in_use(catalog):
    """Every tag carried by at least one product, with the number of products carrying it."""
    counts = {}
    for product in catalog.products():
        for tag in product.tags:
            counts[tag] = counts.get(tag, 0) + 1
    return counts
