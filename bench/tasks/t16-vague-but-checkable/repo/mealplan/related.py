"""'You might also like': recipes like the one on screen."""
from .ingredients import canonical


def _own(book, recipe):
    return {canonical(name) for name in book.ingredient_names(recipe.id)}


def similar(book, recipe_id, profile=None, limit=3):
    """Up to `limit` ids of other recipes like recipe_id, most alike first.

    Alike means sharing tags first, then sharing ingredients; ties by title. A recipe with no tag in common is never
    offered, nor sauces, which are not meals. Recipes longer than the customer's max_minutes are left out.
    """
    shown = book.get(recipe_id)
    tags = set(shown.tags)
    mine = _own(book, shown)
    ranked = []
    for recipe in book:
        if recipe.id == shown.id or 'sauce' in recipe.tags:
            continue
        if profile is not None and not profile.allows_time(recipe):
            continue
        shared_tags = len(tags & set(recipe.tags))
        if not shared_tags:
            continue
        shared_ingredients = len(mine & _own(book, recipe))
        ranked.append((-shared_tags, -shared_ingredients, recipe.title, recipe.id))
    ranked.sort()
    return [entry[-1] for entry in ranked[:max(limit, 0)]]
