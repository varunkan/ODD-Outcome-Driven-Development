"""The house recipe book: the recipes the app ships with. Quantities are for the stated number of servings."""
from .recipes import Recipe, RecipeBook


def _r(id, title, minutes, tags, ingredients, components=(), serves=2):
    return Recipe(id, title, minutes, tags=tags, ingredients=ingredients, components=components, serves=serves)


HOUSE = (
    _r('satay-sauce', 'Satay sauce', 10, ['sauce'],
       [('Peanut butter', 4, 'tbsp'), ('Soy sauce', 1, 'tbsp'), ('Lime', 1, ''), ('Garlic', 1, 'clove')]),
    _r('chicken-satay', 'Chicken satay skewers', 30, ['dinner', 'grill', 'chicken'],
       [('Chicken thighs', 4, ''), ('Garlic', 2, 'cloves'), ('Lime', 1, '')], ['satay-sauce']),
    _r('houmous', 'Houmous', 10, ['dip', 'vegan'],
       [('Chickpeas', 400, 'g'), ('Tahini', 2, 'tbsp'), ('Lemon', 1, ''), ('Garlic', 1, 'clove'),
        ('Olive oil', 3, 'tbsp')]),
    _r('party-platter', 'Party platter', 45, ['dinner', 'sharing'],
       [('Carrots', 2, ''), ('Cucumber', 1, ''), ('Pitta bread', 4, '')], ['chicken-satay', 'houmous'], serves=6),
    _r('chicken-curry', 'Chicken curry', 40, ['dinner', 'chicken', 'spicy'],
       [('Chicken thighs', 6, ''), ('Onion', 1, ''), ('Garlic', 3, 'cloves'), ('Ginger', 20, 'g'),
        ('Tomatoes', 400, 'g'), ('Coconut milk', 400, 'ml'), ('Groundnut oil', 2, 'tbsp')], serves=4),
    _r('chicken-noodles', 'Chicken noodle stir-fry', 20, ['dinner', 'chicken', 'quick'],
       [('Chicken breast', 2, ''), ('Egg noodles', 200, 'g'), ('Soy sauce', 2, 'tbsp'), ('Spring onions', 4, ''),
        ('Sesame oil', 1, 'tbsp')]),
    _r('veg-noodle-soup', 'Vegetable noodle soup', 25, ['dinner', 'vegan', 'soup', 'quick'],
       [('Rice noodles', 150, 'g'), ('Carrot', 1, ''), ('Pak choi', 2, ''), ('Vegetable stock', 800, 'ml'),
        ('Scallions', 3, '')]),
    _r('mushroom-risotto', 'Mushroom risotto', 35, ['dinner', 'vegetarian'],
       [('Arborio rice', 300, 'g'), ('Mushrooms', 250, 'g'), ('Onion', 1, ''), ('Vegetable stock', 1, 'l'),
        ('Parmigiano', 50, 'g'), ('Butter', 30, 'g')], serves=3),
    _r('bechamel', 'Bechamel sauce', 15, ['sauce'],
       [('Whole milk', 500, 'ml'), ('Butter', 40, 'g'), ('Plain flour', 40, 'g'), ('Nutmeg', 1, 'pinch')]),
    _r('beef-lasagne', 'Beef lasagne', 75, ['dinner', 'beef', 'baked'],
       [('Beef mince', 500, 'g'), ('Onion', 1, ''), ('Tomatoes', 800, 'g'), ('Lasagne sheets', 9, '')],
       ['bechamel'], serves=4),
    _r('veg-lasagne', 'Vegetable lasagne', 70, ['dinner', 'vegetarian', 'baked'],
       [('Aubergine', 1, ''), ('Courgettes', 2, ''), ('Tomatoes', 800, 'g'), ('Lasagne sheets', 9, '')],
       ['bechamel'], serves=4),
    _r('tomato-pasta', 'Tomato and basil pasta', 20, ['dinner', 'vegetarian', 'quick'],
       [('Pasta', 200, 'g'), ('Tomatoes', 400, 'g'), ('Basil', 1, 'bunch'), ('Garlic', 2, 'cloves'),
        ('Olive oil', 2, 'tbsp')]),
    _r('prawn-pad-thai', 'Prawn pad thai', 25, ['dinner', 'seafood', 'quick'],
       [('Rice noodles', 200, 'g'), ('Prawns', 200, 'g'), ('Egg', 2, ''), ('Fish sauce', 2, 'tbsp'),
        ('Peanuts', 40, 'g'), ('Lime', 1, ''), ('Spring onions', 3, '')]),
    _r('tofu-pad-thai', 'Tofu pad thai', 25, ['dinner', 'vegan', 'quick'],
       [('Rice noodles', 200, 'g'), ('Tofu', 280, 'g'), ('Tamari', 2, 'tbsp'), ('Lime', 1, ''),
        ('Spring onions', 3, ''), ('Chilli', 1, '')]),
    _r('salmon-traybake', 'Salmon traybake', 30, ['dinner', 'fish'],
       [('Salmon', 2, 'fillets'), ('Potatoes', 500, 'g'), ('Lemon', 1, ''), ('Olive oil', 2, 'tbsp'),
        ('Dill', 1, 'bunch')]),
    _r('chickpea-curry', 'Chickpea curry', 30, ['dinner', 'vegan', 'spicy'],
       [('Chickpeas', 800, 'g'), ('Onion', 1, ''), ('Garlic', 3, 'cloves'), ('Ginger', 20, 'g'),
        ('Tomatoes', 400, 'g'), ('Coconut milk', 400, 'ml'), ('Spinach', 100, 'g')], serves=4),
    _r('cheese-toastie', 'Cheese toastie', 10, ['lunch', 'quick', 'vegetarian'],
       [('Bread', 2, 'slices'), ('Cheddar', 60, 'g'), ('Butter', 10, 'g')], serves=1),
    _r('chicken-satay-wrap', 'Chicken satay wrap', 15, ['lunch', 'chicken', 'quick'],
       [('Tortilla', 2, ''), ('Chicken breast', 1, ''), ('Lettuce', 1, 'handful')], ['satay-sauce']),
    _r('roast-chicken', 'Sunday roast chicken', 110, ['dinner', 'chicken', 'roast'],
       [('Chicken', 1, ''), ('Potatoes', 1, 'kg'), ('Carrots', 4, ''), ('Gravy granules', 4, 'tsp')], serves=4),
    _r('chilli-chicken-tacos', 'Chilli chicken tacos', 25, ['dinner', 'chicken', 'spicy', 'quick'],
       [('Chicken thighs', 4, ''), ('Chilli', 1, ''), ('Tortilla', 6, ''), ('Lime', 1, ''), ('Cilantro', 1, 'bunch')],
       serves=3),
)


def house_book():
    """A fresh RecipeBook holding the house recipes."""
    book = RecipeBook(HOUSE)
    book.check()
    return book
