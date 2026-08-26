# -*- coding: utf-8 -*-
import unittest

from pl_claude_prompts import build_row_cleanup_prompt


class PlKillerRowCleanupPromptTest(unittest.TestCase):
    def test_killer_rules_and_schema(self):
        p = build_row_cleanup_prompt(
            company="https://facebook.com/firma",
            address="mazowieckie",
            phone="Tel +48 22 111, Fax +48 22 222",
            email="biuro@test.pl",
            website="https://facebook.com/firma",
            states="mazowieckie, slaskie, pomorskie",
            handelsketten="styropian, wełna tak",
            url="https://facebook.com/firma",
        )
        self.assertIn("KILLER-REGELN", p)
        self.assertIn("company_name_clean", p)
        self.assertIn("SCHEMA", p)
        self.assertIn("mazowieckie, slaskie, pomorskie", p)
        self.assertIn("facebook.com", p.lower())
        self.assertIn("lento.pl", p.lower())
        self.assertNotIn("Filialbau", p)


if __name__ == "__main__":
    unittest.main()
