# -*- coding: utf-8 -*-
"""Prompty Claude — kampania UA: hurtownie materiałów budowlanych."""
from __future__ import annotations

import re

from pl_campaign_keyword_profile import (
    SERPER_TEMPLATE_PATTERNS,
    gu_required_keywords_sample,
    large_company_markers_sample,
    negative_keywords_sample,
    retail_chain_keywords_sample,
    retail_context_keywords_sample,
    small_company_markers_sample,
)

_REQUIRED_MATERIALS = (
    "cement, piasek, żwir, cegła, bloczek, pustak, beton, stal zbrojeniowa, "
    "styropian, wełna mineralna, płytki, płyta gipsowa, dachówka, drewno konstrukcyjne"
)
PAGE_VERIFY_MAX_CHARS = 18000
CONTACT_EXTRACT_MAX_CHARS = 16000
_CONTACT_EXTRACT_TEXT_PRIORITY = (
    "контакт",
    "kontakt",
    "contact",
    "mailto",
    "@",
    "тел",
    "телефон",
    "phone",
    "email",
    "e-mail",
    "адреса",
)
_PAGE_VERIFY_TEXT_PRIORITY = (
    "hurtownia materiałów budowlanych",
    "materiały budowlane",
    "budowlane",
    "hurtownia",
    "hurt",
    "sprzedaż hurtowa",
    "ceny hurtowe",
    "skład budowlany",
    "dla firm",
    "asortyment",
    "katalog",
    "cennik",
    "oferta",
    "dostawa",
    "cement",
    "piasek",
    "cegła",
    "styropian",
    "płytki",
)


def prioritize_page_text_for_verify(
    page_text: str,
    *,
    max_chars: int = PAGE_VERIFY_MAX_CHARS,
    priority_keywords: tuple[str, ...] | None = None,
) -> str:
    keys = priority_keywords or _PAGE_VERIFY_TEXT_PRIORITY
    raw = (page_text or "").strip()
    if len(raw) <= max_chars:
        return raw
    if "=== http" in raw:
        sections = re.split(r"(?=\n=== https?://)", "\n" + raw)
        sections = [s.strip() for s in sections if s.strip()]
        priority_sec: list[str] = []
        other_sec: list[str] = []
        for sec in sections:
            low = sec.lower()
            if any(k in low for k in keys):
                priority_sec.append(sec)
            else:
                other_sec.append(sec)
        merged = "\n\n".join(priority_sec + other_sec)
    else:
        lines = [ln.strip() for ln in re.split(r"[\n\r]+", raw) if ln.strip()]
        if not lines:
            return raw[:max_chars]
        priority: list[str] = []
        other: list[str] = []
        for ln in lines:
            low = ln.lower()
            if any(k in low for k in keys):
                priority.append(ln)
            else:
                other.append(ln)
        merged = " ".join(priority + other)
    if len(merged) <= max_chars:
        return merged
    return merged[: max_chars - 3] + "..."


