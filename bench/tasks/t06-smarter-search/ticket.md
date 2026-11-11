# Make product search smarter

The search box in the stock tool is driving the shop floor mad. Someone types `usb` and gets nothing, because the
product was entered as "USB Hub". When they do get results, the list is in whatever order the products happened to be
entered, so they scroll up and down hunting for the one they want. I keep hearing "why is search so dumb?".

Please make `catalog.search.search(catalog, query)` smarter.

Two things we are sure about:

1. Upper and lower case must not matter. `usb`, `USB` and `Usb` all find "USB Hub", and they find "usb cable" as
   well.
2. The results come back ordered by product name, A to Z. People read down the list alphabetically, so please do not
   reorder it by "relevance" or anything clever.

Beyond that we have not thought it through. Use your judgement about what else would make search feel smarter for
the people using it.

It should stay what it is today: a function that takes the catalog and the text that was typed, and returns a list
of `Product` objects.

```python
from catalog.products import Catalog, Product
from catalog.search import search

catalog = Catalog()
catalog.add(Product(sku="L-2", name="Floor Lamp", price=4500))
catalog.add(Product(sku="K-1", name="Kettle", price=2500))
catalog.add(Product(sku="L-1", name="Desk Lamp", price=1999))

[product.name for product in search(catalog, "lamp")]    # ["Desk Lamp", "Floor Lamp"]
```
