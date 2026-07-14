# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from https_website_guard import (  # noqa: E402
    SKIPPED_INSECURE_HTTP_REASON,
    annotate_insecure_website_rows,
    is_explicit_http_website,
    is_secure_https_website,
    row_has_insecure_website_status,
    website_https_and_http_urls,
)


class HttpsWebsiteGuardTests(unittest.TestCase):
    def test_website_urls_for_host(self):
        https_url, http_url = website_https_and_http_urls("http://www.example.pl/kontakt")
        self.assertEqual(https_url, "https://example.pl")
        self.assertEqual(http_url, "http://example.pl")

    def test_explicit_http_rejected_without_probe(self):
        secure, reason = is_secure_https_website("http://alfa-norma.com.pl")
        self.assertFalse(secure)
        self.assertEqual(reason, "explicit_http_url")

    @patch("https_website_guard.requests.head")
    def test_valid_https_accepted(self, mock_head):
        response = MagicMock()
        response.url = "https://budmat.pl/"
        mock_head.return_value = response
        secure, reason = is_secure_https_website("https://budmat.pl")
        self.assertTrue(secure)
        self.assertEqual(reason, "ok")

    def test_bare_domain_probed(self):
        self.assertEqual(
            website_https_and_http_urls("alfa-norma.com.pl")[0],
            "https://alfa-norma.com.pl",
        )

    @patch("https_website_guard._http_site_responds", return_value=True)
    @patch("https_website_guard.requests.get")
    @patch("https_website_guard.requests.head")
    def test_ssl_error_with_working_http_rejected(
        self, mock_head, mock_get, _mock_http_ok
    ):
        mock_head.side_effect = SSLError("certificate verify failed")
        mock_get.side_effect = SSLError("certificate verify failed")
        secure, reason = is_secure_https_website("alfa-norma.com.pl", cache={})
        self.assertFalse(secure)
        self.assertEqual(reason, "http_only_no_tls")

    @patch("https_website_guard.requests.head")
    def test_redirect_to_http_rejected(self, mock_head):
        response = MagicMock()
        response.url = "http://example.pl/"
        mock_head.return_value = response
        secure, reason = is_secure_https_website("https://example.pl")
        self.assertFalse(secure)
        self.assertEqual(reason, "redirect_to_http")

    def test_row_insecure_by_status(self):
        row = {"email_status": SKIPPED_INSECURE_HTTP_REASON, "www": "https://x.pl"}
        self.assertTrue(row_has_insecure_website_status(row))

    def test_row_secure_without_status(self):
        row = {"www": "https://x.pl", "verification_reason": "ok"}
        self.assertFalse(row_has_insecure_website_status(row))

    @patch("https_website_guard.is_secure_https_website", return_value=(False, "http_only_no_tls"))
    def test_annotate_marks_insecure_rows(self, _mock_probe):
        rows = [{"nazwa": "Alfa", "www": "http://alfa-norma.com.pl"}]
        out, marked = annotate_insecure_website_rows(rows, {})
        self.assertEqual(marked, 1)
        self.assertEqual(out[0]["email_status"], SKIPPED_INSECURE_HTTP_REASON)
        self.assertEqual(out[0]["verification_reason"], "http_only_no_tls")


from requests.exceptions import SSLError  # noqa: E402


if __name__ == "__main__":
    unittest.main()
