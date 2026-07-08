# -*- coding: utf-8 -*-
"""
Testy regresyjne kampanii PL — słowa kluczowe, filtry, maile, rotacja województw.

  python -m unittest tests.test_pl_materialy_regression -v
  python -m pytest tests/test_pl_materialy_regression.py -v
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pl_materialy_scraper as scraper
from campaign_data_paths import GOOGLE_DRIVE_PL_FOLDER_ID, campaign_output_paths
from pl_materialy_inquiry_email_pl import (
    DEFAULT_INQUIRY_PHONE_PL,
    build_fixed_material_inquiry_pl,
    build_inquiry_signature_pl,
)
from pl_materialy_supplier_filter import (
    is_loose_serper_discovery_candidate,
    is_serper_only_pending_candidate,
    is_valid_retail_store_builder_contact,
)
from pl_wojewodztwo_keywords import (
    ALL_WOJEWODZTWA,
    SERPER_DISCOVERY_BROAD_TERMS,
    SERPER_DISCOVERY_FALLBACK_TERMS,
    SERPER_DISCOVERY_LANDKREIS_TERMS,
    SERPER_DISCOVERY_PLACES_TERMS,
    SERPER_DISCOVERY_TERMS,
    build_discovery_terms,
    build_region_suffix,
    default_max_discovery_terms_for,
)
from pl_wojewodztwo_rotation import (
    WOJEWODZTWO_ROTATION_ORDER,
    commit_rotation_after_run,
    load_rotation_state,
    peek_next_wojewodztwo,
    rotation_state_path,
)


class WojewodztwoCoverageRegression(unittest.TestCase):
    def test_all_wojewodztwa_configured(self):
        self.assertEqual(len(ALL_WOJEWODZTWA), 16)
        self.assertEqual(len(scraper.CAMPAIGN_ACTIVE_BUNDESLAENDER), 16)

    def test_countrywide_region_suffix(self):
        self.assertEqual(build_region_suffix(list(ALL_WOJEWODZTWA)), "Polska")
        self.assertEqual(build_region_suffix(["mazowieckie", "malopolskie"]), "Polska MZ MA")

    def test_discovery_terms_polish(self):
        terms = build_discovery_terms(["mazowieckie"], max_terms=10)
        self.assertGreaterEqual(len(terms), 5)
        joined = " ".join(terms).lower()
        self.assertIn("materiały", joined)
        self.assertIn("warszawa", joined.lower())

    def test_discovery_waves_exported(self):
        self.assertGreaterEqual(len(SERPER_DISCOVERY_FALLBACK_TERMS), 5)
        self.assertGreaterEqual(len(SERPER_DISCOVERY_BROAD_TERMS), 10)
        self.assertGreaterEqual(len(SERPER_DISCOVERY_LANDKREIS_TERMS), 5)
        self.assertGreaterEqual(len(SERPER_DISCOVERY_PLACES_TERMS), 5)
        self.assertGreaterEqual(len(SERPER_DISCOVERY_TERMS), 100)


class SerperConfigRegression(unittest.TestCase):
    def test_serper_pl_locale(self):
        self.assertEqual(scraper.SERPER_COUNTRY, "pl")
        self.assertEqual(scraper.SERPER_LANGUAGE, "pl")
        self.assertEqual(scraper.COUNTRY_RESTRICTION, "PL")

    def test_max_discovery_terms_scale(self):
        self.assertGreaterEqual(default_max_discovery_terms_for(list(ALL_WOJEWODZTWA)), 1000)


class SupplierFilterRegression(unittest.TestCase):
    def test_accepts_building_supplier(self):
        self.assertTrue(
            is_valid_retail_store_builder_contact(
                email="info@budmat.pl",
                url="https://www.budmat.pl/",
                name="Hurtownia Budowlana Warszawa Sp. z o.o.",
                text="Hurtownia materiałów budowlanych cement piasek żwir katalog ceny dostawa",
            )
        )

    def test_rejects_interior_design(self):
        self.assertFalse(
            is_valid_retail_store_builder_contact(
                email="info@design.pl",
                url="https://design.pl",
                name="Wykończenia wnętrz",
                text="remont mieszkań pod klucz",
            )
        )

    def test_loose_serper_candidate(self):
        self.assertTrue(
            is_loose_serper_discovery_candidate(
                url="https://budmat.pl",
                name="Skład budowlany",
                text="materiały budowlane hurt",
            )
        )

    def test_serper_only_pending(self):
        self.assertTrue(
            is_serper_only_pending_candidate(
                name="Hurtownia Kraków",
                url="https://bud-krak.pl",
                text="hurtownia budowlana cement",
            )
        )


class EmailBrandingRegression(unittest.TestCase):
    def test_default_phone(self):
        self.assertEqual(DEFAULT_INQUIRY_PHONE_PL, "516513965")
        self.assertIn("516513965", build_inquiry_signature_pl())

    def test_polish_template(self):
        body = build_fixed_material_inquiry_pl()
        self.assertIn("Szanowni Państwo", body)
        self.assertIn("materiałów budowlanych", body)
        self.assertNotIn("+380", body)

    @patch("mail_transport.send_smtp_email")
    @patch("scraper_env.get_mail_password", return_value="secret")
    @patch("scraper_env.get_mail_user", return_value="test@gmail.com")
    def test_send_email_no_attachments(self, _u, _p, mock_send):
        import logging

        mock_send.return_value = (True, "ok")
        ok, _ = scraper.send_email_pl_materialy(
            "kontakt@hurt.pl",
            "Zapytanie o dostawę materiałów budowlanych",
            build_fixed_material_inquiry_pl(),
            logging.getLogger("test"),
        )
        self.assertTrue(ok)
        self.assertEqual(mock_send.call_args.kwargs.get("attachment_paths"), [])


class WojewodztwoRotationRegression(unittest.TestCase):
    def test_rotation_order_length(self):
        self.assertEqual(len(WOJEWODZTWO_ROTATION_ORDER), 16)
        self.assertEqual(peek_next_wojewodztwo(), WOJEWODZTWO_ROTATION_ORDER[0])

    def test_commit_advances_index(self):
        tmp = Path(tempfile.mkdtemp())
        path = rotation_state_path(tmp)
        state = load_rotation_state(path)
        woj = peek_next_wojewodztwo(state)
        nxt = commit_rotation_after_run(path, state, woj)
        self.assertIn(nxt, WOJEWODZTWO_ROTATION_ORDER)
        self.assertNotEqual(nxt, woj)


class CampaignPathsRegression(unittest.TestCase):
    def test_pl_output_paths_basename(self):
        paths = campaign_output_paths(ROOT, "pl_materialy")
        self.assertTrue(str(paths["cache_file"]).endswith("pl_materialy_cache.json"))
        self.assertTrue(str(paths["output_file"]).endswith("pl_materialy_kontakte.xlsx"))

    def test_pl_drive_folder_id(self):
        self.assertEqual(GOOGLE_DRIVE_PL_FOLDER_ID, "1O15CdN0TH8rx74sPP5C1GuYSweX81IGw")


if __name__ == "__main__":
    unittest.main(verbosity=2)
