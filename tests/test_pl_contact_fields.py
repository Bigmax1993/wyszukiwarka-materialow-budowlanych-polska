# -*- coding: utf-8 -*-
from __future__ import annotations

import unittest

from pl_contact_fields import (
    extract_pl_address_from_text,
    is_pl_junk_company_name,
    is_pl_seo_title,
    looks_like_marketing_text,
    looks_like_pl_physical_address,
    sanitize_export_address,
    serper_discovery_address,
)


class PlContactFieldsTest(unittest.TestCase):
    def test_rejects_marketing_as_address(self):
        self.assertTrue(
            looks_like_marketing_text(
                "W naszym asortymencie znajdziecie Państwo wysokiej jakości materiały"
            )
        )
        self.assertEqual(
            sanitize_export_address(
                "Oferujemy żwir o różnych frakcjach, co pozwala na..."
            ),
            "",
        )

    def test_accepts_pl_street_address(self):
        addr = "ul. Przemysłowa 12, 05-800 Pruszków"
        self.assertTrue(looks_like_pl_physical_address(addr))
        self.assertEqual(sanitize_export_address(addr), addr)

    def test_extract_from_impressum_block(self):
        text = (
            "MAZUR Sp. z o.o.\n"
            "ul. Budowlana 5, 05-120 Legionowo\n"
            "tel. 22 123 45 67"
        )
        self.assertEqual(
            extract_pl_address_from_text(text),
            "ul. Budowlana 5, 05-120 Legionowo",
        )

    def test_junk_company_names(self):
        self.assertTrue(is_pl_junk_company_name("Biuro obsługi klienta"))
        self.assertTrue(is_pl_junk_company_name("Artykuły sezonowe"))
        self.assertTrue(is_pl_seo_title("Fugi do kostki brukowej i płyt Warszawa"))

    def test_serper_organic_has_no_address(self):
        self.assertEqual(
            serper_discovery_address(
                bucket="organic",
                item={
                    "snippet": "W naszym asortymencie znajdziecie Państwo wysokiej jakości...",
                    "address": "",
                },
            ),
            "",
        )

    def test_serper_places_address(self):
        self.assertEqual(
            serper_discovery_address(
                bucket="places",
                item={"address": "ul. Testowa 1, 00-001 Warszawa"},
            ),
            "ul. Testowa 1, 00-001 Warszawa",
        )


if __name__ == "__main__":
    unittest.main()
