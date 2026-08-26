# -*- coding: utf-8 -*-
from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.gdrive_upload_wyniki import (  # noqa: E402
    _gdrive_append_xlsx_enabled,
    _gdrive_consolidate_all_xlsx_enabled,
    _gdrive_version_xlsx_enabled,
    _skip_gdrive_upload,
    is_pl_kontakte_xlsx_name,
    versioned_xlsx_upload_name,
)


class GdriveUploadDefaultsTest(unittest.TestCase):
    def test_version_xlsx_default_off(self):
        env = os.environ.pop("GDRIVE_VERSION_XLSX", None)
        try:
            self.assertFalse(_gdrive_version_xlsx_enabled())
        finally:
            if env is not None:
                os.environ["GDRIVE_VERSION_XLSX"] = env

    def test_append_xlsx_default_on(self):
        env = os.environ.pop("GDRIVE_APPEND_XLSX", None)
        try:
            self.assertTrue(_gdrive_append_xlsx_enabled())
        finally:
            if env is not None:
                os.environ["GDRIVE_APPEND_XLSX"] = env

    def test_consolidate_all_xlsx_default_on(self):
        env = os.environ.pop("GDRIVE_CONSOLIDATE_ALL_XLSX", None)
        try:
            self.assertTrue(_gdrive_consolidate_all_xlsx_enabled())
        finally:
            if env is not None:
                os.environ["GDRIVE_CONSOLIDATE_ALL_XLSX"] = env


class GdriveSkipUploadTest(unittest.TestCase):
    def test_skip_json_and_log(self):
        self.assertTrue(_skip_gdrive_upload(Path("pl_materialy_cache.json")))
        self.assertTrue(_skip_gdrive_upload(Path("pl_materialy_scraper.log")))
        self.assertTrue(_skip_gdrive_upload(Path("pl_materialy_wojewodztwo_rotation.JSON")))

    def test_upload_xlsx_and_eml(self):
        self.assertFalse(_skip_gdrive_upload(Path("pl_materialy_kontakte.xlsx")))
        self.assertFalse(_skip_gdrive_upload(Path("wyslane/mail.eml")))


class GdriveKontakteNameTest(unittest.TestCase):
    def test_canonical_and_dated(self):
        self.assertTrue(is_pl_kontakte_xlsx_name("pl_materialy_kontakte.xlsx"))
        self.assertTrue(
            is_pl_kontakte_xlsx_name("pl_materialy_kontakte_2026-06-08_1405.xlsx")
        )
        self.assertFalse(is_pl_kontakte_xlsx_name("notes.txt"))
        self.assertFalse(is_pl_kontakte_xlsx_name("random.xlsx"))


class GdriveVersionedXlsxTest(unittest.TestCase):
    def test_versions_kontakte_xlsx(self):
        name = versioned_xlsx_upload_name(
            "de_gu_bauunternehmen_kontakte.xlsx", stamp="2026-06-08_1405"
        )
        self.assertEqual(name, "de_gu_bauunternehmen_kontakte_2026-06-08_1405.xlsx")

    def test_non_xlsx_unchanged(self):
        self.assertEqual(
            versioned_xlsx_upload_name("de_gu_bauunternehmen_cache.json", stamp="x"),
            "de_gu_bauunternehmen_cache.json",
        )


class GdriveSheetAppendTest(unittest.TestCase):
    def test_canonical_sheet_and_polish_bool(self):
        from scripts.gdrive_upload_wyniki import (
            _append_sheet_rows,
            _canonical_sheet_name,
            _normalize_export_row,
            order_sheet_columns,
        )
        import pl_materialy_scraper as scraper

        self.assertEqual(_canonical_sheet_name("Kontakty"), "Kontakte")
        self.assertEqual(_canonical_sheet_name("Województwa"), "Wojewodztwa")
        row = _normalize_export_row(
            {"Firmenname": "A", "WWW_geprueft": "ja", "Webseite": "https://a.pl"},
            scraper,
        )
        self.assertEqual(row["Nazwa firmy"], "A")
        self.assertEqual(row["WWW sprawdzone"], "tak")
        self.assertEqual(row["Strona www"], "https://a.pl")

        bucket: dict = {}
        _append_sheet_rows(
            bucket,
            "Kontakte",
            [
                {"Nazwa firmy": "A", "URL": "https://a.pl", "Status maila": "sent"},
                {"Firmenname": "A", "URL": "https://a.pl", "Telefon": "500"},
            ],
            scraper,
        )
        self.assertEqual(len(bucket), 1)
        merged = next(iter(bucket.values()))
        self.assertEqual(merged["Telefon"], "500")
        # Kolumny odpowiedzi/cen są usuwane już przy normalizacji wiersza.
        self.assertNotIn("Status maila", merged)
        ordered = order_sheet_columns("Kontakte", [merged], scraper)
        self.assertEqual(ordered[0]["Nazwa firmy"], "A")
        self.assertNotIn("Status maila", ordered[0])
        self.assertNotIn("Cena rel. 1", ordered[0])


if __name__ == "__main__":
    unittest.main()
