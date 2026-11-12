"""Command line: python3 -m rolegate POLICY.json COMMAND ...

    check   USER ACTION RESOURCE    prints allowed or refused; exit status 0 when allowed, 1 when refused
    explain USER ACTION RESOURCE    prints the decision and the rule and role behind it
    audit   [USER ...]              prints the review sheet of the users given, or of every user
    who-can ACTION RESOURCE         prints the users allowed, one per line
"""

import argparse
import sys

from .audit import audit_user, format_audit, who_can
from .resolver import Resolver
from .storage import load


def build_parser():
    parser = argparse.ArgumentParser(prog='rolegate', description='Ask a role policy questions.')
    parser.add_argument('policy', help='policy JSON file')
    sub = parser.add_subparsers(dest='command')
    for name in ('check', 'explain'):
        p = sub.add_parser(name)
        p.add_argument('user')
        p.add_argument('action')
        p.add_argument('resource')
    p = sub.add_parser('audit')
    p.add_argument('users', nargs='*')
    p = sub.add_parser('who-can')
    p.add_argument('action')
    p.add_argument('resource')
    return parser


def main(argv=None, out=None):
    out = out or sys.stdout
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.command:
        parser.print_help(out)
        return 2
    policy = load(args.policy)
    resolver = Resolver(policy)
    if args.command == 'check':
        allowed = resolver.check(args.user, args.action, args.resource)
        out.write('allowed\n' if allowed else 'refused\n')
        return 0 if allowed else 1
    if args.command == 'explain':
        out.write('%s\n' % (resolver.explain(args.user, args.action, args.resource),))
        return 0
    if args.command == 'audit':
        users = args.users or policy.users()
        out.write('\n'.join(format_audit(user, audit_user(policy, user)) for user in users) + '\n')
        return 0
    if args.command == 'who-can':
        for user in who_can(resolver, args.action, args.resource):
            out.write(user + '\n')
        return 0
    return 2
