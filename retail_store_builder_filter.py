# -*- coding: utf-8 -*-
"""
Kampania DE: wyłącznie Generalunternehmer (GU), którzy:
- stawiają sklepy / filie (Neubau, Filialbau), lub
- robią przebudowy / modernizacje marketów (Umbau, Revitalisierung).
Nie: sam Ladenbau bez GU, ogólne Bauunternehmen, podwykonawcy, sieci handlowe, urzędy.
"""
from __future__ import annotations

from commercial_contact_filter import (
    is_non_commercial_contact,
    is_valid_commercial_company_contact,
)

# Współdzielone z de_gu_bauunternehmen_scraper.REQUIRE_GENERALUNTERNEHMER
REQUIRE_GENERALUNTERNEHMER = True

REQUIRED_RETAIL_CHAIN_KEYWORDS = (
    "aldi",
    "rewe",
    "edeka",
    "lidl",
    "netto",
    "penny",
)


def detect_required_retail_chains(text: str) -> list[str]:
    """Wymagane sieci: Aldi, Rewe, Edeka, Lidl, Netto, Penny."""
    low = (text or "").lower()
    return [c for c in REQUIRED_RETAIL_CHAIN_KEYWORDS if c in low]


def has_required_retail_chain_mention(text: str) -> bool:
    return bool(detect_required_retail_chains(text))

STRICT_GU_MARKERS = (
    "generalunternehmer",
    "generalunternehmen",
    "generalunternehmerleistung",
    "komplettgeneralunternehmer",
    "komplettgeneralunternehmerleistung",
    "hauptauftragnehmer",
    "totalunternehmer",
    "generalübernehmer",
    "generaluebernehmer",
    "gu-leistung",
    " gu ",
)

NON_GU_ROLE_EXCLUSION_MARKERS = (
    "subunternehmer",
    "nachunternehmer",
    "architekturbüro",
    "architekturbuero",
    "planungsbüro",
    "planungsbuero",
    "projektentwicklung",
    "ingenieurbüro",
    "ingenieurbaero",
    "fachingenieur",
    "projektmanagement ohne bau",
)

RETAIL_OPERATOR_DOMAIN_MARKERS = (
    "shop.rewe",
    "rewe-markt",
    "rewe.de/filial",
    "filialfinder",
    "aldi-sued.de",
    "aldi-nord.de",
    "aldi.de",
    "penny.de",
    "kaufland.de",
    "lidl.de",
    "netto-online.de",
    "edeka.de",
    "rossmann.de",
    "dm.de",
    "tegut.de",
    "norma-online",
)

RETAIL_OPERATOR_PAGE_MARKERS = (
    "öffnungszeiten",
    "oeffnungszeiten",
    "wochenangebot",
    "prospekt",
    "filialfinder",
    "marktsuche",
    "jetzt einkaufen",
    "online bestellen",
    "lebensmittel online",
)

RETAIL_STORE_CONTEXT_MARKERS = (
    "filial",
    "laden",
    " markt",
    "markt ",
    "supermarkt",
    "discounter",
    "einzelhandel",
    "verbrauchermarkt",
    "nahversorger",
    "handelsimmobil",
    "lebensmittelmarkt",
    "food retail",
)

# Neubau / realizacja obiektów handlowych
RETAIL_STORE_BUILD_MARKERS = (
    "filialbau",
    "ladenbau",
    "marktbau",
    "supermarktbau",
    "supermarkt-neubau",
    "supermarktneubau",
    "einzelhandelsbau",
    "handelsbau",
    "filialneubau",
    "filialgebäude",
    "filialgebaude",
    "filialstandort",
    "einzelhandelsimmobilie",
    "handelsimmobilie",
    "handelsimmobilien",
    "handelsprojekt",
    "einzelhandelsprojekt",
    "filialprojekt",
    "discounterbau",
    "marktneubau",
    "markterweiterung",
    "ladenerweiterung",
)

