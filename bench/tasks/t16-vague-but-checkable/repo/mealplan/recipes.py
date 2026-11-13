"""Recipes and the recipe book.

A recipe lists its own ingredients and, separately, its components: other recipes it uses whole. The chicken satay
skewers use the satay sauce; the party platter uses the skewers. A component can have components of its own.
"""


class Recipe:
    """One recipe. ingredients is a list of (name, quantity, unit); components is a list of recipe ids."""

    def __init__(self, id, title, minutes, tags=(), ingredients=(), components=(), serves=2):
        if not id or not str(id).strip():
            raise ValueError('a recipe needs an id')
        if not str(title).strip():
            raise ValueError('recipe %s needs a title' % id)
        if not isinstance(minutes, int) or minutes <= 0:
            raise ValueError('recipe %s: minutes must be a whole number above 0' % id)
        self.id = str(id).strip()
        self.title = str(title).strip()
        self.minutes = minutes
        self.tags = tuple(str(tag).strip().lower() for tag in tags)
        self.ingredients = tuple((str(name).strip(), quantity, unit) for name, quantity, unit in ingredients)
        self.components = tuple(components)
        self.serves = serves

    def __repr__(self):
        return 'Recipe(%r)' % self.id


class RecipeBook:
    """Recipes by id.

    memo is a scratch dictionary for work worked out from the recipes (search indexes and the like); it is emptied
    whenever a recipe is added.
    """

    def __init__(self, recipes=()):
        self._recipes = {}
        self.memo = {}
        for recipe in recipes:
            self.add(recipe)

    def add(self, recipe):
        if recipe.id in self._recipes:
            raise ValueError('there is already a recipe %s' % recipe.id)
        self._recipes[recipe.id] = recipe
        self.memo.clear()

    def get(self, recipe_id):
        try:
            return self._recipes[recipe_id]
        except KeyError:
            raise KeyError('no recipe %s' % (recipe_id,)) from None

    def __contains__(self, recipe_id):
        return recipe_id in self._recipes

    def __iter__(self):
        return iter([self._recipes[key] for key in sorted(self._recipes)])

    def __len__(self):
        return len(self._recipes)

    def with_tag(self, tag):
        tag = tag.strip().lower()
        return [recipe for recipe in self if tag in recipe.tags]

    def ingredient_names(self, recipe_id):
        """The names of the recipe's own ingredients, as written in the recipe (components are not looked into)."""
        return [name for name, _, _ in self.get(recipe_id).ingredients]

    def check(self):
        """Raise ValueError when a component is missing or a recipe uses itself, directly or through others."""
        for recipe in self:
            for component in recipe.components:
                if component not in self._recipes:
                    raise ValueError('recipe %s uses %s, which is not in the book' % (recipe.id, component))
        state = {}

        def visit(recipe_id, path):
            if state.get(recipe_id) == 'done':
                return
            if state.get(recipe_id) == 'busy':
                raise ValueError('recipes use each other in a circle: %s' % ' -> '.join(path + [recipe_id]))
            state[recipe_id] = 'busy'
            for component in self._recipes[recipe_id].components:
                visit(component, path + [recipe_id])
            state[recipe_id] = 'done'

        for recipe_id in sorted(self._recipes):
            visit(recipe_id, [])
