"""Acceptance tests for the allergen rule, and for "everything else stays as it is".

Only what the ticket states is checked, through the four functions it names (search, suggest, plan_week, similar)
and Profile. The wishes it leaves open (tidying up, telling people that recipes were left out) are not checked.

The baselines below are what the shipped code returns for a customer with no allergens. The unsafe sets were worked
out by hand from mealplan/house.py and mealplan/ingredients.py:
  peanut:  satay-sauce (peanut butter); chicken-satay and chicken-satay-wrap (use satay-sauce); party-platter (uses
           chicken-satay, which uses satay-sauce: depth two); chicken-curry (groundnut oil, an alias of peanut oil);
           prawn-pad-thai (peanuts).
  milk:    bechamel (whole milk, butter); beef-lasagne, veg-lasagne (use bechamel); mushroom-risotto (parmigiano,
           an alias of parmesan; butter); cheese-toastie (cheddar, butter). Coconut milk is not milk.
  gluten:  'wheat' names it. Soy sauce, flour, pasta, bread, pitta, tortilla, egg noodles, lasagne sheets, gravy
           granules, and everything that uses satay-sauce or bechamel.
  sesame:  houmous (tahini), party-platter (uses houmous), chicken-noodles (sesame oil).
"""
import unittest

from mealplan import Profile, house_book, plan_week, search, similar, suggest

SEARCH = {
    'chicken': ['chicken-satay-wrap', 'chicken-noodles', 'chilli-chicken-tacos', 'chicken-satay', 'chicken-curry',
                'roast-chicken'],
    'pad thai': ['prawn-pad-thai', 'tofu-pad-thai'],
    'curry': ['chickpea-curry', 'chicken-curry'],
    'quick': ['cheese-toastie', 'chicken-satay-wrap', 'chicken-noodles', 'tomato-pasta', 'chilli-chicken-tacos',
              'prawn-pad-thai', 'tofu-pad-thai', 'veg-noodle-soup'],
    'lasagne': ['veg-lasagne', 'beef-lasagne'],
    'platter': ['party-platter'],
    'satay': ['satay-sauce', 'chicken-satay-wrap', 'chicken-satay'],
    'sauce': ['satay-sauce', 'bechamel', 'chicken-noodles', 'prawn-pad-thai'],
    'vegetarian': ['cheese-toastie', 'tomato-pasta', 'mushroom-risotto', 'veg-lasagne'],
    'dinner': ['chicken-noodles', 'tomato-pasta', 'chilli-chicken-tacos', 'prawn-pad-thai', 'tofu-pad-thai',
               'veg-noodle-soup', 'chicken-satay', 'chickpea-curry', 'salmon-traybake', 'mushroom-risotto',
               'chicken-curry', 'party-platter', 'veg-lasagne', 'beef-lasagne', 'roast-chicken'],
    'spicy': ['chilli-chicken-tacos', 'chickpea-curry', 'chicken-curry'],
}

# Every title that matches, in order (what suggest gives with a large limit).
SUGGEST = {
    'c': ['Cheese toastie', 'Chicken curry', 'Chicken noodle stir-fry', 'Chicken satay skewers', 'Chicken satay wrap',
          'Chickpea curry', 'Chilli chicken tacos', 'Sunday roast chicken'],
    'chi': ['Chicken curry', 'Chicken noodle stir-fry', 'Chicken satay skewers', 'Chicken satay wrap', 'Chickpea curry',
            'Chilli chicken tacos', 'Sunday roast chicken'],
    'sa': ['Salmon traybake', 'Satay sauce', 'Bechamel sauce', 'Chicken satay skewers', 'Chicken satay wrap'],
    'pa': ['Party platter', 'Prawn pad thai', 'Tofu pad thai', 'Tomato and basil pasta'],
    't': ['Tofu pad thai', 'Tomato and basil pasta', 'Cheese toastie', 'Chilli chicken tacos', 'Prawn pad thai',
          'Salmon traybake'],
    'v': ['Vegetable lasagne', 'Vegetable noodle soup'],
    's': ['Salmon traybake', 'Satay sauce', 'Sunday roast chicken', 'Bechamel sauce', 'Chicken noodle stir-fry',
          'Chicken satay skewers', 'Chicken satay wrap', 'Vegetable noodle soup'],
}

