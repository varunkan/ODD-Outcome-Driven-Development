"""A customer's food profile, as they filled it in on the settings page."""


class Profile:
    """What a customer told us about their food.

    allergens and dislikes are kept exactly as the customer typed them ('Peanuts', 'coriander'). max_minutes, when
    set, is the longest a recipe may take.
    """

    def __init__(self, name='', allergens=(), dislikes=(), max_minutes=None):
        if max_minutes is not None and (not isinstance(max_minutes, int) or max_minutes <= 0):
            raise ValueError('max_minutes must be a whole number above 0, or None')
        self.name = name
        self.allergens = tuple(str(item) for item in allergens if str(item).strip())
        self.dislikes = tuple(str(item) for item in dislikes if str(item).strip())
        self.max_minutes = max_minutes

    def __repr__(self):
        return 'Profile(%r)' % (self.name,)

    def allows_time(self, recipe):
        return self.max_minutes is None or recipe.minutes <= self.max_minutes

    def to_dict(self):
        return {'name': self.name, 'allergens': list(self.allergens), 'dislikes': list(self.dislikes),
                'max_minutes': self.max_minutes}

    @classmethod
    def from_dict(cls, data):
        return cls(name=data.get('name', ''), allergens=data.get('allergens', ()), dislikes=data.get('dislikes', ()),
                   max_minutes=data.get('max_minutes'))


NOBODY = Profile()
