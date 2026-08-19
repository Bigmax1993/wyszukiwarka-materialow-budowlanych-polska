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
    _gdrive_version_xlsx_enabled,
    _skip_gdrive_upload,
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


class GdriveSkipUploadTest(unittest.TestCase):
    def test_skip_json_and_log(self):
        self.assertTrue(_skip_gdrive_upload(Path("pl_materialy_cache.json")))
        self.assertTrue(_skip_gdrive_upload(Path("pl_materialy_scraper.log")))
        self.assertTrue(_skip_gdrive_upload(Path("pl_materialy_wojewodztwo_rotation.JSON")))

    def test_upload_xlsx_and_eml(self):
        self.assertFalse(_skip_gdrive_upload(Path("pl_materialy_kontakte.xlsx")))
        self.assertFalse(_skip_gdrive_upload(Path("wyslane/mail.eml")))


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


if __name__ == "__main__":
    unittest.main()