# Every recipe offered as similar, in order (what similar gives with a large limit).
SIMILAR = {
    'chicken-noodles': ['chilli-chicken-tacos', 'chicken-satay-wrap', 'prawn-pad-thai', 'tofu-pad-thai',
                        'veg-noodle-soup', 'chicken-curry', 'chicken-satay', 'roast-chicken', 'tomato-pasta',
                        'beef-lasagne', 'cheese-toastie', 'chickpea-curry', 'mushroom-risotto', 'party-platter',
                        'salmon-traybake', 'veg-lasagne'],
    'chicken-curry': ['chilli-chicken-tacos', 'chickpea-curry', 'chicken-satay', 'chicken-noodles', 'roast-chicken',
                      'beef-lasagne', 'tomato-pasta', 'mushroom-risotto', 'veg-lasagne', 'chicken-satay-wrap',
                      'party-platter', 'prawn-pad-thai', 'salmon-traybake', 'tofu-pad-thai', 'veg-noodle-soup'],
    'tofu-pad-thai': ['veg-noodle-soup', 'prawn-pad-thai', 'chilli-chicken-tacos', 'chicken-noodles', 'chickpea-curry',
                      'tomato-pasta', 'chicken-satay', 'beef-lasagne', 'cheese-toastie', 'chicken-curry',
                      'chicken-satay-wrap', 'houmous', 'mushroom-risotto', 'party-platter', 'salmon-traybake',
                      'roast-chicken', 'veg-lasagne'],
    'veg-lasagne': ['beef-lasagne', 'tomato-pasta', 'mushroom-risotto', 'chicken-curry', 'chickpea-curry',
                    'cheese-toastie', 'chicken-noodles', 'chicken-satay', 'chilli-chicken-tacos', 'party-platter',
                    'prawn-pad-thai', 'salmon-traybake', 'roast-chicken', 'tofu-pad-thai', 'veg-noodle-soup'],
    'roast-chicken': ['chicken-curry', 'chicken-noodles', 'chicken-satay', 'chilli-chicken-tacos', 'party-platter',
                      'salmon-traybake', 'veg-noodle-soup', 'beef-lasagne', 'chicken-satay-wrap', 'chickpea-curry',
                      'mushroom-risotto', 'prawn-pad-thai', 'tofu-pad-thai', 'tomato-pasta', 'veg-lasagne'],
}

# The dinners the plan goes round today, quickest first, then by id.
DINNERS = ['chicken-noodles', 'tomato-pasta', 'chilli-chicken-tacos', 'prawn-pad-thai', 'tofu-pad-thai',
           'veg-noodle-soup', 'chicken-satay', 'chickpea-curry', 'salmon-traybake', 'mushroom-risotto', 'chicken-curry',
           'party-platter', 'veg-lasagne', 'beef-lasagne', 'roast-chicken']

UNSAFE = {
    'peanut': {'satay-sauce', 'chicken-satay', 'chicken-satay-wrap', 'party-platter', 'chicken-curry',
               'prawn-pad-thai'},
    'milk': {'bechamel', 'beef-lasagne', 'veg-lasagne', 'mushroom-risotto', 'cheese-toastie'},
    'gluten': {'satay-sauce', 'chicken-satay', 'chicken-satay-wrap', 'party-platter', 'chicken-noodles', 'bechamel',
               'beef-lasagne', 'veg-lasagne', 'tomato-pasta', 'cheese-toastie', 'roast-chicken',
               'chilli-chicken-tacos'},
    'sesame': {'houmous', 'party-platter', 'chicken-noodles'},
}

