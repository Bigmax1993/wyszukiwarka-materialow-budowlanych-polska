# -*- coding: utf-8 -*-
import unittest

from scraper_env import (
    CANONICAL_PL_SENDER_NAME,
    normalize_mail_sender_name,
    normalize_sender_name_in_text,
)


class TestSenderNameNormalization(unittest.TestCase):
    def test_legacy_polish_diacritics(self):
        self.assertEqual(
            normalize_mail_sender_name("Maksym Świńczak"),
            CANONICAL_PL_SENDER_NAME,
        )
        self.assertEqual(
            normalize_mail_sender_name("  Maksym  Świńczak  "),
            CANONICAL_PL_SENDER_NAME,
        )

    def test_canonical_unchanged(self):
        self.assertEqual(
            normalize_mail_sender_name("Maksym Swinczak"),
            CANONICAL_PL_SENDER_NAME,
        )

    def test_with_company_suffix(self):
        self.assertEqual(
            normalize_mail_sender_name("Maksym Świńczak, Kanbud Sp. z o.o."),
            f"{CANONICAL_PL_SENDER_NAME}, Kanbud Sp. z o.o.",
        )

    def test_in_text_body(self):
        body = "Z poważaniem,\n\nMaksym Świńczak\nhttps://swinczakdata.pl"
        fixed = normalize_sender_name_in_text(body)
        self.assertIn(CANONICAL_PL_SENDER_NAME, fixed)
        self.assertNotIn("Świńczak", fixed)


if __name__ == "__main__":
    unittest.main()
