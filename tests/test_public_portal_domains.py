# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pl_materialy_scraper as scraper
from email_targeting import is_public_portal_url


class PublicPortalDomainTests(unittest.TestCase):
    def test_blocks_social_and_classifieds(self):
        blocked = (
            "https://www.facebook.com/page",
            "https://warszawa.lento.pl/ogloszenie",
            "https://olx.pl/oferta",
            "https://allegro.pl/listing",
        )
        for url in blocked:
            with self.subTest(url=url):
                self.assertTrue(is_public_portal_url(url))

    def test_allows_company_sites(self):
        allowed = (
            "https://styrnet.pl/kontakt",
            "https://www.diamond.pl",
            "https://www.hplush.pl",
        )
        for url in allowed:
            with self.subTest(url=url):
                self.assertFalse(is_public_portal_url(url))

    def test_row_from_cache_contact_skips_portal(self):
        row = scraper.row_from_cache_contact(
            "https://warszawa.lento.pl/123",
            {
                "company_name_clean": "Test",
                "official_website": "https://warszawa.lento.pl/123",
            },
        )
        self.assertIsNone(row)

    def test_row_from_cache_contact_keeps_company(self):
        row = scraper.row_from_cache_contact(
            "https://styrnet.pl",
            {
                "company_name_clean": "Styrnet",
                "official_website": "https://styrnet.pl",
                "verification_reason": scraper.PENDING_WWW_VERIFY_REASON,
                "page_snippet": "hurtownia materiałów budowlanych skład budowlany",
            },
        )
        self.assertIsNotNone(row)
        self.assertEqual(row["nazwa"], "Styrnet")


if __name__ == "__main__":
    unittest.main()