TITLES = {recipe.title: recipe.id for recipe in house_book()}

# (allergens as the customer typed them, what must be left out)
CUSTOMERS = [
    (['Peanuts'], UNSAFE['peanut']),
    (['groundnut'], UNSAFE['peanut']),
    ([' PEANUT '], UNSAFE['peanut']),
    (['Dairy'], UNSAFE['milk']),
    (['milk'], UNSAFE['milk']),
    (['Wheat'], UNSAFE['gluten']),
    (['sesame'], UNSAFE['sesame']),
    (['Peanuts', 'Dairy'], UNSAFE['peanut'] | UNSAFE['milk']),
]


def without(ids, unsafe):
    return [recipe_id for recipe_id in ids if recipe_id not in unsafe]


def titles_without(titles, unsafe):
    return [title for title in titles if TITLES[title] not in unsafe]


def rotation(dinners, days, week):
    return [dinners[(week * days + day) % len(dinners)] for day in range(days)]


class ReportedCaseTest(unittest.TestCase):
    def test_the_customer_with_peanuts_in_her_profile(self):
        book = house_book()
        her = Profile(name='Mia', allergens=['Peanuts'])
        offered = suggest(book, 'chi', her)
        self.assertNotIn('Chicken satay skewers', offered)
        self.assertNotIn('Chicken curry', offered)
        plan = plan_week(book, her)
        self.assertEqual(len(plan), 7)
        self.assertNotIn('chicken-satay', plan)
        self.assertNotIn('party-platter', plan_week(book, her, week=1))


class SearchTest(unittest.TestCase):
    def test_unsafe_recipes_are_left_out_and_the_rest_keep_their_order(self):
        book = house_book()
        for allergens, unsafe in CUSTOMERS:
            for text, ids in SEARCH.items():
                with self.subTest(allergens=allergens, text=text):
                    self.assertEqual(search(book, text, Profile(allergens=allergens)), without(ids, unsafe))

    def test_with_a_time_limit_and_dislikes_as_well(self):
        book = house_book()
        self.assertEqual(search(book, 'chicken', Profile(allergens=['Peanuts'], max_minutes=25)),
                         ['chicken-noodles', 'chilli-chicken-tacos'])
        self.assertEqual(search(book, 'pad thai', Profile(allergens=['sesame'], dislikes=['prawns'])),
                         ['tofu-pad-thai', 'prawn-pad-thai'])
        self.assertEqual(search(book, 'pad thai', Profile(allergens=['Peanuts'], dislikes=['prawns'])),
                         ['tofu-pad-thai'])


class SuggestTest(unittest.TestCase):
    def test_unsafe_titles_are_left_out_and_the_limit_is_still_filled(self):
        book = house_book()
        for allergens, unsafe in CUSTOMERS:
            for prefix, titles in SUGGEST.items():
                safe = titles_without(titles, unsafe)
                with self.subTest(allergens=allergens, prefix=prefix):
                    self.assertEqual(suggest(book, prefix, Profile(allergens=allergens)), safe[:5])
                    self.assertEqual(suggest(book, prefix, Profile(allergens=allergens), limit=2), safe[:2])
                    self.assertEqual(suggest(book, prefix, Profile(allergens=allergens), limit=50), safe)

    def test_one_customer_never_gets_another_customers_suggestions(self):
        book = house_book()
        nut = Profile(allergens=['Peanuts'])
        dairy = Profile(allergens=['Dairy'])
        everyone = SUGGEST['c'][:5]
        self.assertEqual(suggest(book, 'c', nut), titles_without(SUGGEST['c'], UNSAFE['peanut'])[:5])
        self.assertEqual(suggest(book, 'c'), everyone)
        self.assertEqual(suggest(book, 'c', Profile()), everyone)
        self.assertEqual(suggest(book, 'c', dairy), titles_without(SUGGEST['c'], UNSAFE['milk'])[:5])
        self.assertEqual(suggest(book, 'c', nut), titles_without(SUGGEST['c'], UNSAFE['peanut'])[:5])

        book = house_book()
        self.assertEqual(suggest(book, 'chi'), SUGGEST['chi'][:5])
        self.assertEqual(suggest(book, 'chi', nut), titles_without(SUGGEST['chi'], UNSAFE['peanut'])[:5])
        self.assertEqual(suggest(book, 'chi', Profile(name='someone else')), SUGGEST['chi'][:5])


