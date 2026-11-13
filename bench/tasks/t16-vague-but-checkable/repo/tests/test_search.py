import unittest

from mealplan import Profile, house_book, plan_week, search, similar, suggest


class SearchTest(unittest.TestCase):
    def test_best_match_first(self):
        book = house_book()
        self.assertEqual(search(book, 'pad thai'), ['prawn-pad-thai', 'tofu-pad-thai'])
        self.assertEqual(search(book, 'Curry'), ['chickpea-curry', 'chicken-curry'])
        self.assertEqual(search(book, 'lasagne')[0], 'veg-lasagne')
        self.assertEqual(search(book, '  '), [])

    def test_time_limit_and_dislikes(self):
        book = house_book()
        self.assertEqual(search(book, 'chicken', Profile(max_minutes=25)),
                         ['chicken-satay-wrap', 'chicken-noodles', 'chilli-chicken-tacos'])
        self.assertEqual(search(book, 'pad thai', Profile(dislikes=['prawns'])), ['tofu-pad-thai', 'prawn-pad-thai'])


class SuggestTest(unittest.TestCase):
    def test_titles_for_what_was_typed(self):
        book = house_book()
        self.assertEqual(suggest(book, 'sa'), ['Salmon traybake', 'Satay sauce', 'Bechamel sauce',
                                               'Chicken satay skewers', 'Chicken satay wrap'])
        self.assertEqual(suggest(book, 'Pa', limit=2), ['Party platter', 'Prawn pad thai'])
        self.assertEqual(suggest(book, 'v', Profile(max_minutes=30)), ['Vegetable noodle soup'])
        self.assertEqual(suggest(book, 'v'), ['Vegetable lasagne', 'Vegetable noodle soup'])
        self.assertEqual(suggest(book, ''), [])


class PlanTest(unittest.TestCase):
    def test_a_week_of_dinners(self):
        book = house_book()
        self.assertEqual(plan_week(book), ['chicken-noodles', 'tomato-pasta', 'chilli-chicken-tacos', 'prawn-pad-thai',
                                           'tofu-pad-thai', 'veg-noodle-soup', 'chicken-satay'])
        self.assertEqual(plan_week(book, week=1)[0], 'chickpea-curry')
        self.assertEqual(plan_week(book, Profile(max_minutes=20), days=3),
                         ['chicken-noodles', 'tomato-pasta', 'chicken-noodles'])
        self.assertEqual(plan_week(book, days=0), [])
        with self.assertRaises(ValueError):
            plan_week(book, Profile(max_minutes=5))

    def test_allergens_typed_as_an_ingredient_name(self):
        plan = plan_week(house_book(), Profile(allergens=['peanuts']), days=14)
        self.assertNotIn('prawn-pad-thai', plan)
        self.assertEqual(len(plan), 14)


class SimilarTest(unittest.TestCase):
    def test_recipes_like_this_one(self):
        book = house_book()
        self.assertEqual(similar(book, 'veg-lasagne'), ['beef-lasagne', 'tomato-pasta', 'mushroom-risotto'])
        self.assertEqual(similar(book, 'chicken-curry', limit=1), ['chilli-chicken-tacos'])
        self.assertNotIn('satay-sauce', similar(book, 'chicken-satay', limit=20))
        self.assertEqual(similar(book, 'chicken-curry', Profile(max_minutes=25)),
                         ['chilli-chicken-tacos', 'chicken-noodles', 'tomato-pasta'])


if __name__ == '__main__':
    unittest.main()
