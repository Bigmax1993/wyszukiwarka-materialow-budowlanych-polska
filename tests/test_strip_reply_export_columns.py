# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LIBS = ROOT / "libs"
for p in (ROOT, LIBS):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from scraper_email_replies import (  # noqa: E402
    is_reply_export_column,
    strip_reply_export_columns,
)


class StripReplyExportColumnsTest(unittest.TestCase):
    def test_detects_listed_columns(self):
        for name in (
            "Status maila",
            "Wysłano",
            "Odpowiedź",
            "Status odpowiedzi",
            "Waluta",
            "Wymaga interwencji",
            "Zadzwoń?",
            "Źródło ceny",
            "Ceny (wszystkie)",
            "Opis",
            "Cena",
            "Cena rel. 1",
            "Cena rel. 2",
            "Cena(wszystkie)",
        ):
            self.assertTrue(is_reply_export_column(name), name)

    def test_keeps_business_columns(self):
        for name in ("Nazwa firmy", "E-mail", "Status", "Telefon", "Strona www"):
            self.assertFalse(is_reply_export_column(name), name)

    def test_strip_row(self):
        row = {
            "Nazwa firmy": "ACME",
            "E-mail": "a@b.pl",
            "Status maila": "sent",
            "Cena rel. 1": "10",
            "Opis": "x",
            "Wysłano": "2026-01-01",
        }
        out = strip_reply_export_columns(row)
        self.assertEqual(out, {"Nazwa firmy": "ACME", "E-mail": "a@b.pl"})


if __name__ == "__main__":
    unittest.main()
