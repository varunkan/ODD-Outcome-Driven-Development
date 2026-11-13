"""The weekly dinner plan."""


def _candidates(book, profile):
    """The dinners the plan may use for this customer, quickest first, then by id."""
    allergens = {name.strip().lower() for name in profile.allergens} if profile is not None else set()
    dislikes = {name.strip().lower() for name in profile.dislikes} if profile is not None else set()
    chosen = []
    for recipe in book.with_tag('dinner'):
        if profile is not None and not profile.allows_time(recipe):
            continue
        names = {name.lower() for name in book.ingredient_names(recipe.id)}
        if names & allergens:
            continue
        if names & dislikes:
            continue
        chosen.append(recipe)
    chosen.sort(key=lambda recipe: (recipe.minutes, recipe.id))
    return chosen


def plan_week(book, profile=None, days=7, week=0):
    """A dinner for each of `days` days, as a list of recipe ids.

    The plan goes round the customer's dinners, quickest first, starting where last week's plan stopped (week 0
    starts at the quickest), and comes round again when there are fewer dinners than days.
    Raises ValueError when no dinner suits the customer.
    """
    if days < 0:
        raise ValueError('days must be zero or more')
    if days == 0:
        return []
    dinners = _candidates(book, profile)
    if not dinners:
        raise ValueError('no dinner suits this profile')
    start = week * days
    return [dinners[(start + day) % len(dinners)].id for day in range(days)]
