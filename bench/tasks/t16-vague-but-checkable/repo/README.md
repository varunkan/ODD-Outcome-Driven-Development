# mealplan

The recipe side of our meal planning app: the house recipe book, the search box and its suggestions, "you might
also like", the weekly dinner plan and the shopping list. Python 3 standard library only.

```python
from mealplan import Profile, house_book, plan_week, search, similar, suggest

book = house_book()
me = Profile(name='Sam', dislikes=['coriander'], max_minutes=45)

search(book, 'curry', me)        # ['chickpea-curry', 'chicken-curry']
suggest(book, 'chi', me)         # up to 5 titles for what has been typed
similar(book, 'chicken-curry')   # ['chilli-chicken-tacos', 'chickpea-curry', 'chicken-satay']
plan_week(book, me)              # seven dinner ids
```

## What is in it

- `mealplan/recipes.py`: `Recipe` (own ingredients, plus components: other recipes used whole) and `RecipeBook`.
- `mealplan/house.py`: the recipes the app ships with.
- `mealplan/ingredients.py`: ingredient names (`canonical`), what each ingredient contains (`allergens_in`), and
  the names people use for each allergen (`allergen_group`).
- `mealplan/profiles.py`: `Profile`: allergens, dislikes and a time limit, as the customer typed them.
- `mealplan/search.py`: `search(book, text, profile=None)` and `suggest(book, prefix, profile=None, limit=5)`.
- `mealplan/related.py`: `similar(book, recipe_id, profile=None, limit=3)`.
- `mealplan/planner.py`: `plan_week(book, profile=None, days=7, week=0)`.
- `mealplan/shopping.py` and `mealplan/cards.py`: the shopping list and the recipe card.

## Tests

```
python3 -m unittest discover -s tests
```
