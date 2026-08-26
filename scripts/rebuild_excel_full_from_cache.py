# -*- coding: utf-8 -*-
"""
Buduje pełny pl_materialy_kontakte.xlsx z artefaktu Wyniki:
  - istniejący Excel
  - contacts
  - claude_row_enrichment (adres/telefon/nazwa)
  - claude_page_verify (verified=true)
Bez kolumn odpowiedzi/cen.
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for _p in (ROOT, ROOT / "libs", ROOT / "scripts"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))


def _s(v) -> str:
    return str(v or "").strip()


def _load_json_section(cache: dict, name: str) -> dict:
    raw = cache.get(name) or {}
    return raw if isinstance(raw, dict) else {}


def rows_from_enrichment(enrich: dict) -> list[dict]:
    rows: list[dict] = []
    for url, info in enrich.items():
        if not isinstance(info, dict):
            continue
        website = _s(info.get("website") or info.get("url") or url)
        name = _s(info.get("company_name_clean") or info.get("nazwa"))
        if not website and not name:
            continue
        phone = _s(info.get("phone") or info.get("telefon") or info.get("phones_found"))
        if "," in phone:
            phone = phone.split(",", 1)[0].strip()
        rows.append(
            {
                "url": _s(info.get("url") or website),
                "www": website,
                "official_website": website,
                "nazwa": name,
                "company_name_clean": name,
                "company_name_raw": name,
                "adres": _s(info.get("address") or info.get("adres") or info.get("full_address")),
                "full_address": _s(info.get("address") or info.get("adres") or info.get("full_address")),
                "telefon": phone,
                "phones_found": phone,
                "bundesland": _s(info.get("bundesland") or info.get("wojewodztwo")),
                "retail_chains_found": _s(info.get("handelsketten") or info.get("retail_chains_found")),
                "email_target": _s(info.get("email_target") or info.get("email")),
                "emails_found": _s(info.get("emails_found") or ""),
                "retail_verified": True,
                "is_small_firm": True,
            }
        )
    return rows


def rows_from_verified(verify: dict) -> list[dict]:
    rows: list[dict] = []
    for url, info in verify.items():
        if not isinstance(info, dict):
            continue
        if info.get("verified") is not True:
            continue
        website = _s(url)
        if not website:
            continue
        chains = info.get("retail_chains") or []
        if isinstance(chains, list):
            chains_s = ", ".join(str(x) for x in chains if str(x).strip())
        else:
            chains_s = _s(chains)
        claude = info.get("claude") if isinstance(info.get("claude"), dict) else {}
        name = _s(
            info.get("company_name_clean")
            or info.get("company_name")
            or claude.get("company_name")
        )
        rows.append(
            {
                "url": website,
                "www": website,
                "official_website": website,
                "nazwa": name or website,
                "company_name_clean": name or website,
                "company_name_raw": name or website,
                "adres": _s(info.get("full_address") or info.get("address")),
                "full_address": _s(info.get("full_address") or info.get("address")),
                "telefon": _s(info.get("phones_found") or info.get("phone")),
                "phones_found": _s(info.get("phones_found") or info.get("phone")),
                "bundesland": _s(info.get("bundesland")),
                "email_target": _s(info.get("email_target")),
                "emails_found": _s(info.get("emails_found")),
                "retail_chains_found": chains_s,
                "retail_verified": True,
                "gu_marker": _s(info.get("gu_marker")),
                "is_gu": bool(info.get("is_gu")),
                "is_small_firm": bool(info.get("is_small_firm", True)),
                "verification_reason": _s(info.get("verification_reason")),
            }
        )
    return rows


def apply_enrichment_to_rows(rows: list[dict], enrich: dict) -> int:
    """Dopisuje puste pola z enrichment po URL."""
    by_url = {}
    for r in rows:
        u = _s(r.get("url") or r.get("www") or r.get("official_website")).lower()
        if u:
            by_url[u] = r
    filled = 0
    for url, info in enrich.items():
        if not isinstance(info, dict):
            continue
        key = _s(info.get("url") or info.get("website") or url).lower()
        row = by_url.get(key)
        if not row:
            continue
        mapping = {
            "nazwa": _s(info.get("company_name_clean")),
            "company_name_clean": _s(info.get("company_name_clean")),
            "adres": _s(info.get("address")),
            "full_address": _s(info.get("address")),
            "telefon": _s(info.get("phone")),
            "phones_found": _s(info.get("phone")),
            "bundesland": _s(info.get("bundesland")),
            "www": _s(info.get("website")),
            "official_website": _s(info.get("website")),
            "retail_chains_found": _s(info.get("handelsketten")),
        }
        for field, val in mapping.items():
            if val and not _s(row.get(field)):
                row[field] = val
                filled += 1
    return filled


def build_full_rows(scraper, cache: dict, existing_rows: list[dict], logger: logging.Logger):
    contacts_rows = scraper.build_all_rows_from_cache(cache)
    enrich = _load_json_section(cache, "claude_row_enrichment")
    verify = _load_json_section(cache, "claude_page_verify")
    enrich_rows = rows_from_enrichment(enrich)
    verify_rows = rows_from_verified(verify)

    merged = scraper.merge_pipeline_rows(list(existing_rows), contacts_rows)
    merged = scraper.merge_pipeline_rows(merged, enrich_rows)
    merged = scraper.merge_pipeline_rows(merged, verify_rows)
    filled = apply_enrichment_to_rows(merged, enrich)

    logger.info(
        "Źródła: excel=%s contacts=%s enrich=%s verified=%s → merged=%s (uzupełniono pól=%s)",
        len(existing_rows),
        len(contacts_rows),
        len(enrich_rows),
        len(verify_rows),
        len(merged),
        filled,
    )
    return merged


def main() -> int:
    parser = argparse.ArgumentParser(description="Pełny Excel PL z cache + enrichment + verify")
    parser.add_argument("--cache", type=Path, default=Path("Wyniki/pl_materialy_cache.json"))
    parser.add_argument("--xlsx", type=Path, default=Path("Wyniki/pl_materialy_kontakte.xlsx"))
    parser.add_argument("--eligible-only", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    logger = logging.getLogger("full_excel_enriched")

    import pl_materialy_scraper as scraper

    cache_path = args.cache
    if not cache_path.is_file():
        hits = list(Path(".").rglob("pl_materialy_cache.json"))
        if not hits:
            raise SystemExit("Brak pl_materialy_cache.json")
        cache_path = hits[0]

    xlsx_path = args.xlsx
    if not xlsx_path.is_file():
        hits = list(Path(".").rglob("pl_materialy_kontakte.xlsx"))
        if hits:
            xlsx_path = hits[0]

    scraper.CACHE_FILE = cache_path
    scraper.OUTPUT_DIR = xlsx_path.parent if xlsx_path else Path("Wyniki")
    scraper.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    scraper.OUTPUT_FILE = scraper.OUTPUT_DIR / "pl_materialy_kontakte.xlsx"

    logger.info("CACHE=%s size=%s", cache_path, cache_path.stat().st_size)
    cache = scraper.load_cache(logger)
    existing, _ = scraper.load_existing_output(scraper.OUTPUT_FILE, logger)
    if xlsx_path.is_file() and xlsx_path.resolve() != scraper.OUTPUT_FILE.resolve():
        extra, _ = scraper.load_existing_output(xlsx_path, logger)
        existing = scraper.merge_pipeline_rows(existing, extra)

    merged = build_full_rows(scraper, cache, existing, logger)
    export = scraper.build_export_rows(
        merged, logger=logger, cache=cache, require_eligible=args.eligible_only
    )
    with_mail = sum(1 for r in export if _s(r.get("E-mail")))
    with_addr = sum(1 for r in export if _s(r.get("Adres")))
    logger.info(
        "export=%s with_email=%s with_address=%s eligible=%s",
        len(export),
        with_mail,
        with_addr,
        args.eligible_only,
    )
    # Rebuild ma zachować dane — bez Claude cleanup (kosztowne i może wyczyścić pola).
    scraper.ENABLE_CLAUDE_ROW_CLEANUP = False
    scraper.save_excel(
        merged,
        scraper.OUTPUT_FILE,
        logger,
        cache=cache,
        require_eligible=args.eligible_only,
    )
    logger.info("WROTE %s bytes=%s", scraper.OUTPUT_FILE, scraper.OUTPUT_FILE.stat().st_size)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
