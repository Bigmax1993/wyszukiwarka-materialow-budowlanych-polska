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
