# -*- coding: utf-8 -*-
"""Testy maili PL — kampania materiały budowlane."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pl_materialy_inquiry_email_pl import (
    DEFAULT_INQUIRY_PHONE_PL,
    DEFAULT_INQUIRY_SENDER_NAME_PL,
    build_fixed_material_inquiry_pl,
    build_inquiry_signature_pl,
    dedupe_inquiry_signature,
    ensure_inquiry_signature,
    inquiry_phone,
    inquiry_sender_name,
)


class PlInquiryEmailTest(unittest.TestCase):
    def test_default_phone(self):
        self.assertEqual(DEFAULT_INQUIRY_PHONE_PL, "516513965")
        self.assertIn("516513965", build_inquiry_signature_pl())
        self.assertEqual(inquiry_phone(), "516513965")

    def test_polish_template(self):
        body = build_fixed_material_inquiry_pl()
        self.assertIn("Szanowni Państwo", body)
        self.assertIn("materiałów budowlanych", body)
        self.assertIn("Z poważaniem", body)
        self.assertIn("516513965", body)
        self.assertTrue("Maksym" in body or inquiry_sender_name() in body)

    def test_no_ua_phone_in_signature(self):
        sig = build_inquiry_signature_pl()
        self.assertNotIn("+380", sig)

    def test_signature_multiline_not_collapsed(self):
        sig = build_inquiry_signature_pl()
        self.assertIn("\n", sig)
        self.assertLessEqual(sig.count("Maksym"), 1)

    def test_dedupe_double_signature(self):
        sig = build_inquiry_signature_pl()
        body = f"Szanowni Państwo,\n\nTreść maila.\n\n{sig}\n\n{sig}"
        cleaned = dedupe_inquiry_signature(body)
        self.assertEqual(cleaned.lower().count("z poważaniem"), 1)
        self.assertEqual(cleaned.count("Maksym"), 1)

    def test_ensure_does_not_append_when_present(self):
        sig = build_inquiry_signature_pl()
        body = f"Szanowni Państwo,\n\nTreść.\n\n{sig}"
        ensured = ensure_inquiry_signature(body)
        self.assertEqual(ensured.lower().count("z poważaniem"), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