# Przebudowa / modernizacja marketów i filii
RETAIL_STORE_UMBAU_MARKERS = (
    "filialumbau",
    "marktumbau",
    "supermarktumbau",
    "filialmodernisierung",
    "marktmodernisierung",
    "filialrevitalisierung",
    "marktrevitalisierung",
    "filialsanierung",
    "marktsanierung",
    "ladenumbau",
    "komplettumbau",
    "bestandsumbau",
    "filialumbau",
    "umbau supermarkt",
    "umbau discounter",
    "modernisierung supermarkt",
    "modernisierung filiale",
    "revitalisierung filiale",
    "revitalisierung markt",
    "umbau lebensmittelmarkt",
    "erneuerung filiale",
)

GU_BUILDER_MARKERS = (
    "generalunternehmer",
    "generalunternehmen",
    "komplettgeneralunternehmer",
    "hauptauftragnehmer",
    "totalunternehmer",
    "generalübernehmer",
    "generaluebernehmer",
    "gu-leistung",
    " gu ",
    "bauunternehmen",
    "bauunternehmung",
)

FILIALBAU_SPECIALIST_MARKERS = (
    "filialbau",
    "ladenbau",
    "marktbau",
    "supermarktbau",
    "einzelhandelsbau",
    "handelsbau",
    "handelsimmobilien",
)

# Galerie / zdjęcia projektów (bez osobnej sekcji „Portfolio”)
MARKET_PHOTO_GALLERY_MARKERS = (
    "bildergalerie",
    "fotogalerie",
    "projektbilder",
    "bauabbildungen",
    "impressionen",
    "einblicke",
    "foto",
    "fotos",
    "bild ",
    "bilder",
    "abbildung",
    "lightbox",
    "bildergalerie",
    "projektgalerie",
    "baustellenfotos",
    "baustellenbilder",
)

# Opisy projektów bez zakładki „Referenzen”
RETAIL_PROJECT_DESCRIPTION_MARKERS = (
    "projektbeschreibung",
    "projektinfo",
    "objektbeschreibung",
    "leistungsübersicht",
    "leistungsuebersicht",
    "baubeschreibung",
    "projektdetails",
    "errichtet",
    "realisiert",
    "fertiggestellt",
    "wir haben",
    "wir realisieren",
    "unsere leistungen",
)

RETAIL_PROJECT_BUILD_ACTIVITY_MARKERS = (
    "neubau",
    "umbau",
    "errichtung",
    "realisierung",
    "fertigstellung",
    "bauprojekt",
    "erweiterung",
    "neueröffnung",
    "neueroeffnung",
)

RETAIL_IMAGE_FILE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp", ".gif", ".avif")

# Sekcja Referenzen / Portfolio (opcjonalna — wystarczą też zdjęcia/alt marketów)
PORTFOLIO_SECTION_MARKERS = (
    "referenzen",
    "referenzprojekt",
    "referenzprojekte",
    "referenzliste",
    "referenzobjekte",
    "portfolio",
    "projektübersicht",
    "projektuebersicht",
    "projektbeispiele",
    "unsere projekte",
    "bauprojekte",
    "objektübersicht",
    "objektuebersicht",
    "case study",
    "baustellenberichte",
    "realisierungen",
    "projektgalerie",
    "projektliste",
)

# Sieci / obiekty handlowe w portfolio (Pflicht: projekty MARKETÓW)
RETAIL_CHAIN_IN_PORTFOLIO_MARKERS = (
    "aldi nord",
    "aldi süd",
    "aldi sued",
    "aldi",
    "rewe",
    "kaufland",
    "lidl",
    "penny",
    "netto",
    "edeka",
    "norma",
    "tegut",
    "marktkauf",
    "nahkauf",
    "globus",
    "famila",
)

