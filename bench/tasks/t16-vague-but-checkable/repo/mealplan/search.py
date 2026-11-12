"""The search box and the suggestions under it."""
import re

from .ingredients import canonical

_WORD = re.compile(r"[a-z]+")


def _words(text):
    return _WORD.findall(str(text).lower())


def _dislikes(book, recipe, profile):
    """True when the recipe's own ingredients include something the customer said they dislike."""
    if profile is None or not profile.dislikes:
        return False
    disliked = {canonical(name) for name in profile.dislikes}
    return any(canonical(name) in disliked for name in book.ingredient_names(recipe.id))


def score(book, recipe, words):
    """How well a recipe matches the typed words: 3 per word starting a word of the title, 2 per tag, 1 per
    ingredient (the recipe's own ingredients)."""
    title_words = _words(recipe.title)
    ingredient_words = set()
    for name in book.ingredient_names(recipe.id):
        ingredient_words.update(_words(canonical(name)))
    total = 0
    for word in words:
        if any(title_word.startswith(word) for title_word in title_words):
            total += 3
        if word in recipe.tags:
            total += 2
        if canonical(word) in ingredient_words or word in ingredient_words:
            total += 1
    return total


def search(book, text, profile=None):
    """The ids of the recipes matching text, best match first.

    Ties go to the quicker recipe, then by title. Recipes longer than the customer's max_minutes are left out.
    Recipes with an ingredient the customer dislikes still show, after all the others.
    """
    words = _words(text)
    if not words:
        return []
    found = []
    for recipe in book:
        if profile is not None and not profile.allows_time(recipe):
            continue
        points = score(book, recipe, words)
        if points:
            found.append((_dislikes(book, recipe, profile), -points, recipe.minutes, recipe.title, recipe.id))
    found.sort()
    return [entry[-1] for entry in found]


def _suggestions(book, prefix, max_minutes, limit):
    starts, inside = [], []
    for recipe in book:
        if max_minutes is not None and recipe.minutes > max_minutes:
            continue
        title = recipe.title.lower()
        if title.startswith(prefix):
            starts.append(recipe.title)
        elif any(word.startswith(prefix) for word in _words(title)) or (' ' + prefix) in title:
            inside.append(recipe.title)
    return (sorted(starts) + sorted(inside))[:limit]


def suggest(book, prefix, profile=None, limit=5):
    """Up to `limit` recipe titles for what has been typed so far.

    Titles that start with the typed text come first, then titles with a later word that starts with it; each group
    A to Z. Recipes longer than the customer's max_minutes are left out. The box asks again on every key press, so
    the answers are kept in the book's memo.
    """
    prefix = ' '.join(str(prefix).lower().split())
    if not prefix or limit <= 0:
        return []
    max_minutes = profile.max_minutes if profile is not None else None
    cache = book.memo.setdefault('suggest', {})
    key = (prefix, limit, max_minutes)
    if key not in cache:
        cache[key] = _suggestions(book, prefix, max_minutes, limit)
    return list(cache[key])
