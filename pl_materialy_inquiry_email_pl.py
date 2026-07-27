# -*- coding: utf-8 -*-
"""
Tekst maila — zapytanie ofertowe do hurtowni materiałów budowlanych (polski).
Domyślny telefon kontaktowy: 516513965 (+48).
"""
from __future__ import annotations

import re

_UA_PHONE_INLINE_RE = re.compile(
    r"(?:\+380|00380)\s*[\d\s()./-]{5,}\d",
    re.IGNORECASE,
)
_FOREIGN_TEL_LINE_RE = re.compile(
    r"^\s*(?:tel\.?|telefon|phone)\s*[.:]?\s*(?:\+380|00380|\+49|0049)[\d\s()./-]*\s*$",
    re.IGNORECASE | re.MULTILINE,
)
_LEGACY_BRANDING_RE = re.compile(
    r"\b(?:mfg|moderner\s*fliesen\w*|fliesenboden|gmbh)\b",
    re.IGNORECASE,
)


def is_foreign_campaign_phone(phone: str) -> bool:
    raw = (phone or "").strip()
    if not raw:
        return False
    low = raw.lower().replace(" ", "")
    if low.startswith("+380") or low.startswith("00380"):
        return True
    if low.startswith("+49") or low.startswith("0049"):
        return True
    digits = re.sub(r"\D", "", raw)
    if digits.startswith("380") and len(digits) >= 11:
        return True
    return digits.startswith("49") and len(digits) >= 11


def strip_foreign_phones_from_text(text: str) -> str:
    if not text:
        return ""
    out = _FOREIGN_TEL_LINE_RE.sub("", text)
    out = _UA_PHONE_INLINE_RE.sub("", out)
    out = re.sub(r"\b(?:tel\.?|telefon|phone)\s*[.:]?\s*(?=\s|$)", "", out, flags=re.IGNORECASE)
    out = re.sub(r"[ \t]+,", ",", out)
    out = re.sub(r",\s*,", ",", out)
    out = re.sub(r"\n{3,}", "\n\n", out)
    return out.strip(" ,\n")


def strip_legacy_branding(text: str) -> str:
    if not text:
        return ""
    out = strip_foreign_phones_from_text(text)
    out = _LEGACY_BRANDING_RE.sub("", out)
    out = re.sub(r"\s+", " ", out).strip(" ,;-")
    return out


def _clean_sender_display_name(raw: str) -> str:
    text = (raw or "").strip()
    if not text:
        return ""
    text = re.sub(r"\b(tel|telefon|phone)\b.*$", "", text, flags=re.IGNORECASE).strip()
    text = strip_foreign_phones_from_text(text)
    text = re.sub(r"https?://\S+|\bwww\.\S+|\S+@\S+", "", text, flags=re.IGNORECASE).strip()
    text = re.sub(r"\+?\d[\d\s()./-]{5,}\d", "", text).strip()
    text = strip_legacy_branding(text)
    return re.sub(r"\s+", " ", text).strip(" ,;-")


DEFAULT_INQUIRY_SENDER_NAME_PL = "Maksym Swinczak"
DEFAULT_INQUIRY_PHONE_PL = "516513965"
DEFAULT_INQUIRY_WEBSITE_PL = "https://swinczakdata.pl"


def inquiry_sender_name() -> str:
    from scraper_env import get_mail_sender_name, normalize_mail_sender_name

    cleaned = _clean_sender_display_name(get_mail_sender_name() or "")
    cleaned = normalize_mail_sender_name(cleaned)
    if not cleaned or any(x in cleaned.lower() for x in ("свінчак", "свинчак", "mfg", "fliesen")):
        return DEFAULT_INQUIRY_SENDER_NAME_PL
    return cleaned


def inquiry_company_name() -> str:
    from scraper_env import get_env_value

    return strip_legacy_branding(get_env_value("INQUIRY_COMPANY_NAME").strip())


def inquiry_phone() -> str:
    from scraper_env import get_env_value

    phone = get_env_value("INQUIRY_PHONE").strip()
    if phone and not is_foreign_campaign_phone(phone):
        return phone
    return DEFAULT_INQUIRY_PHONE_PL


def inquiry_website() -> str:
    from scraper_env import get_env_value

    web = get_env_value("INQUIRY_WEBSITE").strip()
    return web or DEFAULT_INQUIRY_WEBSITE_PL


