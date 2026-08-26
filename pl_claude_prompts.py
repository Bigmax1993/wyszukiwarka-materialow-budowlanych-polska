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
    return f"""ROLA
Jesteś QA danych przed eksportem Excel „Kontakte” (PL materiały budowlane B2B).
Twój JSON ląduje 1:1 w kolumnach arkusza. Błędy = złe maile B2B — zero tolerancji.
Odpowiedz WYŁĄCZNIE jednym obiektem JSON — bez Markdown, bez komentarzy.

GRUPA DOCELOWA (tylko te firmy mogą mieć nazwę)
Hurtownie / składy / dystrybutorzy / producenci materiałów budowlanych w Polsce
(cement, kruszywa, styropian, wełna, chemia budowlana, drewno konstrukcyjne, armatura, stal zbrojeniowa, dachówka, płyty, sucha zabudowa).
NIE: portale ogłoszeniowe, Facebook/Instagram, Allegro, OLX, Lento, Panorama Firm, Wikipedia, banki, urzędy, szkoły, blogi, drogerie, meble, interior design, czysty wykonawca bez handlu materiałami.

SCHEMA (exakt — wszystkie klucze; puste stringi dozwolone)
{{"company_name_clean":"","address":"","phone":"","website":"","bundesland":"","handelsketten":"","url":""}}

═══ company_name_clean — KILLER-REGELN (najwyższy priorytet) ═══
ERLAUBT: oficjalna nazwa firmy + forma prawna w JEDNEJ linii
(Sp. z o.o., sp.j., S.A., sp.k., sp.p., P.H.U., P.P.H., firma jednoosobowa z nazwiskiem).
OK: „Lubar Sp. z o.o.”, „CHEMIA BUDOWLANA Kowalski Sp. j.”, „MB Kruszywa Sp. z o.o.”
NICHT OK / SOFORT company_name_clean="":
• sam URL / domena / ścieżka (https://…, www., .pl/)
• E-mail, emoji, slogan marketingowy, „Biuro obsługi”, „Kontakt”, „Sklep online”
• tytuł SEO / H1 katalogu („Styropian tanio Warszawa”, „Cement i piasek”)
• portal: facebook.com, lento.pl, olx.pl, allegro.pl, wikipedia, yellow pages
• nazwa miasta / województwa jako „firma”
• nagłówek produktu („Kantówki”, „Piasek rzeczny przesiewany”) bez firmy
• „tak”/„nie”/statusy pipeline (sent, skipped_institution, no_suitable_email)
Jeśli wejście to URL — wyprowadź nazwę TYLKO gdy da się ją pewnie odczytać z kontekstu Impressum/danych; NIGDY nie wymyślaj. Niepewność → "".

═══ Excel — sztywny format kolumn ═══
• address → wyłącznie fizyczny adres PL: „ul. Nazwa Nr, XX-XXX Miasto” albo ""; NIGDY województwo, NIGDY kategorie, NIGDY telefon/email
• phone → DOKŁADNIE jeden numer PL (+48… lub 9 cyfr); bez „Tel./Fax”, bez drugiego numeru; inaczej ""
• website → https://domena.pl (ROOT, bez /sklep /kontakt /pdf); inaczej ""
• url → identycznie jak website (https://domena.pl)
• bundesland → GENAU jedna wartość z: [{states}] — inaczej ""
• handelsketten → małe litery, przecinek+spacja, TYLKO kategorie materiałów
  (np. cement, piasek, styropian, wełna, chemia budowlana, drewno, armatura, kruszywa)
  NIGDY „tak”/„nie”, NIGDY statusy, NIGDY URL
• email_nur_info: NIE wstawiaj do JSON — tylko do sprawdzenia spójności z domeną

NEGATYWNE PRZYKŁADY
name="https://facebook.com/…" → company_name_clean="", website="", url=""
name="https://sklep.lubar.pl" + realna firma znana → company_name_clean="Lubar …", website="https://lubar.pl", url="https://lubar.pl"
address="mazowieckie" → address="", bundesland="mazowieckie"
phone="Tel +48 22 111, Fax +48 22 222" → phone="+4822111…" (tylko pierwszy)
handelsketten="styropian, wełna tak" → handelsketten="styropian, wełna"

WEJŚCIE (oczyść / uzupełnij / wyzeruj śmieci)
name={company}
address={address}
phone={phone}
website={website}
url={url}
handelsketten={handelsketten}
email_nur_info={email}
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
    discovery_wojewodztwo: str = "",
    construction_project=None,
) -> str:
    from pl_materialy_inquiry_email_pl import (
        inquiry_phone,
        inquiry_sender_name,
    )
    from pl_regional_sender_context import (
        build_regional_sender_instructions_pl,
        resolve_discovery_wojewodztwo,
    )
    from pl_regional_construction_refs import (
        build_construction_project_prompt_block_pl,
        pick_construction_project,
    )

    snippet = (page_snippet or "").strip()
    if len(snippet) > 3500:
        snippet = snippet[:3497] + "..."
    style = (style_hint or "profesjonalny, naturalny styl B2B, bez szablonowych fraz").strip()
    mats = materials or "materiały budowlane (szeroki asortyment)"
    region_key = resolve_discovery_wojewodztwo(
        {"bundesland": wojewodztwo, "discovery_bundesland": discovery_wojewodztwo},
        fallback=wojewodztwo or discovery_wojewodztwo,
    )
    project = construction_project or pick_construction_project(
        region_key, seed=company_name or wojewodztwo or discovery_wojewodztwo
    )
    project_block = build_construction_project_prompt_block_pl(project)
    regional_sender = build_regional_sender_instructions_pl(
        region_key,
        sender_name=inquiry_sender_name(),
        sender_phone=inquiry_phone(),
        construction_project_block=project_block,
    )
    return f"""ROLA
