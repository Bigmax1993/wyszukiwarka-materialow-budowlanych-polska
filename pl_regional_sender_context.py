# -*- coding: utf-8 -*-
"""Kontekst nadawcy maili PL — firma budowlana średniego rozmiaru per województwo discovery."""
from __future__ import annotations

from pl_wojewodztwo_keywords import WOJEWODZTWO_CONFIG, _normalize_wojewodztwo_key

# Województwa z dużymi ośrodkami — ten sam szablon maila co w mniejszych miastach regionu.
MAJOR_CITY_WOJEWODZTWO_KEYS: frozenset[str] = frozenset(WOJEWODZTWO_CONFIG.keys())


def resolve_discovery_wojewodztwo(contact_info: dict | None, *, fallback: str = "") -> str:
    """Województwo z discovery (discovery_bundesland) lub z wiersza kontaktu."""
    info = contact_info or {}
    for key in ("discovery_bundesland", "bundesland", "wojewodztwo"):
        raw = str(info.get(key) or "").strip()
        if not raw:
            continue
        normalized = _normalize_wojewodztwo_key(raw)
        if normalized in WOJEWODZTWO_CONFIG:
            return normalized
    fb = _normalize_wojewodztwo_key(fallback)
    return fb if fb in WOJEWODZTWO_CONFIG else (fallback or "").strip()


def wojewodztwo_primary_city_pl(wojewodztwo_key: str) -> str:
    key = _normalize_wojewodztwo_key(wojewodztwo_key)
    cfg = WOJEWODZTWO_CONFIG.get(key) or {}
    cities = cfg.get("cities") or ()
    return str(cities[0]) if cities else key


def wojewodztwo_cities_pl(wojewodztwo_key: str, *, limit: int = 5) -> tuple[str, ...]:
    key = _normalize_wojewodztwo_key(wojewodztwo_key)
    cfg = WOJEWODZTWO_CONFIG.get(key) or {}
    cities = tuple(str(c) for c in (cfg.get("cities") or ()))
    return cities[:limit] if limit > 0 else cities


def wojewodztwo_region_label_pl(wojewodztwo_key: str) -> str:
    """Etykieta regionu po polsku do promptu Claude."""
    key = _normalize_wojewodztwo_key(wojewodztwo_key)
    city = wojewodztwo_primary_city_pl(key)
    if key in WOJEWODZTWO_CONFIG:
        return f"{city} (woj. {key})"
    return wojewodztwo_key or "Polska"


def major_city_examples_pl(wojewodztwo_key: str) -> str:
    """Przykładowe duże miasta w województwie — do promptu Claude."""
    key = _normalize_wojewodztwo_key(wojewodztwo_key)
    cities = wojewodztwo_cities_pl(key, limit=3)
    if not cities:
        return ""
    return ", ".join(cities)


def build_regional_sender_instructions_pl(
    wojewodztwo_key: str,
    *,
    sender_name: str,
    sender_phone: str,
    construction_project_block: str = "",
) -> str:
    """
    Instrukcje dla Claude: wybór realnej średniej firmy budowlanej z regionu
    i wzmianka o aktualnej dużej budowie w tym regionie (także w dużych miastach).
    """
    key = _normalize_wojewodztwo_key(wojewodztwo_key)
    region = (
        wojewodztwo_region_label_pl(key)
        if key in WOJEWODZTWO_CONFIG
        else (wojewodztwo_key or "Polska")
    )
    cities = ", ".join(wojewodztwo_cities_pl(key, limit=6)) or region
    major_examples = major_city_examples_pl(key)
    is_major_hub = key in MAJOR_CITY_WOJEWODZTWO_KEYS
    name = (sender_name or "Maksym Swinczak").strip()
    phone = (sender_phone or "516513965").strip()
    project_section = (
        f"\n\n{construction_project_block.strip()}\n"
        if (construction_project_block or "").strip()
        else ""
    )
    major_city_note = ""
    if is_major_hub and major_examples:
        major_city_note = (
            f"\n• Ta reguła obowiązuje JEDNAKOWO dla dużych miast ({major_examples}) "
            f"i mniejszych miejscowości województwa — zmieniają się tylko lokalna firma-nadawca "
            f"oraz konkretny obiekt budowy z bazy (inny adres)."
        )

    return f"""REGION DISCOVERY (obowiązkowy kontekst)
Województwo / region: {region}
Klucz wojewodztwo: {key or "(nieznane)"}
Główne miasta regionu: {cities}

JEDNAKOWY SZABLON LISTA — DLA WSZYSTKICH MIAST (dużych i regionalnych)
• Struktura listu jednakowa: lokalna firma budowlana średniego rozmiaru + realny obiekt z bloku «OBIEKT BUDOWY» + prośba o cennik.
• W dużych ośrodkach wojewódzkich (Warszawa, Kraków, Wrocław, Gdańsk, Poznań, Katowice itd.) NIE zmieniaj formatu — tylko inna lokalna firma i inny adres placu budowy.{major_city_note}

NADAWCA — ŚREDNIA LOKALNA FIRMA BUDOWLANA (miasto / województwo discovery)
• Wybierz REALNĄ, ISTNIEJĄCĄ polską firmę budowlaną / deweloperską / wykonawczą ŚREDNIEGO rozmiaru, działającą w tym regionie discovery (także w dużym mieście województwa).
  Firma MUSI być prawdziwa (KRS / CEIDG / publiczna strona / znana lokalnie) — NIE wymyślaj nazw typu „Budownictwo X Sp. z o.o.”, „Firma Budowlana XYZ”, „Local Build” itd.
  Średni rozmiar = lokalny / regionalny deweloper lub wykonawca (sp. z o.o., S.A. lokalna), NIE największy krajowy holding
  (nie Dom Development, Robyg, Echo Investment, Budimex, Skanska, Murapol, Atal, Develia, Archicom itd.) i nie jednoosobowa „garażowa” firma.
• Użyj pełnej, poprawnej nazwy prawnej firmy (np. z formy „Sp. z o.o.” / „S.A.”), jeśli jest powszechnie znana.
• Firma ma być typowym lokalnym graczem dla tego miasta / regionu — nie „ogólnopolska korporacja”.
• Przedstaw się jako {name} — menedżer działu sprzedaży wybranej REALNEJ firmy.
• W liście jasno nazwij tę firmę i jej rolę (budowa obiektów mieszkaniowych, komercyjnych lub przemysłowych w tym mieście / regionie).
• Obiekt budowy bierz WYŁĄCZNIE z bloku «OBIEKT BUDOWY» poniżej — to realna, publiczna inwestycja; nie wymyślaj innych budów ani adresów.
{project_section}
PODPIS (dodaj na końcu body):
Z poważaniem,
{name}
Menedżer działu sprzedaży
[pełna PRAWDZIWA nazwa wybranej firmy — bez fikcyjnych nazw]
[strona firmy, jeśli znana]
Tel.: {phone}"""