def build_inquiry_signature_pl() -> str:
    lines = ["Z poważaniem,", ""]
    name = inquiry_sender_name()
    if name:
        lines.append(name)
    company = inquiry_company_name()
    if company:
        lines.extend(["", company])
    web = inquiry_website()
    if web:
        lines.extend(["", web])
    phone = inquiry_phone()
    lines.extend(["", f"Tel.: {phone}"])
    return "\n".join(lines).strip()


def body_has_inquiry_signature(body: str) -> bool:
    low = (body or "").lower()
    if "z poważaniem" not in low:
        return False
    name = inquiry_sender_name().strip()
    if not name:
        return False
    first = name.split()[0].lower()
    phone = re.sub(r"\D", "", inquiry_phone())
    tail = low[-500:]
    tail_digits = re.sub(r"\D", "", (body or "")[-500:])
    return first in tail and phone in tail_digits


def dedupe_inquiry_signature(body: str) -> str:
    text = (body or "").strip()
    if not text:
        return text
    name = inquiry_sender_name().strip()
    if not name:
        return text
    search_from = max(0, len(text) - 800)
    region = text[search_from:]
    matches = list(re.finditer(r"z poważaniem", region, flags=re.IGNORECASE))
    if len(matches) < 2:
        return text
    main = text[: search_from + matches[0].start()].rstrip()
    last_sig = text[search_from + matches[-1].start() :].strip()
    return f"{main}\n\n{last_sig}".strip()


def ensure_inquiry_signature(body: str) -> str:
    text = dedupe_inquiry_signature((body or "").strip())
    if body_has_inquiry_signature(text):
        return text
    signature = build_inquiry_signature_pl()
    if not signature:
        return text
    return text.rstrip() + "\n\n" + signature


_SALUTATION_PREFIX_RE = re.compile(
    r"^(Szanowni Państwo,?)\s*",
    re.IGNORECASE,
)
_SIGNATURE_MARKER_RE = re.compile(r"\b(Z poważaniem,?)\b", re.IGNORECASE)
_TEL_LINE_RE = re.compile(
    r"\b(?:Tel\.?|Telefon):?\s*(?:\+48)?[\d\s()./-]{7,}",
    re.IGNORECASE,
)
_WEB_INLINE_RE = re.compile(r"(?:https?://\S+|www\.\S+)", re.IGNORECASE)


def format_inquiry_email_body_pl(body: str) -> str:
    """Układa treść maila: akapity, odstępy między blokami, czytelny podpis."""
    if not body:
        return ""
    text = body.replace("\r\n", "\n").replace("\r", "\n").strip()
    lines = [re.sub(r"[ \t]+", " ", ln).strip() for ln in text.split("\n")]
    text = "\n".join(lines)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()

    if "\n" not in text:
        text = _format_dense_inquiry_body_pl(text)
    else:
        text = _ensure_salutation_spacing_pl(text)
        text = _ensure_signature_spacing_pl(text)
        text = _normalize_signature_lines_pl(text)

    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return text


def _ensure_salutation_spacing_pl(text: str) -> str:
    match = _SALUTATION_PREFIX_RE.match(text)
    if not match:
        return text
    salutation = match.group(1).rstrip(",") + ","
    rest = text[match.end() :].lstrip()
    if rest.startswith("\n\n"):
        return text
    if rest.startswith("\n"):
        return f"{salutation}\n{rest.lstrip()}"
    return f"{salutation}\n\n{rest}"


def _ensure_signature_spacing_pl(text: str) -> str:
    match = _SIGNATURE_MARKER_RE.search(text)
    if not match:
        return text
    before = text[: match.start()].rstrip()
    after = text[match.start() :].lstrip()
    if before.endswith("\n\n") or not before:
        return text
    return f"{before}\n\n{after}"


def _format_dense_inquiry_body_pl(text: str) -> str:
    match = _SIGNATURE_MARKER_RE.search(text)
    if match:
        main = text[: match.start()].strip()
        signature = _normalize_signature_lines_pl(text[match.start() :].strip())
        main = _ensure_salutation_spacing_pl(main)
        return f"{main.rstrip()}\n\n{signature}"
    return _ensure_salutation_spacing_pl(text)


