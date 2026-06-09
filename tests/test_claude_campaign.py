# -*- coding: utf-8 -*-
"""Testy warstwy Claude (bez live API)."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parent.parent
LIBS = ROOT / "libs"
for p in (str(ROOT), str(LIBS)):
    if p not in sys.path:
        sys.path.insert(0, p)

from claude_row_cleanup import parse_claude_row_cleanup_response


class ClaudeRowCleanupTest(unittest.TestCase):
    def test_parse_cleanup_json(self):
        raw = (
            '{"company_name_clean":"Müller Bau GmbH","address":"Hauptstr. 1, 04109 Leipzig",'
            '"phone":"+49 341 123456","website":"https://mueller-bau.de","bundesland":"Sachsen"}'
        )
        parsed = parse_claude_row_cleanup_response(raw)
        self.assertEqual(parsed["company_name_clean"], "Müller Bau GmbH")
        self.assertEqual(parsed["bundesland"], "Sachsen")


class ClaudePageVerifyIntegrationTest(unittest.TestCase):
    def test_claude_verify_accepts_gu_retail(self):
        from claude_page_verify import claude_verify_company_page

        gemini_json = (
            '{"is_gu": true, "has_retail_context": true, '
            '"primary_role": "Generalunternehmer", '
            '"matched_gu_keywords": ["generalunternehmer"], '
            '"matched_retail_keywords": ["filialbau"], '
            '"matched_chains": ["rewe"], '
            '"matched_negative_keywords": [], '
            '"reason": "GU mit Filialbau"}'
        )
        with patch("claude_page_verify.get_anthropic_api_key", return_value="test-key"):
            with patch(
                "claude_page_verify.claude_generate_text",
                return_value=(gemini_json, "claude-sonnet-test"),
            ):
                result = claude_verify_company_page(
                    "Test Bau GmbH",
                    "https://test-bau.de",
                    "Wir sind Generalunternehmer für Filialbau und Rewe Projekte.",
                    logger=MagicMock(),
                    cache={},
                )
        self.assertIsNotNone(result)
        self.assertTrue(result["verified"])
        self.assertIn("rewe", result["retail_chains"])

    def test_claude_reserve_blocks_api_at_buffer(self):
        from claude_client import (
            CLAUDE_DAILY_LIMIT,
            CLAUDE_DISCOVERY_RESERVE,
            claude_generate_text,
            configure_claude_limits,
            is_claude_limit_reached_today,
        )

        configure_claude_limits(daily_limit=3000, reserve=1000)
        cache = {"claude_daily": {"2099-01-01": CLAUDE_DAILY_LIMIT - CLAUDE_DISCOVERY_RESERVE}}
        with patch("claude_client._campaign_today", return_value="2099-01-01"):
            self.assertTrue(is_claude_limit_reached_today(cache))
            with patch("claude_client.get_anthropic_api_key", return_value="test-key"):
                with self.assertRaises(RuntimeError):
                    claude_generate_text("ping", MagicMock(), cache=cache)

    def test_cleanup_bypasses_daily_limit(self):
        from claude_client import (
            CLAUDE_DAILY_LIMIT,
            CLAUDE_DISCOVERY_RESERVE,
            claude_generate_text,
            configure_claude_limits,
        )

        configure_claude_limits(daily_limit=3000, reserve=1000)
        cache = {"claude_daily": {"2099-01-01": CLAUDE_DAILY_LIMIT}}
        with patch("claude_client._campaign_today", return_value="2099-01-01"):
            with patch("claude_client.get_anthropic_api_key", return_value="test-key"):
                with patch("claude_client.requests.post") as mock_post:
                    mock_post.return_value.status_code = 200
                    mock_post.return_value.json.return_value = {
                        "content": [{"type": "text", "text": '{"company_name_clean":"OK GmbH"}'}]
                    }
                    text, _ = claude_generate_text(
                        "cleanup",
                        MagicMock(),
                        cache=cache,
                        bypass_daily_limit=True,
                    )
        self.assertIn("OK GmbH", text)
        self.assertEqual(cache["claude_daily"]["2099-01-01"], CLAUDE_DAILY_LIMIT)

    def test_wide_email_regex_40_chars(self):
        import de_gu_bauunternehmen_scraper as scraper

        local = "a" * 40
        email = f"{local}@example.de"
        found = scraper._find_emails_in_text_regex(f"Kontakt: {email}")
        self.assertIn(email.lower(), found)


if __name__ == "__main__":
    unittest.main()
