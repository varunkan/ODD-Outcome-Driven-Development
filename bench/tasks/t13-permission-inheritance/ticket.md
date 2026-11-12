# Contractors can open finance documents although their role inherits a deny

Our contractors hold the role `contractor`, which inherits from `staff` (read everything under `docs/`) and from
`restricted` (no reading under `docs/finance/`). The README says deny wins, yet a contractor can read finance
documents:

```python
>>> from rolegate import Policy, Resolver
>>> policy = Policy()
>>> policy.add_role('staff')
>>> policy.add_rule('staff', 'allow', 'read', 'docs/**')
>>> policy.add_role('restricted')
>>> policy.add_rule('restricted', 'deny', 'read', 'docs/finance/**')
>>> policy.add_role('contractor', parents=['staff', 'restricted'])
>>> policy.assign('dana', 'contractor')
>>> resolver = Resolver(policy)
>>> resolver.check('dana', 'read', 'docs/finance/q3.pdf')
True
```

Expected: `False`. Listing `restricted` before `staff` happens to give `False`, but the order of parents must not
matter, and in our real setup the deny sits two or three levels above the role people hold.

We found it during the access review, and the review sheet is wrong as well: for a user whose roles both allow and
deny the same action on the same pattern, `audit_user` shows the allow. We also add rules while the service runs,
and we suspect some users keep their old answers afterwards.

What we need:

1. **The rule in the README holds.** A request is refused when any rule the user has denies it: a rule on a role
   assigned to them or on any role those inherit from, at any depth. That deny wins over every allow that also
   matches, whichever role the allow is on (the user's own role included) and whatever the order of assigned roles
   or of parents. Without a matching deny, a matching allow allows; with no matching rule, refused.
2. **Every way of asking gives that same answer**: `Resolver.check`; `Resolver.explain`, whose `Decision` then has
   `allowed=False`, `effect='deny'`, and the deny rule and the role it is on as `rule` and `role`;
   `Resolver.filter(user, action, resources)`; `who_can(resolver, action, resource)`; and the command line, which uses
   these.
3. **The review sheet.** `audit_user(policy, user)` keeps one entry per distinct `(action, pattern)` among the
   user's rules, and when the user has both an allow and a deny for the same action and pattern, the entry shows
   `effect='deny'` and the role the deny is on, wherever the two roles sit in the hierarchy.
4. **Changes are seen at once.** After `add_rule`, `remove_rule`, `set_parents`, `assign` or `unassign` returns,
   every answer above reflects the change for every user it affects, including users who only have the changed role
   through inheritance, at any depth.
5. **The cache stays.** Asking `check` or `explain` the same question again with no change to the policy in between
   must not work the decision out again: `resolver.computed` must not go up.

The interface stays as it is: `Policy` and its methods, `Resolver(policy)` with `check`, `explain`, `filter`, `roles`
and `computed`, `Decision(allowed, effect, role, rule)`, `audit_user`, `AuditEntry(action, pattern, effect, role)`
and `who_can`.
