# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pl_materialy_scraper as scraper  # noqa: E402


class ExcelPolishHeadersTest(unittest.TestCase):
    def test_export_columns_are_polish(self):
        forbidden = (
            "Firmenname",
            "Adresse",
            "Webseite",
            "WWW_geprueft",
            "Kleinunternehmen",
            "GU_Marker",
            "Kategorie_materialow",
            "E-Mail",
        )
        for col in scraper.EXPORT_COLUMNS:
            self.assertNotIn(col, forbidden)
            self.assertTrue(col)

    def test_normalize_aliases_to_polish(self):
        rec = scraper.normalize_excel_record_headers(
            {
                "Firmenname": "ACME",
                "Adresse": "ul. Test 1",
                "WWW_geprueft": "ja",
                "Kleinunternehmen": "nein",
                "GU": "ja",
                "Kategorie_materialow": "styropian",
            }
        )
        self.assertEqual(rec["Nazwa firmy"], "ACME")
        self.assertEqual(rec["Adres"], "ul. Test 1")
        self.assertEqual(rec["WWW sprawdzone"], "ja")
        self.assertEqual(rec["Mała firma"], "nein")
        self.assertEqual(rec["Generalny wykonawca"], "ja")
        self.assertEqual(rec["Kategorie materiałów"], "styropian")

    def test_row_from_excel_accepts_old_and_new(self):
        old = scraper.row_from_excel_record(
            {
                "Firmenname": "Firma A",
                "Webseite": "https://a.example",
                "URL": "https://a.example",
                "WWW_geprueft": "ja",
                "Kleinunternehmen": "nein",
            }
        )
        self.assertEqual(old["nazwa"], "Firma A")
        self.assertTrue(old["retail_verified"])
        self.assertFalse(old["is_small_firm"])

        new = scraper.row_from_excel_record(
            {
                "Nazwa firmy": "Firma B",
                "Strona www": "https://b.example",
                "URL": "https://b.example",
                "WWW sprawdzone": "tak",
                "Mała firma": "nie",
                "Kategorie materiałów": "cement",
            }
        )
        self.assertEqual(new["nazwa"], "Firma B")
        self.assertTrue(new["retail_verified"])
        self.assertFalse(new["is_small_firm"])
        self.assertEqual(new["retail_chains_found"], "cement")

    def test_kontakte_columns_polish(self):
        cols = scraper.row_to_excel_kontakte_columns(
            {
                "nazwa": "X",
                "adres": "ul. 1",
                "bundesland": "mazowieckie",
                "telefon": "500",
                "email_target": "a@b.pl",
                "www": "https://x.pl",
                "url": "https://x.pl",
                "retail_chains_found": "płyty",
            }
        )
        self.assertIn("Kategorie materiałów", cols)
        self.assertNotIn("Kategorie_materialow", cols)


if __name__ == "__main__":
    unittest.main()
