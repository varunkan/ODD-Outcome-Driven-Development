"""The shopping list for a set of recipes."""
from .ingredients import canonical


def _expand(book, recipe_id, scale, into, path):
    if recipe_id in path:
        raise ValueError('recipes use each other in a circle: %s' % ' -> '.join(path + (recipe_id,)))
    recipe = book.get(recipe_id)
    for name, quantity, unit in recipe.ingredients:
        key = (canonical(name), unit)
        into[key] = into.get(key, 0) + quantity * scale
    for component in recipe.components:
        _expand(book, component, scale, into, path + (recipe_id,))


def shopping_list(book, recipe_ids, servings=None):
    """[(ingredient, quantity, unit)] for all of recipe_ids together, components included, sorted by ingredient.

    The same ingredient in the same unit is added up. With servings, every recipe is scaled to that many servings
    (components are scaled with the recipe that uses them).
    """
    totals = {}
    for recipe_id in recipe_ids:
        recipe = book.get(recipe_id)
        scale = 1 if servings is None else servings / recipe.serves
        _expand(book, recipe_id, scale, totals, ())
    rows = []
    for (name, unit), quantity in totals.items():
        if isinstance(quantity, float) and quantity.is_integer():
            quantity = int(quantity)
        elif isinstance(quantity, float):
            quantity = round(quantity, 2)
        rows.append((name, quantity, unit))
    rows.sort(key=lambda row: (row[0], row[2]))
    return rows