class SimilarTest(unittest.TestCase):
    def test_unsafe_recipes_are_left_out_and_the_limit_is_still_filled(self):
        book = house_book()
        for allergens, unsafe in CUSTOMERS:
            for recipe_id, ids in SIMILAR.items():
                safe = without(ids, unsafe)
                with self.subTest(allergens=allergens, recipe=recipe_id):
                    self.assertEqual(similar(book, recipe_id, Profile(allergens=allergens)), safe[:3])
                    self.assertEqual(similar(book, recipe_id, Profile(allergens=allergens), limit=50), safe)


class PlanTest(unittest.TestCase):
    def test_every_day_has_a_safe_dinner_chosen_as_today(self):
        book = house_book()
        for allergens, unsafe in CUSTOMERS:
            dinners = without(DINNERS, unsafe)
            for days, week in ((7, 0), (7, 1), (10, 0), (10, 2), (3, 5)):
                with self.subTest(allergens=allergens, days=days, week=week):
                    self.assertEqual(plan_week(book, Profile(allergens=allergens), days=days, week=week),
                                     rotation(dinners, days, week))

    def test_with_a_time_limit_as_well(self):
        book = house_book()
        self.assertEqual(plan_week(book, Profile(allergens=['Wheat'], max_minutes=25), days=4),
                         ['prawn-pad-thai', 'tofu-pad-thai', 'veg-noodle-soup', 'prawn-pad-thai'])


class NoAllergensTest(unittest.TestCase):
    def test_a_customer_with_no_allergens_sees_what_they_see_today(self):
        book = house_book()
        for profile in (None, Profile(), Profile(name='Sam', allergens=[])):
            for text, ids in SEARCH.items():
                with self.subTest(profile=profile, text=text):
                    self.assertEqual(search(book, text, profile), ids)
            for prefix, titles in SUGGEST.items():
                with self.subTest(profile=profile, prefix=prefix):
                    self.assertEqual(suggest(book, prefix, profile), titles[:5])
                    self.assertEqual(suggest(book, prefix, profile, limit=50), titles)
            for recipe_id, ids in SIMILAR.items():
                with self.subTest(profile=profile, recipe=recipe_id):
                    self.assertEqual(similar(book, recipe_id, profile), ids[:3])
            for days, week in ((7, 0), (7, 1), (10, 2)):
                with self.subTest(profile=profile, days=days, week=week):
                    self.assertEqual(plan_week(book, profile, days=days, week=week), rotation(DINNERS, days, week))

    def test_time_limits_and_dislikes_work_as_today(self):
        book = house_book()
        self.assertEqual(search(book, 'chicken', Profile(max_minutes=25)),
                         ['chicken-satay-wrap', 'chicken-noodles', 'chilli-chicken-tacos'])
        self.assertEqual(search(book, 'pad thai', Profile(dislikes=['prawns'])), ['tofu-pad-thai', 'prawn-pad-thai'])
        self.assertEqual(suggest(book, 'v', Profile(max_minutes=30)), ['Vegetable noodle soup'])
        self.assertEqual(plan_week(book, Profile(max_minutes=20), days=3),
                         ['chicken-noodles', 'tomato-pasta', 'chicken-noodles'])
        self.assertEqual(plan_week(book, Profile(dislikes=['peanuts']), days=4)[3], 'tofu-pad-thai')


if __name__ == '__main__':
    unittest.main()
