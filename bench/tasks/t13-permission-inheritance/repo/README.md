# rolegate

Role-based access rules for our document service. Roles inherit from other roles, rules on a role allow or deny an
action on a set of resources, users hold roles. Python 3 standard library only.

```python
from rolegate import Policy, Resolver

policy = Policy()
policy.add_role('staff')
policy.add_rule('staff', 'allow', 'read', 'docs/**')
policy.add_role('editor', parents=['staff'])
policy.add_rule('editor', 'allow', 'write', 'docs/drafts/**')
policy.assign('ann', 'editor')

resolver = Resolver(policy)
resolver.check('ann', 'read', 'docs/handbook/leave.md')      # True: inherited from staff
resolver.explain('ann', 'write', 'docs/handbook/leave.md')   # Decision(allowed=False, effect=None, role=None, rule=None)
```

## The rules

- A user has the roles assigned to them and every role those inherit from, at any depth.
- A rule is `(effect, action, pattern)`: effect `allow` or `deny`; an action such as `read`, or `*` for every
  action; a resource pattern where `*` is one path segment and `**` any number (`rolegate/patterns.py`).
- **Deny wins.** A request is allowed when at least one rule the user has allows it and no rule the user has denies
  it. A user's roles, inherited ones included, are one set: the order roles were assigned in or parents were listed
  in does not change an answer.
- No matching rule means refused.

## What is in it

- `rolegate/roles.py`: `RoleGraph`, the hierarchy (multiple parents, no cycles).
- `rolegate/policy.py`: `Policy`: `add_role(role, parents=())`, `set_parents`, `add_rule(role, effect, action,
  pattern)`, `remove_rule`, `assign(user, role)`, `unassign`, `roles_of`, `users_with`, `to_dict`/`from_dict`.
- `rolegate/resolver.py`: `Resolver(policy, cache=None)`: `check(user, action, resource)` -> bool,
  `explain(...)` -> `Decision(allowed, effect, role, rule)`, `filter(user, action, resources)` -> the allowed ones in
  the order given, `roles(user)`. Decisions are cached; `resolver.computed` counts those worked out from the policy.
  The resolver subscribes to the policy and drops cached answers a change affects.
- `rolegate/audit.py`: `audit_user(policy, user)` -> `[AuditEntry(action, pattern, effect, role)]`, the quarterly
  access review; `audit_all`, `format_audit`; `who_can(resolver, action, resource)`.
- `rolegate/storage.py`: `save(policy, path)` / `load(path)`, one JSON file.
- `python3 -m rolegate POLICY.json check|explain|audit|who-can ...` (`rolegate/cli.py`).

## Tests

```
python3 -m unittest discover -s tests
```
