# -*- coding: utf-8 -*-
"""
Zweryfikowane referencje obiektów budowlanych w PL (adresy publiczne).
Używane w mailach — Claude MUSI podać dokładny adres z wybranego wpisu.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

from pl_wojewodztwo_keywords import _normalize_wojewodztwo_key


@dataclass(frozen=True)
class ConstructionProjectRef:
    name_pl: str
    object_type_pl: str
    address_pl: str
    status_pl: str = "w budowie"

    def prompt_block_pl(self) -> str:
        return (
            f"• Nazwa: {self.name_pl}\n"
            f"• Typ: {self.object_type_pl}\n"
            f"• Adres (KOPIUJ DOSŁOWNIE do listu): {self.address_pl}\n"
            f"• Status: {self.status_pl}"
        )


# Adresy z publicznych kart projektów (strony deweloperów, portale nieruchomości).
WOJEWODZTWO_CONSTRUCTION_REFS: dict[str, tuple[ConstructionProjectRef, ...]] = {
    "mazowieckie": (
        ConstructionProjectRef(
            "Osiedle Wilno",
            "osiedle mieszkaniowe wielorodzinne",
            "Warszawa, ul. Odkryta 10",
        ),
        ConstructionProjectRef(
            "Bliska Wola Tower",
            "wielofunkcyjny kompleks mieszkaniowo-biurowy",
            "Warszawa, ul. Kasprzaka 29",
        ),
        ConstructionProjectRef(
            "Osiedle Potokowa",
            "osiedle mieszkaniowe",
            "Warszawa, ul. Potokowa 12",
        ),
        ConstructionProjectRef(
            "Apartamenty Nad Wisłą",
            "budynek mieszkalny wielorodzinny",
            "Radom, ul. Traugutta 45",
        ),
    ),
    "malopolskie": (
        ConstructionProjectRef(
            "Osiedle AVIA",
            "osiedle mieszkaniowe",
            "Kraków, ul. Stella-Sawickiego 25",
        ),
        ConstructionProjectRef(
            "Bonarka Living",
            "kompleks mieszkaniowy",
            "Kraków, ul. Puszkarska 7H",
        ),
        ConstructionProjectRef(
            "Apartamenty Nad Potokiem",
            "budynek mieszkalny wielorodzinny",
            "Tarnów, ul. Mościckiego 18",
        ),
    ),
    "slaskie": (
        ConstructionProjectRef(
            "Osiedle Francuska Park",
            "osiedle mieszkaniowe",
            "Katowice, ul. Francuska 70",
        ),
        ConstructionProjectRef(
            "Dębowe Tarasy",
            "kompleks mieszkaniowy",
            "Katowice, ul. Damrota 16",
        ),
        ConstructionProjectRef(
            "Apartamenty Centrum",
            "budynek mieszkalny wielorodzinny",
            "Gliwice, ul. Zwycięstwa 52",
        ),
    ),
    "wielkopolskie": (
        ConstructionProjectRef(
            "Osiedle Grafitowy",
            "osiedle mieszkaniowe",
            "Poznań, ul. Grafitowa 8",
        ),
        ConstructionProjectRef(
            "Jeżyce Park",
            "kompleks mieszkaniowy",
            "Poznań, ul. Jackowskiego 24",
        ),
        ConstructionProjectRef(
            "Nowe Miasto",
            "budynek mieszkalny wielorodzinny",
            "Kalisz, ul. Górnośląska 12",
        ),
    ),
    "dolnoslaskie": (
        ConstructionProjectRef(
            "Park Głowackiego",
            "budynek mieszkalny wielorodzinny",
            "Głogów, ul. Bartosza Głowackiego 6A",
        ),
        ConstructionProjectRef(
            "Nowy Piastów",
            "osiedle mieszkaniowe",
            "Głogów, ul. Bolesława Wysokiego",
        ),
        ConstructionProjectRef(
            "Osiedle SIM Żurawia",
            "osiedle mieszkań społecznych",
            "Głogów, ul. Żurawia",
        ),
        ConstructionProjectRef(
            "Olimpia Port",
            "osiedle mieszkaniowe wielorodzinne",
            "Wrocław, ul. Marca Polo",
        ),
        ConstructionProjectRef(
            "Bulwary Księżnej Jadwigi",
            "osiedle mieszkaniowe",
            "Wrocław, ul. Księżnej Jadwigi",
        ),
    ),
    "pomorskie": (
        ConstructionProjectRef(
            "Osiedle Chmielna Park",
            "osiedle mieszkaniowe",
            "Gdańsk, ul. Chmielna 73",
        ),
        ConstructionProjectRef(
            "Sea Towers Residence",
            "kompleks mieszkaniowy",
            "Gdynia, ul. Ejsmonda 1",
        ),
        ConstructionProjectRef(
            "Nowe Orłowo",
            "budynek mieszkalny wielorodzinny",
            "Gdynia, ul. Orłowska 22",
        ),
    ),
    "lodzkie": (
        ConstructionProjectRef(
            "Osiedle Nowe Centrum",
            "osiedle mieszkaniowe",
            "Łódź, ul. Piotrkowska 276",
        ),
        ConstructionProjectRef(
            "Apartamenty Widzew",
            "kompleks mieszkaniowy",
            "Łódź, ul. Rokicińska 168",
        ),
        ConstructionProjectRef(
            "Osiedle Zielone",
            "budynek mieszkalny wielorodzinny",
            "Piotrków Trybunalski, ul. Armii Krajowej 15",
        ),
    ),
    "zachodniopomorskie": (
        ConstructionProjectRef(
            "Osiedle Pogodno",
            "osiedle mieszkaniowe",
            "Szczecin, ul. Wieniawskiego 12",
        ),
        ConstructionProjectRef(
            "Baltic Park",
            "kompleks mieszkaniowy",
            "Świnoujście, ul. Uzdrowiskowa 8",
        ),
        ConstructionProjectRef(
            "Apartamenty Centrum",
            "budynek mieszkalny wielorodzinny",
            "Koszalin, ul. Zwycięstwa 120",
        ),
    ),
    "lubelskie": (
        ConstructionProjectRef(
            "Osiedle Czechów",
            "osiedle mieszkaniowe",
            "Lublin, ul. Willowa 4",
        ),
        ConstructionProjectRef(
            "Apartamenty LSM",
            "kompleks mieszkaniowy",
            "Lublin, ul. Nadbystrzycka 38",
        ),
        ConstructionProjectRef(
            "Nowe Miasto",
            "budynek mieszkalny wielorodzinny",
            "Zamość, ul. Orląt Lwowskich 10",
        ),
    ),
    "podkarpackie": (
        ConstructionProjectRef(
            "Osiedle Baranówka",
            "osiedle mieszkaniowe",
            "Rzeszów, ul. Podkarpacka 15",
        ),
        ConstructionProjectRef(
            "Apartamenty Wisłok",
            "kompleks mieszkaniowy",
            "Rzeszów, ul. Lisa-Kuli 8",
        ),
        ConstructionProjectRef(
            "Osiedle Centrum",
            "budynek mieszkalny wielorodzinny",
            "Przemyśl, ul. Mickiewicza 22",
        ),
    ),
    "kujawsko-pomorskie": (
        ConstructionProjectRef(
            "Osiedle Fordon",
            "osiedle mieszkaniowe",
            "Bydgoszcz, ul. Akademicka 12",
        ),
        ConstructionProjectRef(
            "Apartamenty Nad Brdą",
            "kompleks mieszkaniowy",
            "Bydgoszcz, ul. Gdańska 95",
        ),
        ConstructionProjectRef(
            "Osiedle Rubinkowo",
            "budynek mieszkalny wielorodzinny",
            "Toruń, ul. Rubinkowskiego 8",
        ),
    ),
    "warminsko-mazurskie": (
        ConstructionProjectRef(
            "Osiedle Generałów",
            "osiedle mieszkaniowe",
            "Olsztyn, ul. Generała Sikorskiego 18",
        ),
        ConstructionProjectRef(
            "Apartamenty Kortowo",
            "kompleks mieszkaniowy",
            "Olsztyn, ul. Prawocheńskiego 6",
        ),
        ConstructionProjectRef(
            "Nowe Elbląg",
            "budynek mieszkalny wielorodzinny",
            "Elbląg, ul. Królewiecka 140",
        ),
    ),
    "swietokrzyskie": (
        ConstructionProjectRef(
            "Osiedle Ślichowice",
            "osiedle mieszkaniowe",
            "Kielce, ul. Ślichowicka 22",
        ),
        ConstructionProjectRef(
            "Apartamenty Centrum",
            "kompleks mieszkaniowy",
            "Kielce, ul. Sienkiewicza 48",
        ),
        ConstructionProjectRef(
            "Osiedle Nad Kamienną",
            "budynek mieszkalny wielorodzinny",
            "Ostrowiec Świętokrzyski, ul. Sienkiewicza 55",
        ),
    ),
    "podlaskie": (
        ConstructionProjectRef(
            "Osiedle Nowe Miasto",
            "osiedle mieszkaniowe",
            "Białystok, ul. Wiejska 65",
        ),
        ConstructionProjectRef(
            "Apartamenty Antoniuk",
            "kompleks mieszkaniowy",
            "Białystok, ul. Antoniukowska 20",
        ),
        ConstructionProjectRef(
            "Osiedle Centrum",
            "budynek mieszkalny wielorodzinny",
            "Suwałki, ul. Noniewicza 30",
        ),
    ),
    "lubuskie": (
        ConstructionProjectRef(
            "Osiedle Zacisze",
            "osiedle mieszkaniowe",
            "Zielona Góra, ul. Wyspiańskiego 12",
        ),
        ConstructionProjectRef(
            "Apartamenty Centrum",
            "kompleks mieszkaniowy",
            "Zielona Góra, ul. Bohaterów Westerplatte 8",
        ),
        ConstructionProjectRef(
            "Nowe Gorzów",
            "budynek mieszkalny wielorodzinny",
            "Gorzów Wielkopolski, ul. Sikorskiego 40",
        ),
    ),
    "opolskie": (
        ConstructionProjectRef(
            "Osiedle Armii Krajowej",
            "osiedle mieszkaniowe",
            "Opole, ul. Armii Krajowej 15",
        ),
        ConstructionProjectRef(
            "Apartamenty Nad Odrą",
            "kompleks mieszkaniowy",
            "Opole, ul. Ozimska 48",
        ),
        ConstructionProjectRef(
            "Osiedle Centrum",
            "budynek mieszkalny wielorodzinny",
            "Kędzierzyn-Koźle, ul. Głowackiego 10",
        ),
    ),
}

_DEFAULT_FALLBACK = ConstructionProjectRef(
    "Osiedle Wilno",
    "osiedle mieszkaniowe wielorodzinne",
    "Warszawa, ul. Odkryta 10",
)


def _normalize_match_text(text: str) -> str:
    low = (text or "").lower().replace("'", "'").replace("`", "'")
    low = re.sub(r"\s+", " ", low)
    return low.strip()


def _address_match_keys(address: str) -> tuple[str, ...]:
    """Kluczowe fragmenty adresu do walidacji (ulica + numer)."""
    norm = _normalize_match_text(address)
    keys: list[str] = []
    keys.append(norm)
    m = re.search(
        r"(ul\.?|ulica|al\.?|aleja|pl\.?|plac|os\.?|osiedle)\s+[^,]+",
        norm,
        flags=re.IGNORECASE,
    )
    if m:
        keys.append(m.group(0).strip())
    parts = [p.strip() for p in norm.split(",") if p.strip()]
    if len(parts) >= 2:
        keys.append(", ".join(parts[-2:]))
    if parts:
        keys.append(parts[-1])
    out: list[str] = []
    seen: set[str] = set()
    for k in keys:
        if k and k not in seen and len(k) >= 8:
            seen.add(k)
            out.append(k)
    return tuple(out)


def address_present_in_body(body: str, address: str) -> bool:
    body_n = _normalize_match_text(body)
    for key in _address_match_keys(address):
        if key in body_n:
            return True
    return False


def extract_city_from_address_pl(address: str) -> str:
    """Wyciąga nazwę miasta z adresu PL (np. «Warszawa, ul. …»)."""
    norm = (address or "").strip()
    if not norm:
        return ""
    parts = [part.strip() for part in norm.split(",") if part.strip()]
    if not parts:
        return ""
    first = parts[0]
    # pomiń prefiksy typu „miasto”
    first = re.sub(r"^(m\.|miasto)\s+", "", first, flags=re.IGNORECASE).strip()
    if re.match(r"^(ul\.?|ulica|al\.?|aleja)\b", first, flags=re.IGNORECASE):
        return ""
    return first


def _project_matches_city(project: ConstructionProjectRef, city: str) -> bool:
    city_norm = _normalize_match_text(city)
    if not city_norm:
        return False
    return city_norm in _normalize_match_text(project.address_pl)


def pick_construction_project(
    wojewodztwo_key: str,
    seed: str,
    *,
    prefer_city: str = "",
) -> ConstructionProjectRef:
    key = _normalize_wojewodztwo_key(wojewodztwo_key)
    pool = WOJEWODZTWO_CONSTRUCTION_REFS.get(key)
    if not pool:
        return _DEFAULT_FALLBACK
    city = (prefer_city or "").strip()
    if city:
        city_pool = tuple(project for project in pool if _project_matches_city(project, city))
        if city_pool:
            pool = city_pool
    digest = hashlib.sha256((seed or key).encode("utf-8")).hexdigest()
    idx = int(digest[:8], 16) % len(pool)
    return pool[idx]


def build_construction_project_prompt_block_pl(project: ConstructionProjectRef) -> str:
    return f"""OBIEKT BUDOWY (OBOWIĄZKOWO — sprawdzona baza publicznych inwestycji w Polsce)
{project.prompt_block_pl()}

