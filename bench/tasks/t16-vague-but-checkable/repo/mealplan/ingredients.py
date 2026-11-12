"""Ingredient names, and the allergens each ingredient contains.

Recipes are typed in by different cooks and the same thing turns up under several names. canonical() turns any
spelling we know into the one name the tables below use: lower case, single spaces, singular, and an alias replaced
by its main name ('groundnut oil' and 'arachis oil' are both 'peanut oil').

CONTAINS says which allergens an ingredient contains (butter contains milk). ALLERGEN_NAMES lists, for every
allergen, the names people use for it ('dairy' is milk, 'wheat' is gluten).
"""
import re

ALIASES = {
    'groundnut': 'peanut',
    'monkey nut': 'peanut',
    'groundnut oil': 'peanut oil',
    'arachis oil': 'peanut oil',
    'scallion': 'spring onion',
    'green onion': 'spring onion',
    'parmigiano': 'parmesan',
    'parmigiano reggiano': 'parmesan',
    'whole milk': 'milk',
    'semi-skimmed milk': 'milk',
    'double cream': 'cream',
    'single cream': 'cream',
    'cilantro': 'coriander',
    'shrimp': 'prawn',
    'king prawn': 'prawn',
    'eggplant': 'aubergine',
    'zucchini': 'courgette',
    'plain flour': 'wheat flour',
    'flour': 'wheat flour',
    'shoyu': 'soy sauce',
    'natural yogurt': 'yoghurt',
    'yogurt': 'yoghurt',
}

CONTAINS = {
    'peanut': ('peanut',),
    'peanut butter': ('peanut',),
    'peanut oil': ('peanut',),
    'milk': ('milk',),
    'butter': ('milk',),
    'cream': ('milk',),
    'parmesan': ('milk',),
    'cheddar': ('milk',),
    'mozzarella': ('milk',),
    'yoghurt': ('milk',),
    'ghee': ('milk',),
    'egg': ('egg',),
    'mayonnaise': ('egg',),
    'egg noodle': ('egg', 'gluten'),
    'lasagne sheet': ('egg', 'gluten'),
    'wheat flour': ('gluten',),
    'pasta': ('gluten',),
    'bread': ('gluten',),
    'pitta bread': ('gluten',),
    'flatbread': ('gluten',),
    'tortilla': ('gluten',),
    'gravy granule': ('gluten',),
    'soy sauce': ('soy', 'gluten'),
    'tamari': ('soy',),
    'tofu': ('soy',),
    'miso': ('soy',),
    'prawn': ('crustacean',),
    'fish sauce': ('fish',),
    'salmon': ('fish',),
    'anchovy': ('fish',),
    'almond': ('tree nut',),
    'cashew': ('tree nut',),
    'pine nut': ('tree nut',),
    'walnut': ('tree nut',),
    'sesame oil': ('sesame',),
    'sesame seed': ('sesame',),
    'tahini': ('sesame',),
    'celery': ('celery',),
    'mustard': ('mustard',),
}

ALLERGEN_NAMES = {
    'peanut': ('peanut', 'peanuts', 'groundnut', 'groundnuts'),
    'milk': ('milk', 'dairy', 'lactose'),
    'egg': ('egg', 'eggs'),
    'gluten': ('gluten', 'wheat'),
    'soy': ('soy', 'soya', 'soybean', 'soybeans'),
    'fish': ('fish',),
    'crustacean': ('crustacean', 'crustaceans', 'shellfish'),
    'tree nut': ('tree nut', 'tree nuts'),
    'sesame': ('sesame',),
    'celery': ('celery',),
    'mustard': ('mustard',),
}

# Ingredients the tables do not mention but recipes use; known so that their plurals are recognised.
OTHER_KNOWN = frozenset((
    'basil', 'beef mince', 'carrot', 'chicken', 'chicken breast', 'chicken thigh', 'chickpea', 'chilli',
    'coconut milk', 'coriander', 'courgette', 'cucumber', 'dill', 'garlic', 'ginger', 'lemon', 'lettuce', 'lime',
    'mushroom', 'nutmeg', 'olive oil', 'onion', 'pak choi', 'potato', 'rice noodle', 'arborio rice', 'spinach',
    'spring onion', 'tomato', 'vegetable stock', 'aubergine',
))

KNOWN = frozenset(CONTAINS) | frozenset(ALIASES.values()) | OTHER_KNOWN

_SPACES = re.compile(r'\s+')


def _tidy(name):
    return _SPACES.sub(' ', str(name).strip().lower())


def _singular(name):
    """name without a plural ending when the singular is a name we know; otherwise name as it is."""
    for ending, keep in (('oes', 'o'), ('es', ''), ('s', '')):
        if name.endswith(ending):
            stem = name[:-len(ending)] + keep
            if stem in KNOWN or stem in ALIASES:
                return stem
    return name


def canonical(name):
    """The one name the tables use for an ingredient: 'Groundnut Oil' -> 'peanut oil', 'Tomatoes' -> 'tomato'."""
    name = _tidy(name)
    if name in ALIASES:
        return ALIASES[name]
    name = _singular(name)
    return ALIASES.get(name, name)


def allergens_in(name):
    """The allergens the ingredient called name contains, as a frozenset ('Butter' -> {'milk'})."""
    return frozenset(CONTAINS.get(canonical(name), ()))


def allergen_group(name):
    """The allergen a person means by name ('Dairy' -> 'milk', 'groundnuts' -> 'peanut'), or None if unknown."""
    name = _tidy(name)
    for group, names in ALLERGEN_NAMES.items():
        if name in names:
            return group
    return None