def _normalize_signature_lines_pl(text: str) -> str:
    match = _SIGNATURE_MARKER_RE.search(text)
    if not match:
        return text
    before = text[: match.start()].rstrip()
    marker = match.group(1)
    if not marker.endswith(","):
        marker = marker + ","
    rest = text[match.end() :].strip()
    if not rest:
        signature = marker
    else:
        tel_match = _TEL_LINE_RE.search(rest)
        tel = tel_match.group(0).strip() if tel_match else ""
        if tel_match:
            rest = (rest[: tel_match.start()] + rest[tel_match.end() :]).strip(" ,;")

        web_match = _WEB_INLINE_RE.search(rest)
        web = web_match.group(0).strip() if web_match else ""
        if web_match:
            rest = (rest[: web_match.start()] + rest[web_match.end() :]).strip(" ,;")

        name_lines = [ln.strip(" ,;") for ln in rest.splitlines() if ln.strip(" ,;")]
        parts = [marker]
        parts.extend(name_lines)
        if web:
            parts.append(web)
        if tel:
            parts.append(tel if tel.lower().startswith("tel") else f"Tel.: {tel}")
        signature = "\n".join(parts)
    if before:
        return f"{before}\n\n{signature}"
    return signature


def ensure_inquiry_contact_in_body(body: str) -> str:
    """
    Uzupełnia brakujący telefon PL w podpisie.
    Nie dokleja statycznego podpisu, jeśli Claude już dodał blok «Z poważaniem».
    """
    text = strip_legacy_branding_preserve_layout(
        strip_foreign_phones_from_text((body or "").strip())
    )
    if not text:
        return build_inquiry_signature_pl()
    phone = inquiry_phone()
    if phone in text:
        return text
    if re.search(r"z\s+powa[zż]aniem", text, flags=re.IGNORECASE):
        return f"{text.rstrip()}\nTel.: {phone}"
    return f"{text.rstrip()}\n\n{build_inquiry_signature_pl()}"


def strip_legacy_branding_preserve_layout(text: str) -> str:
    if not text:
        return ""
    out = strip_foreign_phones_from_text(text)
    out = _LEGACY_BRANDING_RE.sub("", out)
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in out.splitlines()]
    out = "\n".join(lines).strip()
    return re.sub(r"\n{3,}", "\n\n", out)


def build_inquiry_sender_brief_pl() -> str:
    company = inquiry_company_name()
    who = company if company else "Analityk rynku materiałów budowlanych (B2B)"
    return (
        f"{who} — zbieram informacje o ofertach hurtowych w ramach analizy rynku "
        "i benchmarku dostawców (cement, piasek, żwir, bloczki, stal, styropian, "
        "wełna, płyty GK, dachówki, zaprawy itd.). Szczegóły: https://swinczakdata.pl/dla-hurtowni.html"
    )


def build_sender_contact_line_pl() -> str:
    parts: list[str] = []
    name = inquiry_sender_name()
    if name:
        parts.append(name)
    company = inquiry_company_name()
    if company:
        parts.append(company)
    web = inquiry_website()
    if web:
        parts.append(web)
    parts.append(f"Tel. {inquiry_phone()}")
    return strip_legacy_branding(", ".join(parts))


def build_fixed_material_inquiry_pl() -> str:
    intro = (
        "zwracam się w ramach analizy rynku materiałów budowlanych (benchmark B2B). "
        "Proszę o informację o możliwości dostawy hurtowej w Państwa regionie."
    )
    if inquiry_company_name():
        intro = (
            f"zwracam się w imieniu {inquiry_company_name()} w ramach analizy rynku "
            "materiałów budowlanych. Poszukujemy ofert hurtowych do porównania dostawców."
        )
    return f"""Szanowni Państwo,

{intro}

Interesuje nas szeroki asortyment: cement, piasek, żwir, kruszywa, cegła, bloczki, stal zbrojeniowa, styropian, wełna mineralna, płyty gipsowe, pokrycia dachowe, zaprawy, farby i produkty pokrewne. Zależą nam na cenach hurtowych netto, dostępności magazynowej oraz możliwości dostawy.

Więcej o współpracy B2B: https://swinczakdata.pl/dla-hurtowni.html

Prosimy o przesłanie aktualnego cennika lub wskazanie osoby kontaktowej z działu sprzedaży / hurtu.

Dziękujemy za współpracę.

{build_inquiry_signature_pl()}"""


FIXED_MATERIAL_INQUIRY_PL = build_fixed_material_inquiry_pl()


def inquiry_email_signature_pl() -> str:
    return build_inquiry_signature_pl()


def inquiry_sender_brief_pl() -> str:
    return build_inquiry_sender_brief_pl()


INQUIRY_EMAIL_SIGNATURE_PL = build_inquiry_signature_pl()
INQUIRY_SENDER_BRIEF_PL = build_inquiry_sender_brief_pl()

# Aliasy kompatybilności ze scraperem (fork UA)
strip_de_campaign_branding = strip_legacy_branding
strip_german_phones_from_text = strip_foreign_phones_from_text