MARKET_PROJECT_IN_PORTFOLIO_MARKERS = (
    "supermarktprojekt",
    "marktprojekt",
    "filialprojekt",
    "einzelhandelsprojekt",
    "discounterprojekt",
    "referenzprojekt supermarkt",
    "referenzprojekt filiale",
    "referenzprojekt markt",
    "portfolio supermarkt",
    "portfolio filiale",
    "portfolio markt",
    "projekte supermarkt",
    "projekte filiale",
    "projekte discounter",
    "projekte einzelhandel",
    "referenz supermarkt",
    "referenz filiale",
    "referenz markt",
    "realisierte filialen",
    "realisierte märkte",
    "realisierte maerkte",
    "filialneubau",
    "marktneubau",
    "filialumbau",
    "marktumbau",
    "supermarktbau",
    "marktbau",
    "lebensmittelmarkt",
    "verbrauchermarkt",
    "nahversorger",
)

MEDIA_PUBLISHER_DOMAIN_MARKERS = (
    "hi-heute.de",
    "funkemedien",
    "verlag",
    "redaktion.",
    "business-news",
    "fachzeitung",
    "fachmedien",
    "presseportal",
    "nachrichten.",
    "news-medien",
    "magazin.",
    "branchennews",
    "branchenportal",
)

MEDIA_PUBLISHER_NAME_MARKERS = (
    "verlag ",
    " verlag",
    "redaktion",
    "fachmedium",
    "fachzeitschrift",
    "nachrichten",
    "news group",
    "business news",
    "business media",
    "pressemitteilung",
    "fachportal",
)

MEDIA_PUBLISHER_URL_PATH_MARKERS = (
    "/news/",
    "/nachrichten/",
    "/artikel/",
    "/newsletter/",
    "/magazin/",
    "/supermarkte_und_discounter",
)

PURE_RENOVATION_WITHOUT_STORE_BUILD = (
    "altbausanierung",
    "wohnsanierung",
    "denkmalsanierung",
    "komplettsanierung wohn",
    "wohnungsbau",
    "wohnungsmodernisierung",
)


def _blob(*parts: str) -> str:
    return " ".join((p or "").strip() for p in parts if (p or "").strip()).lower()


def _has_retail_store_context(low: str) -> bool:
    return any(m in low for m in RETAIL_STORE_CONTEXT_MARKERS)


def is_excluded_non_gu_role(text: str) -> bool:
    low = (text or "").lower()
    return any(m in low for m in NON_GU_ROLE_EXCLUSION_MARKERS)


def is_generalunternehmer(text: str) -> tuple[bool, str]:
    """True tylko gdy tekst zawiera marker GU (bez samodzielnego bauunternehmen/ladenbau)."""
    low = (text or "").lower()
    if is_excluded_non_gu_role(low):
        return False, "excluded_non_gu_role"
    for marker in STRICT_GU_MARKERS:
        if marker in low:
            return True, marker.strip()
    return False, ""


def is_gu_or_retail_build_specialist(text: str) -> bool:
    low = (text or "").lower()
    if REQUIRE_GENERALUNTERNEHMER:
        ok, _ = is_generalunternehmer(low)
        return ok
    if any(m in low for m in GU_BUILDER_MARKERS):
        return True
    return any(m in low for m in FILIALBAU_SPECIALIST_MARKERS)


def is_media_publisher_contact(
    *,
    url: str = "",
    email: str = "",
    name: str = "",
    text: str = "",
) -> bool:
    """True = medium / wydawca / portal branżowy, nie Bauunternehmen."""
    low = _blob(name, url, email, text)
    if any(m in low for m in MEDIA_PUBLISHER_NAME_MARKERS):
        return True
    url_low = (url or "").lower()
    if any(m in url_low for m in MEDIA_PUBLISHER_DOMAIN_MARKERS):
        return True
    if any(m in url_low for m in MEDIA_PUBLISHER_URL_PATH_MARKERS):
        return True
    email_low = (email or "").strip().lower()
    if email_low.startswith("redaktion@"):
        return True
    return False


