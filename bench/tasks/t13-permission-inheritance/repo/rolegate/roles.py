"""The role hierarchy: every role may inherit from any number of parent roles, and the graph has no cycles."""


class UnknownRole(KeyError):
    def __str__(self):
        return 'no role %r' % (self.args[0] if self.args else None)


class CycleError(ValueError):
    """A role would end up inheriting from itself."""


def _check_name(role):
    if not isinstance(role, str) or not role.strip() or role != role.strip():
        raise ValueError('a role name is a non-empty string without surrounding spaces, not %r' % (role,))
    return role


class RoleGraph:
    def __init__(self):
        self._parents = {}

    def __contains__(self, role):
        return role in self._parents

    def __len__(self):
        return len(self._parents)

    def roles(self):
        return sorted(self._parents)

    def add(self, role, parents=()):
        _check_name(role)
        if role in self._parents:
            raise ValueError('role %r exists' % role)
        parents = self._checked_parents(role, parents)
        self._parents[role] = parents

    def remove(self, role):
        self._need(role)
        children = sorted(r for r, ps in self._parents.items() if role in ps)
        if children:
            raise ValueError('role %r is inherited by %s' % (role, ', '.join(children)))
        del self._parents[role]

    def parents(self, role):
        """The role's own parents, in the order they were given."""
        return self._need(role)

    def set_parents(self, role, parents):
        self._need(role)
        parents = self._checked_parents(role, parents)
        for parent in parents:
            if parent == role or role in self.ancestors(parent):
                raise CycleError('%r cannot inherit from %r: %r already inherits from it' % (role, parent, parent))
        self._parents[role] = parents

    def ancestors(self, role):
        """The role itself, then everything it inherits, breadth first, parents in their given order, each once."""
        self._need(role)
        order, seen, frontier = [], {role}, [role]
        while frontier:
            order.extend(frontier)
            following = []
            for current in frontier:
                for parent in self._parents[current]:
                    if parent not in seen:
                        seen.add(parent)
                        following.append(parent)
            frontier = following
        return order

    def descendants(self, role):
        """Every role that inherits from `role`, directly or not; `role` itself is not included."""
        self._need(role)
        found, frontier = set(), [role]
        while frontier:
            current = frontier.pop()
            for child, parents in self._parents.items():
                if current in parents and child not in found:
                    found.add(child)
                    frontier.append(child)
        return found

    def depth(self, role):
        """0 for a role without parents, otherwise one more than its deepest parent."""
        parents = self._need(role)
        return 1 + max(self.depth(p) for p in parents) if parents else 0

    def _need(self, role):
        try:
            return self._parents[role]
        except KeyError:
            raise UnknownRole(role) from None

    def _checked_parents(self, role, parents):
        if isinstance(parents, str):
            parents = (parents,)
        out = []
        for parent in parents:
            self._need(parent)
            if parent == role:
                raise CycleError('%r cannot inherit from itself' % role)
            if parent not in out:
                out.append(parent)
        return tuple(out)
