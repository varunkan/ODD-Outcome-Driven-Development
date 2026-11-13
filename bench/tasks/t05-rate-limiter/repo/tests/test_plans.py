import unittest

from apigate.plans import PLANS, Plan, parse_rate, plan_named


class PlanTests(unittest.TestCase):

    def test_rates_are_parsed_into_a_count_and_seconds(self):
        self.assertEqual(parse_rate('60/hour'), (60, 3600))
        self.assertEqual(parse_rate(' 5 / Second '), (5, 1))
        for bad in ('', '60', 'lots/hour', '60/fortnight', '0/hour', None):
            with self.assertRaises(ValueError):
                parse_rate(bad)

    def test_plans_describe_themselves_for_the_pricing_page(self):
        self.assertEqual(PLANS['free'].describe(), 'free: 60 requests per hour')
        self.assertEqual(PLANS['pro'].describe(), 'pro: 600 requests per minute')
        self.assertEqual(PLANS['internal'].describe(), 'internal: unlimited')
        self.assertEqual(Plan('trial', 1, 1800).describe(), 'trial: 1 request per 30 minutes')

    def test_built_in_plans_are_found_by_name(self):
        self.assertEqual(plan_named('free'), Plan('free', 60, 3600))
        self.assertTrue(plan_named('internal').unlimited)
        self.assertFalse(plan_named('pro').unlimited)
        with self.assertRaises(ValueError):
            plan_named('platinum')
        with self.assertRaises(ValueError):
            Plan('broken', 10, 0)


if __name__ == '__main__':
    unittest.main()