def is_retail_store_operator_contact(
    *,
    url: str = "",
    email: str = "",
    text: str = "",
) -> bool:
    """True = operator sklepu, nie GU."""
    low = _blob(url, email, text)
    if any(m in low for m in RETAIL_OPERATOR_DOMAIN_MARKERS):
        if not any(
            b in low
            for b in (
                *RETAIL_STORE_BUILD_MARKERS,
                *RETAIL_STORE_UMBAU_MARKERS,
                *GU_BUILDER_MARKERS,
                *FILIALBAU_SPECIALIST_MARKERS,
            )
        ):
            return True
    if sum(1 for m in RETAIL_OPERATOR_PAGE_MARKERS if m in low) >= 2:
        if not any(
            b in low
            for b in (*RETAIL_STORE_BUILD_MARKERS, *RETAIL_STORE_UMBAU_MARKERS)
        ):
            return True
    return False


def _has_portfolio_section(low: str) -> bool:
    if _portfolio_negates_market_projects(low):
        return False
    return any(m in low for m in PORTFOLIO_SECTION_MARKERS)


def portfolio_negates_market_projects(text: str) -> bool:
    """„keine Supermarktprojekte”, „ohne Filialbau-Referenzen” itp."""
    low = (text or "").lower()
    return _portfolio_negates_market_projects(low)


def _portfolio_negates_market_projects(low: str) -> bool:
    """Jawna deklaracja braku projektów marketów — nie mylić z brakiem galerii www."""
    return any(
        x in low
        for x in (
            "keine supermarkt",
            "kein supermarkt",
            "ohne supermarkt",
            "nicht supermarkt",
            "keine filial",
            "kein filial",
            "ohne filial",
            "keine marktprojekte",
            "keine supermarktprojekte",
            "ohne einzelhandel",
            "keine einzelhandel",
        )
    )


def _has_retail_project_image_paths(low: str) -> bool:
    """Ścieżki/alt obrazów sklepów (np. rewe-filiale.jpg) — bez sekcji Referenzen."""
    if _portfolio_negates_market_projects(low):
        return False
    if not any(ext in low for ext in RETAIL_IMAGE_FILE_EXTENSIONS):
        return False
    retail_hint = _has_retail_store_context(low) or any(
        chain in low for chain in RETAIL_CHAIN_IN_PORTFOLIO_MARKERS
    )
    if not retail_hint:
        return False
    return any(
        hint in low
        for hint in (
            *RETAIL_PROJECT_BUILD_ACTIVITY_MARKERS,
            "supermarkt",
            "filiale",
            "filial",
            "discounter",
            "markt",
            "projekt",
            "bau",
        )
    )


def _has_retail_project_description_evidence(low: str) -> bool:
    """Opisy realizacji marketów na stronie głównej / podstronach (bez Referenzen)."""
    if _portfolio_negates_market_projects(low):
        return False
    if not _has_retail_store_context(low):
        return False
    if not any(m in low for m in RETAIL_PROJECT_BUILD_ACTIVITY_MARKERS):
        return False
    if any(chain in low for chain in RETAIL_CHAIN_IN_PORTFOLIO_MARKERS):
        return True
    if any(m in low for m in RETAIL_PROJECT_DESCRIPTION_MARKERS):
        return True
    if _has_retail_project_image_paths(low):
        return True
    return False


def _has_market_photo_gallery_context(low: str) -> bool:
    """Zdjęcia / galeria z marketami (bez nagłówka Portfolio)."""
    if _portfolio_negates_market_projects(low):
        return False
    if _has_retail_project_image_paths(low):
        return True
    if not any(m in low for m in MARKET_PHOTO_GALLERY_MARKERS):
        return False
    return _has_retail_store_context(low) or any(
        chain in low for chain in RETAIL_CHAIN_IN_PORTFOLIO_MARKERS
    )