def build_page_verify_prompt(
    company_name: str,
    website: str,
    page_text: str,
    *,
    max_chars: int = PAGE_VERIFY_MAX_CHARS,
    serper_blob: str = "",
    pages_crawled: int = 0,
) -> str:
    from claude_page_text import (
        build_automatic_evidence_excerpt,
        build_claude_context_header,
        extract_crawl_section_urls,
    )

    raw = page_text or ""
    priority_urls = extract_crawl_section_urls(raw)
    header = build_claude_context_header(
        company_name,
        website,
        serper_blob=serper_blob,
        pages_crawled=pages_crawled or max(raw.count("=== http"), 1 if raw else 0),
        priority_urls=priority_urls,
    )
    evidence = build_automatic_evidence_excerpt(raw)
    snippet = prioritize_page_text_for_verify(raw, max_chars=max_chars)
    supplier_kw = ", ".join(gu_required_keywords_sample())
    material_kw = ", ".join(retail_context_keywords_sample())
    category_kw = ", ".join(retail_chain_keywords_sample())
    neg_kw = ", ".join(negative_keywords_sample())
    small_kw = ", ".join(small_company_markers_sample())
    large_kw = ", ".join(large_company_markers_sample())
    return f"""ROLA
Jesteś analitykiem B2B. Szukasz WYŁĄCZNIE hurtowni / składów hurtowych materiałów budowlanych działających w POLSCE.

CEL (is_gu=true) — muszą być spełnione JEDNOCZEŚNIE:
1) Sprzedaż HURTOWA materiałów budowlanych (hurt, hurtownia, sprzedaż/ceny hurtowe, skład budowlany, oferta dla firm/wykonawców).
2) Asortyment materiałów budowlanych (np. {_REQUIRED_MATERIALS}).
3) Działalność w Polsce (polski adres, domena .pl, województwo, numer +48, NIP).

NIE CEL (is_gu=false):
• Sklepy WYŁĄCZNIE detaliczne / markety DIY bez oferty hurtowej → primary_role="Sklep detaliczny"
• Wykonawcy i usługi budowlane bez sprzedaży materiałów → primary_role="Wykonawca bez sprzedaży"
• Biura projektowe/architektoniczne, wykończenia wnętrz, remonty pod klucz
• Portale, media, urzędy, banki, ogłoszenia (OLX/Allegro)
• Firmy spoza Polski (choćby sprzedawały hurtowo) → dodaj "poza polską" do matched_negative_keywords

ZADANIE
Przeczytaj wyciąg ze strony (wszystkie podstrony oznaczone «=== URL ===»).
Czy to hurtownia / skład hurtowy materiałów budowlanych w Polsce? Odpowiedz TYLKO w formacie JSON — bez markdown.

CO JEST DOWODEM (is_gu=true)
• Fraza roli hurtowej: hurt, hurtownia, sprzedaż hurtowa, ceny hurtowe, skład budowlany, dla firm/wykonawców
• Realna oferta handlowa: asortyment, katalog, cennik, dostawa
• Kategorie materiałów: {_REQUIRED_MATERIALS}

ODRZUĆ (is_gu=false / has_retail_context=false)
• Brak jakiejkolwiek oferty hurtowej (tylko detal) — to nie jest hurtownia
• Wykonawca/usługa bez sprzedaży materiałów, biuro architektoniczne, wykończenia, remonty pod klucz
• Media, portale, urzędy, banki, ogłoszenia, giełdy używanych
• Firma bez działalności w Polsce

POLA JSON (te same klucze dla zgodności z pipeline)
• is_gu = true TYLKO jeśli hurtownia/skład hurtowy materiałów budowlanych w Polsce (pkt 1–3 spełnione)
• has_retail_context = true jeśli jest realna oferta handlowa materiałów (asortyment, katalog, cennik, hurt)
• matched_gu_keywords = dopasowane frazy roli hurtowej ze strony
• matched_retail_keywords = dopasowane frazy oferty/asortymentu
• matched_chains = kategorie materiałów z tekstu (cement, piasek, …) — tylko jeśli wymienione
• matched_negative_keywords = trafienia negatywne; dodaj "poza polską" gdy firma nie działa w Polsce
• is_small_firm = mała/regionalna firma (nie duża sieć / międzynarodowy koncern)
• primary_role = jedna z: Hurtownia, Skład budowlany, Dystrybutor hurtowy, Sklep detaliczny, Producent, Wykonawca bez sprzedaży, Biuro architektoniczne, Media, Portal, Urząd, Bank, Ogłoszenie, Inne
• reason = krótkie uzasadnienie po polsku

MAŁE OZNAKI: {small_kw}
DUŻE OZNAKI (is_small_firm=false): {large_kw}

SŁOWA KLUCZOWE HURTOWNI: {supplier_kw}
KONTEKST MATERIAŁÓW: {material_kw}
KATEGORIE: {category_kw}
NEGATYW: {neg_kw}

SCHEMA JSON
{{
  "matched_gu_keywords": [],
  "matched_retail_keywords": [],
  "matched_chains": [],
  "matched_negative_keywords": [],
  "is_gu": false,
  "has_retail_context": false,
  "is_small_firm": false,
  "primary_role": "",
  "reason": ""
}}

KONTEKST
{header}

AUTODOWODY
{evidence}

WYCIĄG ZE STRONY
{snippet or "(pusto)"}
"""


def build_row_cleanup_prompt(
    *,
    company: str,
    address: str,
    phone: str,
    email: str,
    website: str,
    states: str,
    handelsketten: str = "",
    url: str = "",
) -> str:
    return f"""РОЛЬ
Ти готуєш рядок Excel для B2B-бази постачальників будматеріалів в Polskі.
Відповідай ЛИШЕ JSON.

СХЕМА
{{"company_name_clean":"","address":"","phone":"","website":"","bundesland":"","handelsketten":"","url":""}}

ПРАВИЛА
• company_name_clean — офіційна назва + форма (ТОВ, ПП, ФОП) або ""
• address — адреса в Polskі або ""
• phone — один номер UA (+380 або 0…) або ""
• website — https://domain (корінь) або ""
• bundesland — один з: [{states}] або ""
• handelsketten — категорії матеріалів (cement, piasek, …) через кому або ""
• url — як website

ВХІД
company={company!r}
address={address!r}
phone={phone!r}
email={email!r}
website={website!r}
handelsketten={handelsketten!r}
url={url!r}
"""


