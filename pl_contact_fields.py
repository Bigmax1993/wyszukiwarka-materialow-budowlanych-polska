# -*- coding: utf-8 -*-
"""
Walidacja i czyszczenie nazwy firmy oraz adresu — kampania PL materiały budowlane.
"""
from __future__ import annotations

import re

_PL_POSTAL_RE = re.compile(r"\b\d{2}-\d{3}\b")
_PL_STREET_RE = re.compile(
    r"\b(?:ul\.?|ulica|al\.?|aleja|aleje|pl\.?|plac|os\.?|osiedle|"
    r"skwer|rondo|bulw\.?|bulwar)\b",
    re.IGNORECASE,
)
_PL_ADDRESS_LINE_RE = re.compile(
    r"(?:"
    r"(?:ul\.?|ulica|al\.?|aleja|pl\.?|plac|os\.?|osiedle)\s+[A-Za-zÀ-ž0-9\.\-\s]{2,60},?\s*\d{2}-\d{3}\s+[A-Za-zÀ-ž\-]+"
    r"|"
    r"\d{2}-\d{3}\s+[A-Za-zÀ-ž\-]+(?:,?\s+(?:ul\.?|ulica|al\.?|aleja|pl\.?|plac)\s+[A-Za-zÀ-ž0-9\.\-\s]{2,60})?"
    r")",
    re.IGNORECASE,
)

_MARKETING_TEXT_MARKERS = (
    "w naszym asortymencie",
    "w ofercie",
    "oferujemy",
    "znajdziecie państwo",
    "znajdziecie panstwo",
    "zapraszamy",
    "nasza oferta",
    "nasz asortyment",
    "sprzedajemy",
    "proponujemy",
    "dysponujemy",
    "zapewniamy",
    "specjalizujemy się",
    "specjalizujemy sie",
    "jest producentem",
    "jesteśmy producentem",
    "jestesmy producentem",
    "firma „",
    'firma "',
    "jako producent",
    "jako dystrybutor",
    "wysokiej jakości",
    "wysokiej jakosci",
    "solidne materiały",
    "solidne materialy",
    "w atrakcyjnych cenach",
    "zapraszamy do",
    "zachęcamy",
    "zachecamy",
    "…",
    "...",
)

_PL_JUNK_NAME_MARKERS = (
    "biuro obsługi",
    "biuro obslugi",
    "obsługi klienta",
    "obslugi klienta",
    "artykuły sezonowe",
    "artykuly sezonowe",
    " poleca",
    "polecamy",
    "fugi do ",
    "płytki ",
    "plytki ",
    "bloczki ",
    "cegła ",
    "cegla ",
    "styropianu, materiałów",
    "styropianu, materialow",
    "hurtownia styropianu",
    "materiałów budowlanych",
    "materialow budowlanych",
    "sklep internetowy",
    "strona główna",
    "strona glowna",
    "kontakt z nami",
    "o nas",
    "regulamin",
    "polityka prywatności",
    "polityka prywatnosci",
    "newsletter",
    "blog",
    "aktualności",
    "aktualnosci",
    "promocje",
    "wyprzedaż",
    "wyprzedaz",
)

_PL_SEO_TITLE_MARKERS = (
    "hurtownia ",
    "skład budowlany",
    "sklad budowlany",
    "materiały budowlane",
    "materialy budowlane",
    "producent ",
    "dystrybutor ",
    " ceny ",
    " cennik",
    " warszawa",
    " kraków",
    " krakow",
    " wrocław",
    " wroclaw",
    " gdańsk",
    " gdansk",
    " poznań",
    " poznan",
    " łódź",
    " lodz",
)


def looks_like_marketing_text(text: str) -> bool:
    low = " ".join((text or "").split()).lower()
    if not low:
        return False
    if len(low) > 140 and not _PL_POSTAL_RE.search(low):
        return True
    return any(m in low for m in _MARKETING_TEXT_MARKERS)


def looks_like_pl_physical_address(text: str) -> bool:
    raw = " ".join((text or "").split()).strip()
    if not raw or len(raw) < 8:
        return False
    if looks_like_marketing_text(raw):
        return False
    has_postal = bool(_PL_POSTAL_RE.search(raw))
    has_street = bool(_PL_STREET_RE.search(raw))
    if has_postal and has_street:
        return len(raw) <= 180
    if has_postal and re.search(r"\d+[a-zA-Z]?", raw):
        return len(raw) <= 160
    return False


def extract_pl_address_from_text(text: str) -> str:
    """Wyciąga pierwszy sensowny adres PL z bloku tekstu (Impressum/kontakt)."""
    if not (text or "").strip():
        return ""
    for chunk in re.split(r"[\n\r;|]+", text):
        line = " ".join(chunk.split()).strip(" ,;-")
        if looks_like_pl_physical_address(line):
            return line[:180]
    match = _PL_ADDRESS_LINE_RE.search(text)
    if match:
        candidate = " ".join(match.group(0).split()).strip(" ,;-")
        if looks_like_pl_physical_address(candidate):
            return candidate[:180]
    return ""


def sanitize_export_address(raw: str, *, fallback_text: str = "") -> str:
    """Adres do Excela — odrzuca snippet Google / marketing."""
    text = " ".join((raw or "").split()).strip()
    if looks_like_pl_physical_address(text):
        return text[:180]
    if text and not looks_like_marketing_text(text):
        extracted = extract_pl_address_from_text(text)
        if extracted:
            return extracted
    if fallback_text:
        extracted = extract_pl_address_from_text(fallback_text)
        if extracted:
            return extracted
    return ""


def is_pl_junk_company_name(name: str) -> bool:
    low = " ".join((name or "").split()).lower()
    if not low:
        return True
    if any(m in low for m in _PL_JUNK_NAME_MARKERS):
        return True
    if low in ("kontakt", "o nas", "start", "home", "strona główna", "strona glowna"):
        return True
    return False


def is_pl_seo_title(name: str) -> bool:
    """Tytuł wyniku Google / nagłówek SEO — nie nazwa prawna."""
    text = " ".join((name or "").split()).strip()
    if not text:
        return False
    low = text.lower()
    if is_pl_junk_company_name(text):
        return True
    if any(m in low for m in _PL_SEO_TITLE_MARKERS) and len(text.split()) >= 4:
        return True
    if text.count(",") >= 2:
        return True
    if ":" in text and len(text.split()) >= 3:
        return True
    if len(text) > 55 and not re.search(
        r"\b(?:sp\.?\s*z\.?\s*o\.?\s*o\.?|sp\.?\s*j\.?|sp\.?\s*k\.?|s\.?\s*a\.?)\b",
        text,
        re.IGNORECASE,
    ):
        return True
    return False


def serper_discovery_address(*, bucket: str, item: dict) -> str:
    """Adres z Serper — tylko Places API; organic snippet nie jest adresem."""
    if bucket != "places":
        return ""
    raw = (item.get("address") or "").strip()
    return sanitize_export_address(raw)