Jesteś autorem listów B2B po polsku. Piszesz UNIKALNY list do KONKRETNEJ firmy-dostawcy materiałów budowlanych w Polsce.
Każdy list ma różnić się sformułowaniami — nie kopiuj jednego szablonu dla wszystkich.

{regional_sender}

ODBIORCA (dostawca materiałów budowlanych)
Nazwa: {company_name}
Strona: {website or "(brak)"}
Województwo dostawcy: {wojewodztwo or "(nieznane)"}
Adres: {address or "(brak)"}
Kategorie materiałów (z bazy): {mats}

FRAGMENT STRONY / OPIS (użyj do personalizacji — wspomnij ich asortyment, region, specjalizację):
{snippet or "(brak — zwróć się ogólnie do dostawcy materiałów budowlanych)"}

ZADANIE
Napisz w pełni spersonalizowany list ZAPYTANIA o współpracę / ceny hurtowe / cennik.
• Język: WYŁĄCZNIE polski.
• Zwrot: „Szanowni Państwo” lub spersonalizowany do {company_name}.
• Koniecznie wspomnij coś konkretnego o tej firmie-dostawcy (asortyment, region, typ działalności).
• Koniecznie wspomnij wybraną lokalną firmę budowlaną — MUSI to być PRAWDZIWA, istniejąca firma z regionu (pełna nazwa w treści i w podpisie). Nie wymyślaj fikcyjnych nazw.
• Koniecznie wspomnij WYŁĄCZNIE obiekt z bloku «OBIEKT BUDOWY» — to realna inwestycja z publicznej bazy (pełna nazwa + adres dosłownie). Nie wymyślaj innych budów.
• Jednakowy format dla dużych miast (Warszawa, Kraków, Wrocław…) i mniejszych miejscowości (np. Głogów).
• Poproś o cennik lub kontakt do działu hurtu / sprzedaży.
• Nie wymyślaj cen, rabatów, terminów dostawy, których nie ma we wejściu.
• Styl: {style}
• Długość treści: 140–240 słów (bez podpisu).

FORMAT LISTU (body — plain text z pustymi liniami między blokami)
Obowiązkowa struktura — używaj \\n\\n między blokami:
1) Zwrot (jeden wiersz), np. «Szanowni Państwo,»
2) Pusta linia
3) 2–3 akapity głównego tekstu (każdy akapit — osobny blok przez \\n\\n)
4) Pusta linia
5) «Z poważaniem,» (osobny wiersz)
6) Imię oraz stanowisko / PRAWDZIWA firma (osobny wiersz)
7) Tel.: {inquiry_phone()} (osobny wiersz)

