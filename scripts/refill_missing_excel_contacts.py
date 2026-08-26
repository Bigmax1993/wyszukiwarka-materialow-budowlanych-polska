# -*- coding: utf-8 -*-
"""
Uzupełnij braki w Excelu: Serper → crawl → Claude + luźniejszy regex → nadpisz Excel.

Dla wierszy bez e-maila / telefonu / adresu:
  1) zapytanie Serper o firmę (www),
  2) pełny crawl domeny,
  3) ekstrakcja kontaktów (regex PL + Claude),
  4) zapis contacts w cache JSON + nadpisanie pl_materialy_kontakte.xlsx.
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for _p in (ROOT, ROOT / "libs", ROOT / "scripts"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))


def _s(v) -> str:
    return str(v or "").strip()


def row_missing_fields(row: dict) -> list[str]:
    missing: list[str] = []
    if not _s(row.get("email_target") or row.get("emails_found")):
        missing.append("email")
    phone = _s(row.get("telefon") or row.get("phones_found"))
    if not phone:
        missing.append("phone")
    if not _s(row.get("adres") or row.get("full_address")):
        missing.append("address")
    return missing


def refill_missing(
    *,
    limit: int = 40,
    dry_run: bool = False,
    logger: logging.Logger | None = None,
) -> dict:
    import pl_materialy_scraper as scraper

    log = logger or logging.getLogger("refill_missing")
    os.environ["RELAXED_CONTACT_REGEX"] = "1"
    scraper.set_relaxed_contact_regex(True)
    # Claude cleanup przy zapisie — tylko pola z brakami; wyłączamy agresywne czyszczenie.
    scraper.ENABLE_CLAUDE_ROW_CLEANUP = False

    cache = scraper.load_cache(log)
    rows, _ = scraper.load_existing_output(scraper.OUTPUT_FILE, log)
    scraper.merge_cache_contacts_into_pipeline(rows, cache)

    candidates: list[tuple[int, dict, list[str]]] = []
    for i, row in enumerate(rows):
        miss = row_missing_fields(row)
        if not miss:
            continue
        url = _s(row.get("url") or row.get("www") or row.get("official_website"))
        name = _s(row.get("nazwa") or row.get("company_name_clean"))
        if not url and not name:
            continue
        if scraper.is_public_portal_url(url):
            continue
        candidates.append((i, row, miss))

    log.info(
        "Braki: %s wierszy (limit=%s). Pola: email/phone/address",
        len(candidates),
        limit,
    )
    stats = {
        "candidates": len(candidates),
        "processed": 0,
        "filled_email": 0,
        "filled_phone": 0,
        "filled_address": 0,
        "errors": 0,
    }
    if dry_run:
        for _, row, miss in candidates[:limit]:
            log.info(
                "DRY %s | %s | brak=%s",
                _s(row.get("nazwa"))[:40],
                _s(row.get("url") or row.get("www"))[:60],
                ",".join(miss),
            )
        return stats

    for _, row, miss in candidates[: max(0, limit)]:
        name = _s(row.get("nazwa") or row.get("company_name_clean"))
        before = {
            "email": _s(row.get("email_target")),
            "phone": _s(row.get("telefon") or row.get("phones_found")),
            "address": _s(row.get("adres") or row.get("full_address")),
        }
        try:
            # Wyczyść stary crawl tej domeny, by ponowić z relaxed regex.
            www = _s(row.get("www") or row.get("official_website") or row.get("url"))
            if www and isinstance(cache.get("website_crawl"), dict):
                cache["website_crawl"].pop(www, None)
                cache["website_crawl"].pop(www.rstrip("/"), None)
            updated = scraper.enrich_row_with_contacts(
                row, cache, log, force_refresh=True, gap_fill=True
            )
            row.update(updated)
            stats["processed"] += 1
            if not before["email"] and _s(row.get("email_target")):
                stats["filled_email"] += 1
            if not before["phone"] and _s(row.get("telefon") or row.get("phones_found")):
                stats["filled_phone"] += 1
            if not before["address"] and _s(row.get("adres") or row.get("full_address")):
                stats["filled_address"] += 1
            log.info(
                "OK %s | email=%s phone=%s addr=%s | było brak=%s",
                name[:40],
                bool(_s(row.get("email_target"))),
                bool(_s(row.get("telefon") or row.get("phones_found"))),
                bool(_s(row.get("adres") or row.get("full_address"))),
                ",".join(miss),
            )
        except Exception as e:
            stats["errors"] += 1
            log.warning("FAIL %s: %s", name[:40], e)

        # Częsty zapis — nie trać postępu przy timeout GHA.
        if stats["processed"] and stats["processed"] % 5 == 0:
            scraper.save_cache(cache, log)
            scraper.save_excel(
                rows, scraper.OUTPUT_FILE, log, cache=cache, require_eligible=False
            )

    scraper.save_cache(cache, log)
    scraper.save_excel(
        rows, scraper.OUTPUT_FILE, log, cache=cache, require_eligible=False
    )
    # Po refill: uzupełnij jeszcze raz z JSON (bez kasowania).
    try:
        from scripts.verify_excel_from_json import run_verify_after_excel_save

        run_verify_after_excel_save(scraper.OUTPUT_DIR, "pl", log)
    except Exception as e:
        log.warning("verify po refill: %s", e)

    log.info(
        "REFILL done processed=%s email+%s phone+%s addr+%s errors=%s",
        stats["processed"],
        stats["filled_email"],
        stats["filled_phone"],
        stats["filled_address"],
        stats["errors"],
    )
    return stats


def main() -> int:
    parser = argparse.ArgumentParser(description="Refill braków Excel: Serper+Claude crawl")
    parser.add_argument("--limit", type=int, default=int(os.environ.get("REFILL_MISSING_LIMIT") or 40))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    stats = refill_missing(limit=args.limit, dry_run=args.dry_run)
    print(
        f"REFILL_OK candidates={stats['candidates']} processed={stats['processed']} "
        f"email+={stats['filled_email']} phone+={stats['filled_phone']} "
        f"addr+={stats['filled_address']} errors={stats['errors']}"
    )
    return 0 if stats["errors"] == 0 or stats["processed"] > 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