def build_personalized_inquiry_email_prompt_pl(
    *,
    company_name: str,
    website: str = "",
    wojewodztwo: str = "",
    address: str = "",
    materials: str = "",
    page_snippet: str = "",
    style_hint: str = "",
) -> str:
    from pl_materialy_inquiry_email_pl import (
        build_inquiry_sender_brief_pl,
        build_inquiry_signature_pl,
        build_sender_contact_line_pl,
        inquiry_phone,
    )

    snippet = (page_snippet or "").strip()
    if len(snippet) > 3500:
        snippet = snippet[:3497] + "..."
    style = (style_hint or "profesjonalny, naturalny styl B2B, bez szablonowych fraz").strip()
    mats = materials or "materiały budowlane (szeroki asortyment)"
    sender_brief = build_inquiry_sender_brief_pl()
    sender_contact = build_sender_contact_line_pl()
    signature_block = build_inquiry_signature_pl()
    phone = inquiry_phone()
    return f"""ROLA
Jesteś autorem listów B2B po polsku. Piszesz UNIKALNY list do KONKRETNEJ hurtowni / dostawcy materiałów budowlanych w Polsce.
Każdy list ma różnić się sformułowaniami — nie kopiuj jednego szablonu.

NADAWCA (kontekst, nie wymyślaj innych faktów)
{sender_brief}
Kontakt: {sender_contact or "kupujący materiałów budowlanych"}

ODBIORCA
Nazwa: {company_name}
Strona: {website or "(brak)"}
Województwo: {wojewodztwo or "(nieznane)"}
Adres: {address or "(brak)"}
Kategorie materiałów (z bazy): {mats}

FRAGMENT STRONY / OPIS (użyj do personalizacji — wspomnij asortyment, region, specjalizację):
{snippet or "(brak — zwróć się ogólnie do dostawcy materiałów budowlanych)"}

ZADANIE
Napisz w pełni spersonalizowany list ZAPYTANIA o współpracę / ceny hurtowe / cennik.
• Język: WYŁĄCZNIE polski.
• Zwrot: „Szanowni Państwo” lub spersonalizowany do {company_name}.
• Koniecznie wspomnij coś konkretnego o tej firmie (asortyment, region, typ działalności).
• Poproś o cennik lub kontakt do działu hurtu / sprzedaży.
• Nie wymyślaj cen, rabatów, terminów dostawy.
• Styl: {style}
• Długość treści: 120–220 słów (bez podpisu).

ZAKAZANE
• Numery ukraińskie (+380) i niemieckie (+49)
• Jedyny telefon kontaktowy w podpisie: {phone}
• Słowa: gratis, promocja, pilnie, kliknij, rabat 50%
• Ten sam tekst dla różnych firm
• Załączniki / pliki / linki do pobrania
• HTML, markdown

PODPIS (dodaj na końcu body BEZ zmian):
{signature_block}

WYJŚCIE — TYLKO JSON (bez markdown):
{{"subject":"...","body":"..."}}

subject: unikalny, do 78 znaków, po polsku, z nazwą lub specjalizacją firmy
body: pełny list gotowy do wysyłki (plain text), łącznie z podpisem powyżej
"""


def build_custom_email_prompt_uk(
    draft: str,
    company_name: str,
    *,
    city_name: str = "",
    delivery_address: str = "",
) -> str:
    ctx_city = f"Регіон: {city_name}. " if city_name else ""
    ctx_addr = f"Адреса доставки (без змін): {delivery_address}. " if delivery_address else ""
    return f"""РОЛЬ
Ти редактор B2B-листів polskською. Мінімально адаптуй шаблон під конкретну фірму.

ОДЕРЖУВАЧ
{company_name}
{ctx_city}{ctx_addr}

ЗАВДАННЯ
Адаптуй шаблон (1–2 речення контексту про фірму). Збережи ВСІ факти: обсяги, адреси, телефони, підпис.

ЗАБОРОНЕНО
• Вигадані ціни
• gratis, акція, терміново
• Зміна підпису

ВИХІД (лише JSON)
{{"subject":"...","body":"..."}}

ШАБЛОН
{draft}
"""
