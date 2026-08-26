# -*- coding: utf-8 -*-
import unittest

import pl_materialy_scraper as scraper


class TestRelaxedContactRegex(unittest.TestCase):
    def setUp(self):
        scraper.set_relaxed_contact_regex(True)

    def tearDown(self):
        scraper.set_relaxed_contact_regex(False)

    def test_pl_mobile_and_landline(self):
        text = "Kontakt: 32 256 08 38 oraz +48 662 268 043 biuro@firma.pl"
        phones = scraper._find_phones_in_text_regex(text)
        emails = scraper._find_emails_in_text_regex(text)
        self.assertTrue(any("662" in p or "256" in p for p in phones), phones)
        self.assertIn("biuro@firma.pl", emails)

    def test_malpa_deobfuscation(self):
        text = "napisz: biuro (małpa) sklep.pl"
        emails = scraper._find_emails_in_text_regex(text)
        self.assertTrue(any("biuro@" in e for e in emails), emails)

    def test_strict_mode_skips_bare_pl_when_not_relaxed(self):
        scraper.set_relaxed_contact_regex(False)
        # Stary regex jest DE-centric (+49/0) — goły PL mobile często odpada.
        text = "tel 662268043"
        phones_strict = scraper._find_phones_in_text_regex(text)
        scraper.set_relaxed_contact_regex(True)
        phones_relaxed = scraper._find_phones_in_text_regex(text)
        self.assertGreaterEqual(len(phones_relaxed), len(phones_strict))


if __name__ == "__main__":
    unittest.main()
