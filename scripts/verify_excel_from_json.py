# -*- coding: utf-8 -*-
"""
Po zapisie Excela: weryfikuje vs cache JSON, uzupelnia braki i nadpisuje plik.

Walidacja przepuszcza z JSON pola potrzebne w Excelu (nazwa, e-mail, telefon,
adres, wojewodztwo, www, URL) — bez filtra GU/retail.
Zrodla: contacts + claude_row_enrichment + claude_page_verify.
Po zapisie ponownie czyta caly plik; przy lukach znow JSON → uzupelnienie → zapis.
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LIBS = ROOT / "libs"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(LIBS) not in sys.path:
    sys.path.insert(0, str(LIBS))

from scripts.excel_from_json_validate import (  # noqa: E402
    fill_export_from_json,
    json_contact_has_needed_data,
    merge_contact_info,
    merge_contacts_maps,
    pipeline_row_from_json,
    verify_and_fill_until_complete,
)
from scripts.recover_pi_cache_contacts import recover_contacts_from_cache_file  # noqa: E402
from scraper_email_replies import ReplySyncConfig, write_excel_with_reply_styles  # noqa: E402

CAMPAIGNS = {
    "pl": {
        "module": "pl_materialy_scraper",
        "lang": "pl",
        "campaign_id": "pl_materialy",
        "xlsx_name": "pl_materialy_kontakte.xlsx",
        "cache_glob": "*_cache.json",
    },
    "ua": {
        "module": "ua_materialy_scraper",
        "lang": "uk",
        "campaign_id": "ua_materialy",
        "xlsx_name": "ua_materialy_kontakte.xlsx",
        "cache_glob": "*_cache.json",
    },
}


def _load_scraper(campaign: str):
    spec = CAMPAIGNS[campaign]
    return __import__(spec["module"]), spec


def _cell(value) -> str:
    if value is None:
        return ""
    return str(value).strip()


def pipeline_row_as_info(row: dict) -> dict:
    return {
        "company_name_clean": _cell(row.get("company_name_clean") or row.get("nazwa")),
        "company_name": _cell(row.get("nazwa")),
        "email_target": _cell(row.get("email_target")),
        "emails_found": _cell(row.get("emails_found")),
        "phones_found": _cell(row.get("phones_found") or row.get("telefon")),
        "full_address": _cell(row.get("full_address") or row.get("adres")),
        "official_website": _cell(row.get("official_website") or row.get("www")),
        "bundesland": _cell(row.get("bundesland")),
        "retail_chains_found": _cell(row.get("retail_chains_found")),
        "email_status": _cell(row.get("email_status")),
        "retail_verified": bool(row.get("retail_verified")),
        "is_gu": bool(row.get("is_gu")),
        "is_small_firm": row.get("is_small_firm", True),
        "gu_marker": _cell(row.get("gu_marker")),
    }


def load_cache_without_website_crawl(cache_path: Path) -> dict:
    """Wczytaj cache bez ogromnego website_crawl (unikaj OOM na GB plikach)."""
    size = cache_path.stat().st_size if cache_path.is_file() else 0
    # Małe pliki — pełny JSON (bez website_crawl w pamięci wynikowej).
    if size and size < 40_000_000:
        try:
            data = json.loads(cache_path.read_text(encoding="utf-8", errors="replace"))
            if isinstance(data, dict):
                data.pop("website_crawl", None)
                data.pop("gemini_website_crawl", None)
                return data
        except (json.JSONDecodeError, MemoryError, OSError):
            pass

    markers = (b'\n  "website_crawl"', b'\n  "gemini_website_crawl"')
    buf = bytearray()
    cut_at = None
    with open(cache_path, "rb") as f:
        while True:
            chunk = f.read(4 * 1024 * 1024)
            if not chunk:
                break
            start = max(0, len(buf) - 64)
            buf.extend(chunk)
            for marker in markers:
                idx = buf.find(marker, start)
                if idx >= 0 and (cut_at is None or idx < cut_at):
                    cut_at = idx
            if cut_at is not None:
                break
            # Bezpieczeństwo: nie trzymaj >200MB prefixu bez markera
            if len(buf) > 200_000_000:
                break

    if cut_at is None:
        # Brak website_crawl — spróbuj cały prefix jako JSON (może mały cache)
        try:
            data = json.loads(bytes(buf).decode("utf-8", errors="replace"))
            return data if isinstance(data, dict) else {}
        except (json.JSONDecodeError, MemoryError):
            return {}

    prefix = bytes(buf[:cut_at]).decode("utf-8", errors="replace").rstrip()
    if prefix.endswith(","):
        prefix = prefix[:-1]
    repaired = prefix + "\n}"
    try:
        data = json.loads(repaired)
        return data if isinstance(data, dict) else {}
    except json.JSONDecodeError:
        return {}


def contacts_from_enrichment_and_verify(cache: dict) -> dict[str, dict]:
    """Dodatkowe źródła JSON → mapa contacts (adres/telefon/nazwa + verified)."""
    out: dict[str, dict] = {}
    enrich = cache.get("claude_row_enrichment") or cache.get("gemini_row_enrichment") or {}
    if isinstance(enrich, dict):
        for url, info in enrich.items():
            if not isinstance(info, dict):
                continue
            key = _cell(info.get("url") or info.get("website") or url)
            if not key:
                continue
            out[key] = {
                "company_name_clean": _cell(info.get("company_name_clean")),
                "full_address": _cell(info.get("address") or info.get("full_address")),
                "phones_found": _cell(info.get("phone") or info.get("phones_found")),
                "official_website": _cell(info.get("website") or key),
                "bundesland": _cell(info.get("bundesland")),
                "retail_chains_found": _cell(info.get("handelsketten")),
                "email_target": _cell(info.get("email_target") or info.get("email")),
                "retail_verified": True,
            }
    verify = cache.get("claude_page_verify") or cache.get("gemini_page_verify") or {}
    if isinstance(verify, dict):
        for url, info in verify.items():
            if not isinstance(info, dict) or info.get("verified") is not True:
                continue
            key = _cell(url)
            if not key:
                continue
            chains = info.get("retail_chains") or []
            if isinstance(chains, list):
                chains_s = ", ".join(str(x) for x in chains if str(x).strip())
            else:
                chains_s = _cell(chains)
            out[key] = merge_contact_info(
                out.get(key) or {},
                {
                    "company_name_clean": _cell(
                        info.get("company_name_clean") or info.get("company_name")
                    ),
                    "full_address": _cell(
                        info.get("full_address") or info.get("address")
                    ),
                    "phones_found": _cell(
                        info.get("phones_found") or info.get("phone")
                    ),
                    "official_website": key,
                    "bundesland": _cell(info.get("bundesland")),
                    "retail_chains_found": chains_s,
                    "email_target": _cell(info.get("email_target")),
                    "emails_found": _cell(info.get("emails_found")),
                    "retail_verified": True,
                    "gu_marker": _cell(info.get("gu_marker")),
                    "is_gu": bool(info.get("is_gu")),
                    "is_small_firm": info.get("is_small_firm", True),
                    "verification_reason": _cell(info.get("verification_reason")),
                },
            )
    return out


def contacts_from_website_crawl_file(cache_path: Path, logger: logging.Logger) -> dict[str, dict]:
    """Streamuj website_crawl z dysku (ijson) → mapa contacts bez page_text."""
    try:
        import ijson
    except ImportError:
        logger.warning("ijson niedostępny — pomijam website_crawl")
        return {}
    try:
        from scripts.rebuild_excel_full_from_cache import aggregate_crawl_contact
    except Exception as e:
        logger.warning("aggregate_crawl_contact: %s", e)
        return {}
    out: dict[str, dict] = {}
    try:
        with cache_path.open("rb") as f:
            for url, entry in ijson.kvitems(f, "website_crawl"):
                info = aggregate_crawl_contact(url, entry)
                if not info:
                    continue
                key = _cell(info.get("official_website") or url)
                if key:
                    out[key] = info
    except Exception as e:
        logger.warning("%s: website_crawl stream fail (%s)", cache_path.name, e)
        return {}
    return out


def collect_needed_contacts(wyniki: Path, xlsx: Path, scraper, logger: logging.Logger) -> dict[str, dict]:
    merged: dict[str, dict] = {}
    for cache_path in sorted(wyniki.glob("*_cache.json")):
        recovered: dict = {}
        extras: dict = {}
        try:
            raw = load_cache_without_website_crawl(cache_path)
            recovered = raw.get("contacts") if isinstance(raw.get("contacts"), dict) else {}
            extras = contacts_from_enrichment_and_verify(raw)
        except Exception as e:
            logger.warning("%s: stream cache fail (%s) — fallback recover", cache_path.name, e)
        if not recovered:
            recovered = recover_contacts_from_cache_file(cache_path)
        crawl_contacts = contacts_from_website_crawl_file(cache_path, logger)
        logger.info(
            "%s: contacts=%s enrich+verified=%s crawl=%s",
            cache_path.name,
            len(recovered),
            len(extras),
            len(crawl_contacts),
        )
        merged = merge_contacts_maps(merged, recovered)
        if extras:
            merged = merge_contacts_maps(merged, extras)
        if crawl_contacts:
            merged = merge_contacts_maps(merged, crawl_contacts)
    if xlsx.is_file():
        rows, _ = scraper.load_existing_output(xlsx, logger)
        excel_contacts = {}
        for row in rows:
            url = _cell(row.get("url") or row.get("www") or row.get("official_website"))
            if url:
                excel_contacts[url] = pipeline_row_as_info(row)
        logger.info("%s: excel_rows=%s", xlsx.name, len(excel_contacts))
        merged = merge_contacts_maps(merged, excel_contacts)
    needed = {}
    for url, info in merged.items():
        if not json_contact_has_needed_data(url, info):
            continue
        if scraper.is_public_portal_url(url) or scraper.is_public_portal_url(
            (info or {}).get("official_website") or ""
        ):
            continue
        needed[url] = info
    logger.info("Do Excela z JSON: %s z %s contacts", len(needed), len(merged))
    return needed


def run_verify_after_excel_save(
    wyniki: Path | None = None,
    campaign: str = "pl",
    logger: logging.Logger | None = None,
) -> tuple[int, list[dict]]:
    """Wywołanie z scrapera / rebuild: uzupełnij Excel z JSON i nadpisz plik.

    Zwraca (liczba_wierszy, luki). Przy braku contacts JSON — (0, []).
    """
    log = logger or logging.getLogger("verify_excel_json")
    wyniki = Path(wyniki) if wyniki else ROOT / "Wyniki"
    scraper, spec = _load_scraper(campaign)
    xlsx = wyniki / spec["xlsx_name"]
    contacts = collect_needed_contacts(wyniki, xlsx, scraper, log)
    if not contacts:
        log.warning("verify_excel: brak contacts JSON z danymi — pomijam")
        return 0, []
    cache = {"contacts": contacts}
    n_rows, gaps = verify_and_save(scraper, spec, contacts, xlsx, cache, log)
    if gaps:
        log.warning("VERIFY_PARTIAL rows=%s gaps=%s file=%s", n_rows, len(gaps), xlsx)
    else:
        log.info("VERIFY_OK rows=%s contacts_json=%s file=%s", n_rows, len(contacts), xlsx)
    return n_rows, gaps



def write_sheets(
    scraper,
    spec: dict,
    xlsx: Path,
    export_rows: list[dict],
    pipeline_rows: list[dict],
    cache: dict,
    logger,
) -> None:
    state_rows = scraper.build_bundesland_rows(pipeline_rows) if pipeline_rows else []
    cfg = ReplySyncConfig(
        cache_path=scraper.CACHE_FILE,
        xlsx_path=xlsx,
        lang=spec["lang"],
        campaign_id=spec["campaign_id"],
        include_reply_export_columns=spec.get("campaign_id") != "pl_materialy",
    )
    write_excel_with_reply_styles(
        xlsx,
        {
            "Info": scraper.build_excel_info_sheet_rows(),
            "Kontakte": export_rows,
            "Wojewodztwa": state_rows,
        },
        cache,
        cfg,
        logger,
    )


def verify_and_save(scraper, spec: dict, contacts: dict, xlsx: Path, cache: dict, logger) -> tuple[int, list[dict]]:
    # Zachowaj istniejący Excel — tylko uzupełnij braki / dopisz brakujące URL z JSON.
    existing_pipeline: list[dict] = []
    if xlsx.is_file():
        existing_pipeline, _ = scraper.load_existing_output(xlsx, logger)
    export_rows = (
        scraper.build_export_rows(
            existing_pipeline, logger=logger, cache=cache, require_eligible=False
        )
        if existing_pipeline
        else []
    )
    export_rows, n_fill = fill_export_from_json(contacts, export_rows)
    logger.info("Uzupelnienie z JSON: %s zmian (start=%s)", n_fill, len(existing_pipeline))
    export_rows, gaps, rounds = verify_and_fill_until_complete(contacts, export_rows)
    logger.info("Weryfikacja pamieci: rund=%s luk=%s wierszy=%s", rounds, len(gaps), len(export_rows))

    # Pipeline do arkusza Wojewodztwa: Excel + nowe z JSON
    by_url: dict[str, dict] = {}
    for row in existing_pipeline:
        url = _cell(row.get("url") or row.get("www") or row.get("official_website"))
        if url:
            by_url[url] = row
    for url, info in contacts.items():
        key = _cell(url)
        if not key:
            continue
        incoming = pipeline_row_from_json(key, info)
        if key not in by_url:
            by_url[key] = incoming
        else:
            # Non-destructive: uzupełnij puste pola pipeline
            cur = by_url[key]
            for k, v in incoming.items():
                if v not in (None, "", [], {}) and cur.get(k) in (None, "", [], {}):
                    cur[k] = v
    pipeline_rows = list(by_url.values())
    write_sheets(scraper, spec, xlsx, export_rows, pipeline_rows, cache, logger)

    extra = 0
    gaps_after: list[dict] = []
    loaded_export = export_rows
    loaded_pipeline = pipeline_rows
    for disk_round in range(5):
        loaded, _ = scraper.load_existing_output(xlsx, logger)
        loaded_pipeline = loaded
        loaded_export = scraper.build_export_rows(
            loaded, logger=logger, cache=cache, require_eligible=False
        )
        loaded_export, gaps_after, fill_rounds = verify_and_fill_until_complete(
            contacts, loaded_export
        )
        extra += fill_rounds
        if fill_rounds or gaps_after:
            logger.warning(
                "Po odczycie dysku (runda %s) JSON uzupelnia i zapisuje: rund=%s luki=%s",
                disk_round + 1,
                fill_rounds,
                len(gaps_after),
            )
            write_sheets(scraper, spec, xlsx, loaded_export, loaded_pipeline, cache, logger)
            if fill_rounds:
                continue
        break
    logger.info(
        "Weryfikacja koncowa: wierszy=%s luki=%s rund_dysku=%s",
        len(loaded_export),
        len(gaps_after),
        extra,
    )
    return len(loaded_export), gaps_after


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--campaign", choices=sorted(CAMPAIGNS), default="pl")
    parser.add_argument("--wyniki", type=Path, default=ROOT / "Wyniki")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    logger = logging.getLogger("verify_excel_json")

    n_rows, gaps = run_verify_after_excel_save(args.wyniki, args.campaign, logger)
    if n_rows == 0 and not gaps:
        print("VERIFY_SKIP: brak contacts JSON z danymi do Excela")
        return 1
    if gaps:
        print(f"VERIFY_FAIL rows={n_rows} gaps={len(gaps)}")
        for g in gaps[:20]:
            print(f"  {g['url']}: {g['reason']} {g['columns']}")
        return 1
    print(f"VERIFY_OK rows={n_rows} file={args.wyniki / CAMPAIGNS[args.campaign]['xlsx_name']}")
    return 0



if __name__ == "__main__":
    raise SystemExit(main())
