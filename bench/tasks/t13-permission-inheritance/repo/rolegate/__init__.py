"""rolegate: role-based access rules with inheritance. Python 3 standard library only."""

from .audit import AuditEntry, audit_all, audit_user, format_audit, who_can
from .cache import DecisionCache
from .model import ALLOW, DENY, Decision, Rule
from .patterns import matches
from .policy import Policy
from .resolver import Resolver
from .roles import CycleError, RoleGraph, UnknownRole
from .storage import load, save

__all__ = ['ALLOW', 'AuditEntry', 'CycleError', 'DENY', 'Decision', 'DecisionCache', 'Policy', 'Resolver',
           'RoleGraph', 'Rule', 'UnknownRole', 'audit_all', 'audit_user', 'format_audit', 'load', 'matches', 'save',
           'who_can']
