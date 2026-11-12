import unittest

from mealplan import Recipe, RecipeBook, house_book, recipe_card, shopping_list
from mealplan.ingredients import allergen_group, allergens_in, canonical


class IngredientNameTest(unittest.TestCase):
    def test_canonical_names(self):
        self.assertEqual(canonical('  Groundnut   Oil '), 'peanut oil')
        self.assertEqual(canonical('Tomatoes'), 'tomato')
        self.assertEqual(canonical('Peanuts'), 'peanut')
        self.assertEqual(canonical('Lasagne sheets'), 'lasagne sheet')
        self.assertEqual(canonical('scallions'), 'spring onion')
        self.assertEqual(canonical('Saffron'), 'saffron')

    def test_what_an_ingredient_contains(self):
        self.assertEqual(allergens_in('Butter'), {'milk'})
        self.assertEqual(allergens_in('Arachis oil'), {'peanut'})
        self.assertEqual(allergens_in('Soy sauce'), {'soy', 'gluten'})
        self.assertEqual(allergens_in('Coconut milk'), set())
        self.assertEqual(allergens_in('Carrots'), set())

    def test_names_people_use_for_allergens(self):
        self.assertEqual(allergen_group('Dairy'), 'milk')
        self.assertEqual(allergen_group(' groundnuts '), 'peanut')
        self.assertEqual(allergen_group('Wheat'), 'gluten')
        self.assertIsNone(allergen_group('coriander'))


class BookTest(unittest.TestCase):
    def test_house_book(self):
        book = house_book()
        self.assertEqual(len(book), 20)
        self.assertEqual(book.get('chicken-satay').components, ('satay-sauce',))
        self.assertEqual(book.ingredient_names('chicken-satay'), ['Chicken thighs', 'Garlic', 'Lime'])
        self.assertEqual([recipe.id for recipe in book.with_tag('sauce')], ['bechamel', 'satay-sauce'])

    def test_missing_and_circular_components(self):
        with self.assertRaises(ValueError):
            RecipeBook([Recipe('a', 'A', 5, components=['b'])]).check()
        with self.assertRaises(ValueError) as caught:
            RecipeBook([Recipe('a', 'A', 5, components=['b']), Recipe('b', 'B', 5, components=['a'])]).check()
        self.assertIn('a -> b -> a', str(caught.exception))
        with self.assertRaises(ValueError):
            RecipeBook([Recipe('a', 'A', 5), Recipe('a', 'Again', 5)])

    def test_shopping_list_includes_components(self):
        rows = dict(((name, unit), quantity) for name, quantity, unit in
                    shopping_list(house_book(), ['chicken-satay', 'chicken-satay-wrap']))
        self.assertEqual(rows[('peanut butter', 'tbsp')], 8)
        self.assertEqual(rows[('lime', '')], 3)
        self.assertEqual(rows[('chicken breast', '')], 1)
        scaled = dict(((name, unit), quantity) for name, quantity, unit in
                      shopping_list(house_book(), ['party-platter'], servings=3))
        self.assertEqual(scaled[('pitta bread', '')], 2)
        self.assertEqual(scaled[('peanut butter', 'tbsp')], 2)

    def test_recipe_card(self):
        card = recipe_card(house_book(), 'mushroom-risotto')
        self.assertTrue(card.startswith('Mushroom risotto\n35 min, serves 3\n'))
        self.assertIn('- 50 g Parmigiano', card)
        self.assertIn('Contains: milk', card)
        self.assertIn('Uses: Satay sauce', recipe_card(house_book(), 'chicken-satay'))


if __name__ == '__main__':
    unittest.main()
