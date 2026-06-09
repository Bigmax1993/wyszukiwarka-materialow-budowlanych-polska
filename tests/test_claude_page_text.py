# -*- coding: utf-8 -*-
import unittest

from claude_page_text import (
    build_automatic_evidence_excerpt,
    build_claude_context_header,
    format_crawl_text_for_claude,
    sort_crawl_urls_for_claude,
)
from website_full_crawl import WebsiteCrawlResult
from claude_prompts import PAGE_VERIFY_MAX_CHARS, build_page_verify_prompt


class ClaudePageTextTest(unittest.TestCase):
    def test_sort_verify_puts_referenzen_first(self):
        urls = [
            "https://firma.de/impressum",
            "https://firma.de/referenzen",
            "https://firma.de/kontakt",
        ]
        out = sort_crawl_urls_for_claude(urls, purpose="verify")
        self.assertEqual(out[0], "https://firma.de/referenzen")

    def test_sort_contact_puts_impressum_first(self):
        urls = [
            "https://firma.de/referenzen",
            "https://firma.de/impressum",
        ]
        out = sort_crawl_urls_for_claude(urls, purpose="contact")
        self.assertEqual(out[0], "https://firma.de/impressum")

    def test_format_crawl_truncates_per_section(self):
        result = WebsiteCrawlResult(
            pages={
                "https://firma.de/impressum": {
                    "page_text": "x" * 3000,
                }
            },
            urls_visited=["https://firma.de/impressum"],
        )
        text = format_crawl_text_for_claude(
            result, purpose="contact", per_section_max_chars=500
        )
        self.assertIn("=== https://firma.de/impressum ===", text)
        body = text.split("\n", 1)[1]
        self.assertLessEqual(len(body), 503)
        self.assertTrue(body.endswith("..."))

    def test_evidence_excerpt_finds_retail_line(self):
        page = (
            "=== https://firma.de/karriere ===\n"
            "Auftraggeber Netto Marken-Discount im Einzelhandel"
        )
        out = build_automatic_evidence_excerpt(page)
        self.assertIn("Netto", out)

    def test_verify_prompt_includes_serper_and_evidence(self):
        page = (
            "=== https://firma.de/referenzen ===\n"
            "Neubau Rewe Markt in Dresden"
        )
        p = build_page_verify_prompt(
            "Test GmbH",
            "https://firma.de",
            page,
            serper_blob="Generalunternehmer Filialbau",
            pages_crawled=1,
        )
        self.assertIn("SERPER-KONTEXT", p)
        self.assertIn("AUTOMATISCHE DOWODY", p)
        self.assertIn("Rewe", p)
        self.assertEqual(PAGE_VERIFY_MAX_CHARS, 18000)

    def test_context_header(self):
        h = build_claude_context_header(
            "Firma GmbH",
            "https://firma.de",
            serper_blob="GU Leipzig",
            pages_crawled=5,
        )
        self.assertIn("Firma GmbH", h)
        self.assertIn("GU Leipzig", h)
        self.assertIn("5", h)


if __name__ == "__main__":
    unittest.main()
