# -*- coding: utf-8 -*-
"""
Odtwórz pl_materialy_kontakte.xlsx z pl_materialy_cache.json na Google Drive.

Problem: Excel na Drive miał tylko wiersze z małych plików .xlsx, podczas gdy
pełna baza siedzi w cache JSON. Ten skrypt:
  1) pobiera cache (+ opcjonalnie obecny Excel) z Drive
  2) buduje Excel ze WSZYSTKICH contacts (bez filtra eligible)
  3) uploaduje tylko zbiorczy .xlsx (cache zostaje na Drive)

Użycie:
  python scripts/rebuild_excel_from_drive_cache.py
  python scripts/rebuild_excel_from_drive_cache.py --dry-run
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for _p in (ROOT, ROOT / "scripts", ROOT / "libs"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import gdrive_upload_wyniki as gdrive  # noqa: E402
from campaign_data_paths import wyniki_dir, resolve_data_root  # noqa: E402

_CACHE_NAME = "pl_materialy_cache.json"
_XLSX_NAME = "pl_materialy_kontakte.xlsx"


def _find_file(service, folder_id: str, name: str) -> dict | None:
    return gdrive._find_drive_file_by_name(service, folder_id, name)


def _count_contacts_streaming(path: Path) -> int:
    """Policz contacts bez pełnego json.load (cache może mieć >1 GB)."""
    try:
        import ijson  # type: ignore
    except ImportError:
        return -1
    n = 0
    with open(path, "rb") as f:
        for _ in ijson.kvitems(f, "contacts"):
            n += 1
    return n


def _extract_slim_cache(src: Path, dest: Path, logger: logging.Logger) -> dict:
    """
    Z dużego cache bierze contacts (+ lekkie sekcje mailowe), bez website_crawl itd.
    Przy braku ijson: pełny json.load.
    """
    size_mb = src.stat().st_size / (1024 * 1024)
    try:
        import ijson  # type: ignore
    except ImportError:
        ijson = None

    if ijson is None or size_mb < 80:
        logger.info("Ładowanie pełnego JSON (%.1f MB)…", size_mb)
        with open(src, encoding="utf-8") as f:
            return json.load(f)

    logger.info(
        "Duży cache (%.1f MB) — stream ijson: tylko contacts + pola mailowe…",
        size_mb,
    )
    slim: dict = {
        "contacts": {},
        "email_daily": {},
        "email_sent_targets": {},
        "email_domain_daily": {},
        "email_suppression": {},
        "claude_row_enrichment": {},
    }
    keep_top = set(slim.keys())
    with open(src, "rb") as f:
        for key, value in ijson.kvitems(f, ""):
            if key in keep_top and isinstance(value, dict):
                slim[key] = value
                logger.info("  wczytano sekcję %s: %s pozycji", key, len(value))
    dest.parent.mkdir(parents=True, exist_ok=True)
    with open(dest, "w", encoding="utf-8") as f:
        json.dump(slim, f, ensure_ascii=False)
    logger.info("Slim cache: %s (%.1f MB)", dest, dest.stat().st_size / (1024 * 1024))
    return slim


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Excel PL ze wszystkich contacts w cache na Drive"
    )
    parser.add_argument("--folder-id", default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--eligible-only",
        action="store_true",
        help="Zastosuj filtr eligible (domyślnie: WSZYSTKIE kontakty z cache)",
    )
    parser.add_argument(
        "--max-rows",
        type=int,
        default=0,
        help="Limit wierszy do testu (0 = bez limitu)",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    logger = logging.getLogger("rebuild_excel_from_drive_cache")

    folder_id = (args.folder_id or gdrive._default_folder_id("pl")).strip()
    creds, use_oauth = gdrive._load_credentials()
    service, MediaFileUpload = gdrive._drive_service(creds)
    upload_folder = gdrive._resolve_upload_folder(
        service, folder_id, use_oauth=use_oauth
    )

    cache_meta = _find_file(service, upload_folder, _CACHE_NAME)
    if not cache_meta:
        raise SystemExit(f"Brak {_CACHE_NAME} w folderze Drive {upload_folder}")

    data_root = resolve_data_root(ROOT, campaign="pl")
    w = wyniki_dir(data_root)
    w.mkdir(parents=True, exist_ok=True)
    local_cache = w / _CACHE_NAME
    local_xlsx = w / _XLSX_NAME

    print(
        f"Pobieram {_CACHE_NAME} z Drive "
        f"(size={cache_meta.get('size', '?')} B)…"
    )
    gdrive._download_drive_file(service, cache_meta["id"], local_cache)
    print(f"Pobrano: {local_cache} ({local_cache.stat().st_size} B)")

    streamed = _count_contacts_streaming(local_cache)
    if streamed >= 0:
        print(f"contacts (stream): {streamed}")

    import pl_materialy_scraper as scraper

    # Wymuś ścieżki Wyniki w scraperze
    scraper.OUTPUT_DIR = w
    scraper.OUTPUT_FILE = local_xlsx
    scraper.CACHE_FILE = local_cache

    slim_path = w / "pl_materialy_cache_slim.json"
    cache = _extract_slim_cache(local_cache, slim_path, logger)
    # Dalszy load_cache scrapera — użyj slim jeśli powstał
    if slim_path.is_file() and slim_path.stat().st_size < local_cache.stat().st_size:
        scraper.CACHE_FILE = slim_path
        # nadpisz ścieżkę żeby save nie zapisał giganta
        local_cache = slim_path

    contacts = cache.get("contacts") or {}
    print(f"contacts w cache: {len(contacts)}")
    print(f"sekcje cache: {sorted(k for k, v in cache.items() if v)}")

    xlsx_meta = _find_file(service, upload_folder, _XLSX_NAME)
    existing_rows: list[dict] = []
    if xlsx_meta:
        with tempfile.TemporaryDirectory(prefix="pl-xlsx-") as tmp:
            remote = Path(tmp) / _XLSX_NAME
            gdrive._download_drive_file(service, xlsx_meta["id"], remote)
            existing_rows, _ = scraper.load_existing_output(remote, logger)
            print(f"Istniejący Excel na Drive: {len(existing_rows)} wierszy")

    cache_rows = scraper.build_all_rows_from_cache(cache)
    if args.max_rows and args.max_rows > 0:
        cache_rows = cache_rows[: args.max_rows]
        print(f"LIMIT testowy: {len(cache_rows)} wierszy")

    merged = scraper.merge_pipeline_rows(existing_rows, cache_rows)
    print(
        f"Pipeline: cache_rows={len(cache_rows)} + excel={len(existing_rows)} "
        f"→ merged={len(merged)}"
    )

    require_eligible = bool(args.eligible_only)
    export_preview = scraper.build_export_rows(
        merged, logger=logger, cache=cache, require_eligible=require_eligible
    )
    print(
        f"Do Excela (eligible={require_eligible}): {len(export_preview)} wierszy "
        f"(z e-mailem: {sum(1 for r in export_preview if (r.get('E-mail') or '').strip())})"
    )

    if args.dry_run:
        print("DRY-RUN: bez zapisu / uploadu")
        return 0

    scraper.save_excel(
        merged,
        local_xlsx,
        logger,
        cache=cache,
        require_eligible=require_eligible,
    )
    print(f"Zapisano lokalnie: {local_xlsx} ({local_xlsx.stat().st_size} B)")

    os.environ["GDRIVE_VERSION_XLSX"] = "0"
    os.environ["GDRIVE_APPEND_XLSX"] = "0"
    os.environ["GDRIVE_CONSOLIDATE_ALL_XLSX"] = "0"
    print(f"Upload: {_XLSX_NAME}")
    gdrive._upload_file(
        service, MediaFileUpload, local_xlsx, upload_folder, version_xlsx=False
    )
    print(
        f"Gotowe.\nhttps://drive.google.com/drive/folders/{upload_folder}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