def _has_market_projects_evidence(low: str) -> bool:
    """
    Dowód projektów marketów na stronie: referencje, portfolio LUB zdjęcia/alt/src
    (np. Fotogalerie Rewe, Bild Supermarkt Neubau) — bez wymogu sekcji Portfolio.
    """
    if _portfolio_negates_market_projects(low):
        if not any(
            chain in low
            for chain in RETAIL_CHAIN_IN_PORTFOLIO_MARKERS
            if len(chain) >= 4
        ):
            return False
    if any(m in low for m in MARKET_PROJECT_IN_PORTFOLIO_MARKERS):
        return True
    for chain in sorted(RETAIL_CHAIN_IN_PORTFOLIO_MARKERS, key=len, reverse=True):
        if chain in low and (
            _has_portfolio_section(low)
            or "referenzen" in low
            or "referenzprojekt" in low
            or _has_market_photo_gallery_context(low)
            or is_gu_or_retail_build_specialist(low)
        ):
            return True
    if _has_market_photo_gallery_context(low):
        return True
    if _has_retail_store_context(low) and any(
        m in low
        for m in (
            "referenzprojekt",
            "referenzprojekte",
            "einzelhandelsprojekt",
            "filialprojekt",
            "marktprojekt",
            "supermarktprojekt",
            "discounterprojekt",
        )
    ):
        return True
    if _has_portfolio_section(low) and _has_retail_store_context(low):
        if ("portfolio" in low or "unsere projekte" in low or "bauprojekte" in low) and (
            "supermarkt" in low
            or "filial" in low
            or "discounter" in low
            or "einzelhandel" in low
            or "lebensmittelmarkt" in low
            or "verbrauchermarkt" in low
        ):
            return not _portfolio_negates_market_projects(low)
    if _has_retail_project_description_evidence(low):
        return True
    if _has_retail_project_image_paths(low):
        return True
    return False


def has_market_project_evidence_on_website(text: str) -> bool:
    """Projekty marketów: Referenzen/Portfolio, zdjęcia sklepów (alt/src) lub opisy."""
    return _has_market_projects_evidence((text or "").lower())


def has_retail_references_or_portfolio(text: str) -> bool:
    """Alias — ten sam warunek co has_market_project_evidence_on_website."""
    return has_market_project_evidence_on_website(text)


has_market_store_projects_portfolio = has_market_project_evidence_on_website


def mentions_retail_store_build_activity_core(text: str) -> bool:
    """GU / Filialbau + Neubau/Umbau marketów (bez wymogu Referenzen)."""
    low = (text or "").lower()
    if any(m in low for m in PURE_RENOVATION_WITHOUT_STORE_BUILD):
        if not _has_retail_store_context(low):
            return False
    if "bausanierung" in low and not _has_retail_store_context(low):
        if not any(m in low for m in FILIALBAU_SPECIALIST_MARKERS):
            return False
    if not is_gu_or_retail_build_specialist(low):
        return False
    if not _has_retail_store_context(low):
        return False
    has_neubau = any(m in low for m in RETAIL_STORE_BUILD_MARKERS)
    has_umbau = any(m in low for m in RETAIL_STORE_UMBAU_MARKERS)
    if "umbau" in low or "modernisierung" in low or "revitalisierung" in low:
        if _has_retail_store_context(low):
            has_umbau = True
    if has_neubau or has_umbau:
        return True
    return any(m in low for m in GU_BUILDER_MARKERS) and (
        "neubau" in low or "realis" in low or "erricht" in low
    )


def mentions_retail_store_build_activity(text: str) -> bool:
    """GU / Filialbau + Neubau/Umbau + opcjonalnie dowód projektów (Referenzen/Portfolio)."""
    low = (text or "").lower()
    if not mentions_retail_store_build_activity_core(low):
        return False
    if portfolio_negates_market_projects(low):
        return False
    if has_retail_references_or_portfolio(low):
        return True
    return mentions_retail_store_build_activity_core(low)


_SERPER_ONLY_GU_MARKERS = STRICT_GU_MARKERS
_SERPER_ONLY_ROLE_MARKERS = _SERPER_ONLY_GU_MARKERS
_SERPER_ONLY_TRADE_MARKERS = (
    "laden",
    "filial",
    "einzelhandel",
    "supermarkt",
    "gewerbe",
    "markt",
    "discounter",
    "filiale",
    "handelsimmobilie",
)