Przykład body w JSON (z \\n oraz \\n\\n) — nazwa firmy w przykładzie jest ILUSTRACYJNA; w realnym liście wstaw prawdziwą firmę z regionu:
"body":"Szanowni Państwo,\\n\\nPierwszy akapit listu.\\n\\nDrugi akapit z prośbą o cennik.\\n\\nZ poważaniem,\\n{inquiry_sender_name()}\\nMenedżer działu sprzedaży\\n[prawdziwa lokalna firma budowlana]\\nTel.: {inquiry_phone()}"

ZAKAZANE
• Numery ukraińskie (+380) i niemieckie (+49) — zabronione; jedyny telefon kontaktowy: {inquiry_phone()} (w podpisie)
• Słowa: gratis, promocja, pilnie, kliknij, rabat 50%
• Ten sam tekst dla różnych firm
• Zabronione dodawanie załączników / plików / linków do pobrania
• HTML, markdown
• Przedstawianie się jako dostawca lub anonimowy „kupujący” bez nazwy firmy budowlanej
• Fikcyjne / wymyślone nazwy firm-nadawców (np. „Budownictwo Region Sp. z o.o.”, „Firma Budowlana XYZ”, „Local Build”)
• Wymyślone lub zmienione adresy placu budowy (inna ulica, numer, miasto)
• Inny obiekt budowy niż ten z bloku «OBIEKT BUDOWY» — nawet jeśli znasz podobną inwestycję w okolicy

WYJŚCIE — TYLKO JSON (bez markdown):
{{"subject":"...","body":"..."}}

subject: unikalny, do 78 znaków, po polsku; wspomnij typ obiektu budowy lub region
body: pełny list gotowy do wysyłki (plain text z akapitami przez \\n\\n), łącznie z podpisem (imię, stanowisko, firma, tel.)
"""


def build_reminder_email_prompt_pl(
    *,
    company_name: str,
    original_subject: str = "",
    sent_date: str = "",
    original_body_excerpt: str = "",
    reminder_number: int = 1,
) -> str:
    excerpt = (original_body_excerpt or "").strip()
    if len(excerpt) > 1200:
        excerpt = excerpt[:1197] + "..."
    tone = (
        "delikatne, uprzejme przypomnienie (pierwsze)"
        if reminder_number < 2
        else "stanowcze, ale kulturalne drugie przypomnienie"
    )
    date_line = f"Data pierwszego maila: {sent_date}." if sent_date else ""
    subj_line = f"Temat pierwszego maila: {original_subject}." if original_subject else ""
    return f"""ROLA
Piszesz krótki, NATURALNY list-przypomnienie po polsku — jak żywa osoba z branży budowlanej, nie bot.
To follow-up B2B do dostawcy materiałów budowlanych, który nie odpowiedział na zapytanie.

ODBIORCA
Firma: {company_name}
{date_line}
{subj_line}

KONTEKST (pierwszy list — NIE wklejaj go ponownie, tylko odwołaj się ogólnie):
{excerpt or "(brak treści — odwołaj się do zapytania o materiały budowlane)"}

ZADANIE
Napisz WYŁĄCZNIE tekst przypomnienia (bez podpisu, bez cytatu poprzedniego listu).
• Ton: {tone}
• 2–3 krótkie akapity oddzielone pustą linią (\\n\\n)
• Zacznij od „Dzień dobry,” lub spersonalizowanego zwrotu do {company_name}
• Naturalny, ludzki język — unikaj szablonowych fraz typu „uprzejmie przypominam o naszym zapytaniu ofertowym z dnia…”
• Krótko wspomnij, że czekasz na odpowiedź / cennik / kontakt — bez nacisku
• 50–110 słów łącznie
• NIE powtarzaj długiej listy produktów z pierwszego listu

ZAKAZANE
• Podpis, imię, telefon, linki, HTML, markdown
• Słowa: pilnie, ostatnia szansa, natychmiast, gratis, promocja
• Jedna ściana tekstu bez akapitów

WYJŚCIE — TYLKO JSON (bez markdown):
{{"intro":"..."}}

intro: tylko tekst przypomnienia (plain text), z akapitami przez pustą linię
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
