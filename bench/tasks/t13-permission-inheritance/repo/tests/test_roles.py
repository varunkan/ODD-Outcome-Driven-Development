import unittest

from rolegate import CycleError, RoleGraph, UnknownRole


def graph():
    g = RoleGraph()
    g.add('base')
    g.add('staff', ['base'])
    g.add('auditor', ['base'])
    g.add('lead', ['staff', 'auditor'])
    g.add('head', ['lead'])
    return g


class RoleGraphTest(unittest.TestCase):
    def test_ancestors_breadth_first_each_once(self):
        self.assertEqual(graph().ancestors('head'), ['head', 'lead', 'staff', 'auditor', 'base'])
        self.assertEqual(graph().ancestors('base'), ['base'])

    def test_parent_order_is_kept(self):
        g = graph()
        g.set_parents('lead', ['auditor', 'staff'])
        self.assertEqual(g.ancestors('lead'), ['lead', 'auditor', 'staff', 'base'])

    def test_descendants(self):
        self.assertEqual(graph().descendants('staff'), {'lead', 'head'})
        self.assertEqual(graph().descendants('base'), {'staff', 'auditor', 'lead', 'head'})
        self.assertEqual(graph().descendants('head'), set())

    def test_depth(self):
        self.assertEqual(graph().depth('base'), 0)
        self.assertEqual(graph().depth('head'), 3)

    def test_cycles_are_refused(self):
        g = graph()
        with self.assertRaises(CycleError):
            g.set_parents('base', ['head'])
        with self.assertRaises(CycleError):
            g.set_parents('staff', ['staff'])
        self.assertEqual(g.parents('base'), ())

    def test_unknown_roles(self):
        g = graph()
        with self.assertRaises(UnknownRole):
            g.add('x', ['nope'])
        with self.assertRaises(UnknownRole):
            g.ancestors('nope')

    def test_remove_only_leaves(self):
        g = graph()
        with self.assertRaises(ValueError):
            g.remove('staff')
        g.remove('head')
        self.assertNotIn('head', g)

    def test_names(self):
        g = RoleGraph()
        for bad in ('', ' x', None):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                g.add(bad)
        g.add('x')
        with self.assertRaises(ValueError):
            g.add('x')