def is_serper_only_pending_candidate(
    *,
    email: str = "",
    url: str = "",
    name: str = "",
    text: str = "",
    search_term: str = "",
) -> bool:
    """
    Sobota (serper-only): luźny filtr na tytule/snippetcie.
    Bez wymogu Neubau/Umbau — weryfikacja małej firmy w niedzielę.
    Sieć handlowa: w snippetcie LUB w frazie Serper (Google rzadko powtarza
    „Lidl/Rewe” w snippetcie mimo trafnej strony).
    """
    combined = _blob(name, url, email, text)
    if is_non_commercial_contact(email=email, url=url, name=name):
        return False
    if is_media_publisher_contact(email=email, url=url, name=name, text=combined):
        return False
    if is_retail_store_operator_contact(url=url, email=email, text=combined):
        return False
    if not is_valid_commercial_company_contact(email=email, url=url, name=name):
        return False
    low = combined.lower()
    chain_context = f"{low} {(search_term or '').lower()}".strip()
    if not has_required_retail_chain_mention(chain_context):
        return False
    if is_excluded_non_gu_role(low):
        return False
    gu_ok, _ = is_generalunternehmer(low)
    if gu_ok:
        return True
    # GU w nazwie (np. „BAUTAL GU GmbH”) — bez wymogu słów branżowych w snippetcie
    if " gu " in f" {low} " or low.endswith(" gu"):
        return True
    has_trade = any(m in low for m in _SERPER_ONLY_TRADE_MARKERS)
    return gu_ok and has_trade


def is_loose_serper_discovery_candidate(
    *,
    email: str = "",
    url: str = "",
    name: str = "",
    text: str = "",
) -> bool:
    """
    Lżejszy filtr na etapie Serper (tytuł/snippet).
    Wymaga GU/Filialbau + kontekst EH; bez wymogu portfolio (to sprawdza www).
    """
    combined = _blob(name, url, email, text)
    if is_non_commercial_contact(email=email, url=url, name=name):
        return False
    if is_media_publisher_contact(email=email, url=url, name=name, text=combined):
        return False
    if is_retail_store_operator_contact(url=url, email=email, text=combined):
        return False
    if not is_valid_commercial_company_contact(email=email, url=url, name=name):
        return False
    if not has_required_retail_chain_mention(combined):
        return False
    return mentions_retail_store_build_activity_core(combined)


def is_valid_retail_store_builder_contact(
    *,
    email: str = "",
    url: str = "",
    name: str = "",
    text: str = "",
) -> bool:
    """GU / Bauunternehmen budujące lub przebudowujące sklepy i markety."""
    combined = _blob(name, url, email, text)
    if is_non_commercial_contact(email=email, url=url, name=name):
        return False
    if is_media_publisher_contact(email=email, url=url, name=name, text=combined):
        return False
    if is_retail_store_operator_contact(url=url, email=email, text=combined):
        return False
    if not is_valid_commercial_company_contact(email=email, url=url, name=name):
        return False
    if portfolio_negates_market_projects(combined):
        return False
    return mentions_retail_store_build_activity_core(combined)


def is_cache_contact_not_store_builder(place_url: str, info: dict | None) -> bool:
    if not isinstance(info, dict):
        return True
    if (
        (info.get("verification_reason") or "").strip() == "pending_www_verify"
        and not info.get("retail_verified")
    ):
        return False
    if (info.get("discovery_bundesland") or "").strip() and not email:
        return False
    email = (info.get("email_target") or "").strip()
    if not email:
        found = (info.get("emails_found") or "").strip()
        if found:
            email = found.split(",")[0].strip()
    url = (place_url or info.get("official_website") or "").strip()
    name = (
        info.get("company_name_clean")
        or info.get("company_name")
        or info.get("company_name_raw")
        or ""
    ).strip()
    extra = " ".join(
        str(info.get(k) or "")
        for k in (
            "verification_reason",
            "page_snippet",
            "serper_title",
            "serper_snippet",
            "retail_chains",
            "retail_chains_found",
        )
    )
    return not is_valid_retail_store_builder_contact(
        email=email, url=url, name=name, text=extra
    )
