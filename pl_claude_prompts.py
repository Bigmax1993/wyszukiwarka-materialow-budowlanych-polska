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

_REQUIRED_MATERIALS = "cement, piasek, щебінь, цегла, блок, арматура, утеплювач, плитка, гіпсокартон"
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
    "materiały budowlane",
    "budowlane",
    "каталог",
    "асортимент",
    "продукція",
    "прайс",
    "ціни",
    "опт",
    "склад",
    "доставка",
    "цемент",
    "пісок",
    "щебінь",
    "цегла",
    "утеплювач",
    "плитка",
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
    return f"""РОЛЬ
Ти — аналітик B2B для пошуку постачальників будівельних матеріалів в Polskі.
Ціль: гуртові склади, магазини будматеріалів, виробники та дистриб'ютори.
НЕ ціль: портали новин, держустанови, чисті підрядники без продажу матеріалів, оголошення OLX.

ЗАВДАННЯ
Прочитай витяг сайту (усі підсторінки, позначені «=== URL ===»).
Чи це комерційний постачальник будматеріалів? Відповідай ЛИШЕ JSON — без markdown.

ЩО ВВАЖАЄТЬСЯ ДОКАЗОМ
• Продаж/опт будматеріалів, склад, доставка, каталог, прайс
• Згадка категорій: {_REQUIRED_MATERIALS}
• Роль: постачальник, виробник, дистриб'ютор, будмаркет, будівельна база

ВІДХИЛИТИ (is_gu=false / has_retail_context=false)
• Biuro architektoniczne, дизайн інтер'єру, ремонт квартир без продажу матеріалів
• Новини, медіа, держоргани, банки, вакансії без комерційної пропозиції
• OLX/оголошення б/у без стабільного бізнесу постачальника

ПОЛЯ JSON (ті самі ключі для сумісності з pipeline)
• is_gu = true якщо це постачальник/виробник/склад будматеріалів
• has_retail_context = true якщо є комерційна пропозиція матеріалів (каталог, асортимент, ціни, опт)
• matched_chains = категорії матеріалів з тексту (cement, piasek, …) — лише якщо згадані
• is_small_firm = регіональна/мала фірма (не велика міжнародна мережа)

МАЛІ ОЗНАКИ: {small_kw}
ВЕЛИКІ ОЗНАКИ (is_small_firm=false): {large_kw}

КЛЮЧОВІ СЛОВА ПОСТАЧАЛЬНИКА: {supplier_kw}
КОНТЕКСТ МАТЕРІАЛІВ: {material_kw}
КАТЕГОРІЇ: {category_kw}
НЕГАТИВ: {neg_kw}

СХЕМА JSON
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

КОНТЕКСТ
{header}

АВТОДОКАЗИ
{evidence}

ВИТЯГ САЙТУ
{snippet or "(порожньо)"}
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