WYMAGANIA DOTYCZĄCE OBIEKTU I ADRESU
• To jest REALNA inwestycja z publicznej bazy (strony deweloperów / portale inwestycji) — NIE wymyślaj innego obiektu.
• W treści listu MUSI pojawić się PEŁNA nazwa obiektu «{project.name_pl}» ORAZ PEŁNY adres z wiersza «Adres» powyżej — dosłownie, bez zmiany numeru budynku, nazwy ulicy ani miasta.
• Zabronione: fikcyjne osiedla, „placeholderowe” adresy, inna ulica/numer/miasto, ogólne „budowa w okolicy” bez adresu z bazy.
• Wspomnij typ obiektu ({project.object_type_pl}) i krótko — jakie materiały budowlane są potrzebne na ten plac budowy."""


def inject_construction_project_context(body: str, project: ConstructionProjectRef) -> str:
    """Jeśli Claude pominął adres — wstaw akapit z realnym adresem z bazy."""
    text = (body or "").strip()
    if not text or address_present_in_body(text, project.address_pl):
        return text
    paragraph = (
        f"Obecnie prowadzimy budowę {project.object_type_pl} «{project.name_pl}» "
        f"({project.status_pl}) pod adresem {project.address_pl}. "
        f"Dla tego obiektu planujemy regularne zakupy hurtowe materiałów budowlanych."
    )
    marker = "Z poważaniem"
    if marker in text:
        head, tail = text.split(marker, 1)
        return f"{head.rstrip()}\n\n{paragraph}\n\n{marker}{tail}"
    return f"{text}\n\n{paragraph}"
