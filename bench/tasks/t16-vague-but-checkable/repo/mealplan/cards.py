"""The recipe card shown when a customer opens a recipe."""
from .ingredients import allergens_in


def _amount(quantity, unit):
    if not unit:
        return '%g' % quantity
    return '%g %s' % (quantity, unit)


def recipe_card(book, recipe_id):
    """The card as text: title, time, servings, ingredients, what it uses, and the allergens in its own
    ingredients."""
    recipe = book.get(recipe_id)
    lines = [recipe.title, '%d min, serves %d' % (recipe.minutes, recipe.serves), '']
    for name, quantity, unit in recipe.ingredients:
        lines.append('- %s %s' % (_amount(quantity, unit), name))
    if recipe.components:
        lines.append('')
        lines.append('Uses: ' + ', '.join(book.get(component).title for component in recipe.components))
    found = set()
    for name, _, _ in recipe.ingredients:
        found |= allergens_in(name)
    if found:
        lines.append('')
        lines.append('Contains: ' + ', '.join(sorted(found)))
    return '\n'.join(lines) + '\n'
