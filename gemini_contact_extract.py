# -*- coding: utf-8 -*-
"""
Ekstrakcja kontaktów po parse HTML: Gemini z tekstu strony, potem regex w scraperze.
Wyłącz ENABLE_GEMINI_CONTACT_EXTRACTION → sam regex (fallback).
"""
from __future__ import annotations

import hashlib
import json
import re
from typing import Callable

from commercial_contact_filter import filter_commercial_emails

_JSON_BLOCK_RE = re.compile(r"\{.*\}", re.DOTALL)
_PHONE_SKIP_DIGIT_PREFIXES = ("19", "20")


def build_gemini_contact_extract_prompt(
    page_url: str,
    page_text: str,
    *,
    website: str = "",
    max_chars: int = 10_000,
) -> str:
    snippet = re.sub(r"\s+", " ", (page_text or "").strip())
    if len(snippet) > max_chars:
        snippet = snippet[: max_chars - 3] + "..."
    site = website or page_url or "unbekannt"
    return (
        "Du extrahierst Kontaktdaten aus einem deutschen Webseiten-Auszug "
        "(Bauunternehmen / Generalunternehmer, Impressum oder Kontakt).\n\n"
        "REGELN:\n"
        "- NUR Daten, die im Text vorkommen — nichts erfinden.\n"
        "- E-Mails: echte Firmenadressen mit @; keine Platzhalter, keine "
        "noreply/no-reply, keine Bild-/CSS-Dateien.\n"
        "- Telefon: deutsche Rufnummern (+49 oder 0…); keine Jahreszahlen, "
        "keine Fax wenn nur Tel. gesucht (Fax optional weglassen).\n"
        "- Firma: offizieller Firmenname mit Rechtsform (GmbH, UG, AG, …) "
        "des Seitenbetreibers; leer bei Katalogen, Portalen, PDF-Titeln, "
        "Nachrichten, reinen Städtenamen.\n"
        "- Bei Obfuskation (at), [at], (punkt) — normalisiere zu echter E-Mail.\n\n"
        f"Webseite: {site}\n"
        f"Seite: {page_url or site}\n\n"
        "Antwort NUR als JSON (kein Markdown):\n"
        "{\n"
        '  "company_name": "Muster Bau GmbH",\n'
        '  "emails": ["info@muster-bau.de"],\n'
        '  "phones": ["+49 231 1234567"],\n'
        '  "reason": "kurz DE max 1 Satz"\n'
        "}\n\n"
        f"Auszug:\n{snippet or '(leer)'}"
    )


def _normalize_email(raw: str) -> str:
    low = (raw or "").strip().lower()
    low = re.sub(r"^mailto:\s*", "", low)
    low = low.split("?")[0].split("#")[0].strip(".,;:()[]{}<>\"'`")
    if "@" not in low:
        return ""
    local, _, domain = low.partition("@")
    local, domain = local.strip(), domain.strip().rstrip(".")
    if not local or not domain or "." not in domain:
        return ""
    return f"{local}@{domain}"


def normalize_phone_contact(raw: str) -> str:
    normalized = " ".join((raw or "").split()).strip(".,;:()[]")
    if not normalized:
        return ""
    digits = re.sub(r"\D", "", normalized)
    if len(digits) < 7:
        return ""
    if len(digits) in (4, 8) and digits.startswith(_PHONE_SKIP_DIGIT_PREFIXES):
        return ""
    if digits.startswith("49") and len(digits) < 10:
        return ""
    if digits.startswith("0049"):
        digits = "49" + digits[4:]
    if digits.startswith("49") and not normalized.startswith("+"):
        rest = digits[2:]
        if len(rest) >= 9:
            normalized = f"+49 {rest[:3]} {rest[3:]}".strip()
    return normalized


def parse_gemini_contact_extract_response(text: str) -> dict:
    raw = (text or "").strip()
    match = _JSON_BLOCK_RE.search(raw)
    payload = match.group(0) if match else raw
    data = json.loads(payload)
    if not isinstance(data, dict):
        raise ValueError("Gemini contact extract: not a JSON object")

    emails: list[str] = []
    for item in data.get("emails") or []:
        norm = _normalize_email(str(item))
        if norm and norm not in emails:
            emails.append(norm)
    emails = filter_commercial_emails(emails)

    phones: list[str] = []
    for item in data.get("phones") or []:
        norm = normalize_phone_contact(str(item))
        if norm and norm not in phones:
            phones.append(norm)

    company_name = " ".join(str(data.get("company_name") or "").split()).strip()
    reason = str(data.get("reason") or "").strip()

    company_names = [company_name] if company_name else []
    return {
        "company_name": company_name,
        "company_names": company_names,
        "emails": emails,
        "phones": phones,
        "reason": reason,
    }


def gemini_extract_contacts_from_page(
    page_text: str,
    page_url: str,
    logger,
    cache: dict | None,
    *,
    gemini_generate_text: Callable,
    api_key: str,
    website: str = "",
    max_input_chars: int = 10_000,
    is_rate_limited: Callable[[dict | None], bool] | None = None,
    on_step: Callable[[str], None] | None = None,
) -> dict:
    """Live Gemini: jeden Aufruf na stronę → firma, e-maile, telefony."""
    empty = {
        "company_name": "",
        "company_names": [],
        "emails": [],
        "phones": [],
        "reason": "",
    }
    if not (page_text or "").strip():
        return empty
    if is_rate_limited and is_rate_limited(cache):
        return empty
    if not api_key:
        return empty

    snippet = re.sub(r"\s+", " ", page_text.strip())
    digest = hashlib.sha256(
        f"{page_url}|{website}|{snippet[:1200]}".encode("utf-8")
    ).hexdigest()[:24]
    cache_bucket = (cache or {}).setdefault("gemini_contact_extract", {})
    if digest in cache_bucket:
        cached = cache_bucket[digest]
        return cached if isinstance(cached, dict) else empty

    prompt = build_gemini_contact_extract_prompt(
        page_url,
        page_text,
        website=website,
        max_chars=max_input_chars,
    )
    try:
        response, used_model = gemini_generate_text(prompt, logger, api_key, cache=cache)
        parsed = parse_gemini_contact_extract_response(response)
        if on_step:
            on_step(f"Gemini Kontakte: {used_model} ({len(parsed['emails'])} mail, {len(parsed['phones'])} tel)")
        cache_bucket[digest] = parsed
        return parsed
    except Exception as exc:
        logger.warning("Gemini Kontakt-Extraktion fehlgeschlagen (%s): %s", page_url, exc)
        cache_bucket[digest] = empty
        return empty
