# -*- coding: utf-8 -*-
"""Weryfikacja HTTPS — strony HTTP-only / bez certyfikatu nie przechodzą dalej."""
from __future__ import annotations

import logging
from urllib.parse import urlparse

import requests
from requests.exceptions import SSLError

SKIPPED_INSECURE_HTTP_REASON = "skipped_insecure_http"

_DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
}


def _host_from_url(url: str) -> str:
    text = (url or "").strip()
    if not text:
        return ""
    if not text.startswith(("http://", "https://")):
        text = f"https://{text.lstrip('/')}"
    try:
        host = (urlparse(text).netloc or "").lower()
    except Exception:
        return ""
    if host.startswith("www."):
        host = host[4:]
    return host


def website_https_and_http_urls(url: str) -> tuple[str, str]:
    """Kanoniczne https:// i http:// dla tej samej domeny."""
    host = _host_from_url(url)
    if not host:
        return "", ""
    return f"https://{host}", f"http://{host}"


def is_explicit_http_website(url: str) -> bool:
    return (url or "").strip().lower().startswith("http://")


def _final_url_is_https(response: requests.Response) -> bool:
    final = (getattr(response, "url", "") or "").strip().lower()
    return final.startswith("https://")


def _probe_url(url: str, *, timeout: int, method: str = "HEAD") -> tuple[bool, str]:
    if not url:
        return False, "empty_url"
    fn = requests.head if method == "HEAD" else requests.get
    try:
        response = fn(
            url,
            timeout=timeout,
            allow_redirects=True,
            headers=_DEFAULT_HEADERS,
        )
        if _final_url_is_https(response):
            return True, "ok"
        if (getattr(response, "url", "") or "").lower().startswith("http://"):
            return False, "redirect_to_http"
        return False, "non_https_final_url"
    except SSLError:
        return False, "ssl_error"
    except requests.RequestException as exc:
        low = str(exc).lower()
        if "ssl" in low or "certificate" in low:
            return False, "ssl_error"
        return False, "connection_error"


def _http_site_responds(http_url: str, *, timeout: int) -> bool:
    try:
        response = requests.get(
            http_url,
            timeout=timeout,
            allow_redirects=True,
            headers=_DEFAULT_HEADERS,
        )
        return response.status_code < 500
    except requests.RequestException:
        return False


def is_secure_https_website(
    url: str,
    *,
    logger: logging.Logger | None = None,
    timeout: int = 15,
    cache: dict | None = None,
) -> tuple[bool, str]:
    """
    True = witryna dostępna po HTTPS z poprawnym TLS (lub redirect na https://).
    False = http:// w źródle, błąd SSL, redirect w dół na http:// lub tylko HTTP.
    """
    raw = (url or "").strip()
    if not raw:
        return True, ""

    https_url, http_url = website_https_and_http_urls(raw)
    if not https_url:
        return True, ""

    cache_key = _host_from_url(raw)
    if cache is not None and cache_key:
        bucket = cache.setdefault("https_probe", {})
        cached = bucket.get(cache_key)
        if isinstance(cached, dict) and "secure" in cached:
            return bool(cached["secure"]), str(cached.get("reason") or "")

    if is_explicit_http_website(raw):
        reason = "explicit_http_url"
        _store_probe(cache, cache_key, False, reason, logger)
        return False, reason

    for method in ("HEAD", "GET"):
        ok, detail = _probe_url(https_url, timeout=timeout, method=method)
        if ok:
            _store_probe(cache, cache_key, True, detail, logger)
            return True, detail
        if detail == "redirect_to_http":
            _store_probe(cache, cache_key, False, detail, logger)
            return False, detail
        if detail == "ssl_error":
            if http_url and _http_site_responds(http_url, timeout=timeout):
                reason = "http_only_no_tls"
                _store_probe(cache, cache_key, False, reason, logger)
                return False, reason
            _store_probe(cache, cache_key, False, detail, logger)
            return False, detail

    _store_probe(cache, cache_key, False, detail, logger)
    return False, detail


def _store_probe(
    cache: dict | None,
    cache_key: str,
    secure: bool,
    reason: str,
    logger: logging.Logger | None,
) -> None:
    if cache is not None and cache_key:
        cache.setdefault("https_probe", {})[cache_key] = {
            "secure": secure,
            "reason": reason,
        }
    if logger and not secure:
        logger.info("HTTPS odrzucono %s: %s", cache_key, reason)


def row_website_url(row: dict) -> str:
    for key in ("official_website", "www", "url", "Strona www"):
        val = (row.get(key) or "").strip()
        if val:
            return val
    return ""


_INSECURE_HTTPS_REASONS = frozenset(
    {
        "explicit_http_url",
        "ssl_error",
        "http_only_no_tls",
        "redirect_to_http",
        "non_https_final_url",
        "https_unavailable",
        "connection_error",
    }
)


def row_has_insecure_website_status(row: dict) -> bool:
    """Szybki filtr Excela / cache — bez ponownego sondowania HTTP."""
    if (row.get("email_status") or "").strip() == SKIPPED_INSECURE_HTTP_REASON:
        return True
    return (row.get("verification_reason") or "").strip() in _INSECURE_HTTPS_REASONS


def is_row_insecure_website(row: dict, *, cache: dict | None = None) -> bool:
    if row_has_insecure_website_status(row):
        return True
    website = row_website_url(row)
    if not website:
        return False
    secure, reason = is_secure_https_website(website, cache=cache)
    if not secure:
        return True
    return False
