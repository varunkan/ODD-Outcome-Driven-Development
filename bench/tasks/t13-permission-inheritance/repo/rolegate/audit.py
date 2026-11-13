"""What the quarterly access review reads: per user, every rule that reaches them and what it gives."""

from collections import namedtuple

AuditEntry = namedtuple('AuditEntry', 'action pattern effect role')


def audit_user(policy, user):
    """One entry per distinct (action, pattern) among the rules the user has, on an assigned role or inherited:
    the effect the user gets for it and the role that effect comes from. Sorted by action, then pattern.

    Roles are visited from the assigned ones outwards, so a rule on a nearer role is the one reported."""
    entries = {}
    seen = set()

    def visit(role):
        if role in seen:
            return
        seen.add(role)
        for rule in policy.rules(role):
            entries.setdefault((rule.action, rule.pattern), AuditEntry(rule.action, rule.pattern, rule.effect, role))
        for parent in policy.graph.parents(role):
            visit(parent)

    for role in policy.roles_of(user):
        visit(role)
    return [entries[key] for key in sorted(entries)]


def audit_all(policy):
    """{user: audit_user(policy, user)} for every user that holds a role."""
    return {user: audit_user(policy, user) for user in policy.users()}


def who_can(resolver, action, resource):
    """The users, sorted, that may do `action` on `resource`."""
    return [user for user in resolver.policy.users() if resolver.check(user, action, resource)]


def format_audit(user, entries):
    """The review sheet for one user, one line per entry."""
    if not entries:
        return '%s: no rules' % user
    width_action = max(len(e.action) for e in entries)
    width_pattern = max(len(e.pattern) for e in entries)
    lines = ['%s:' % user]
    for e in entries:
        lines.append('  %-5s  %-*s  %-*s  from %s' % (e.effect, width_action, e.action, width_pattern, e.pattern,
                                                      e.role))
    return '\n'.join(lines)
