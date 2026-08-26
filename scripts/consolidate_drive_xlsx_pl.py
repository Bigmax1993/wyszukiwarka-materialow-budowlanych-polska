# -*- coding: utf-8 -*-
"""
Jednorazowo / ręcznie: scal WSZYSTKIE Excel z folderu Google Drive PL
do jednego pl_materialy_kontakte.xlsx (append wierszy, polskie kolumny).

Użycie:
  python scripts/consolidate_drive_xlsx_pl.py
  python scripts/consolidate_drive_xlsx_pl.py --dry-run
  python scripts/consolidate_drive_xlsx_pl.py --keep-old-copies
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import gdrive_upload_wyniki as gdrive  # noqa: E402
from campaign_data_paths import resolve_data_root, wyniki_dir  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Scal wszystkie Excel z Drive PL do jednego pliku zbiorczego"
    )
    parser.add_argument("--campaign-dir", type=Path, default=ROOT)
    parser.add_argument("--folder-id", default=None)
    parser.add_argument(
        "--keep-old-copies",
        action="store_true",
        help="Nie usuwaj starych kopii z datą z Drive",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Tylko lista plików na Drive (bez pobierania/scalania)",
    )
    parser.add_argument(
        "--no-upload",
        action="store_true",
        help="Scal lokalnie, bez uploadu zbiorczego na Drive",
    )
    args = parser.parse_args()

    os.environ.setdefault("GDRIVE_CONSOLIDATE_ALL_XLSX", "1")
    os.environ.setdefault("GDRIVE_APPEND_XLSX", "1")
    os.environ.setdefault("GDRIVE_VERSION_XLSX", "0")

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    logger = logging.getLogger("consolidate_drive_xlsx_pl")

    folder_id = (args.folder_id or gdrive._default_folder_id("pl")).strip()
    creds, use_oauth = gdrive._load_credentials()
    service, MediaFileUpload = gdrive._drive_service(creds)
    upload_folder_id = gdrive._resolve_upload_folder(
        service, folder_id, use_oauth=use_oauth
    )

    files = gdrive._list_pl_kontakte_xlsx_on_drive(service, upload_folder_id)
    print(f"Folder Drive: https://drive.google.com/drive/folders/{upload_folder_id}")
    print(f"Znaleziono {len(files)} plik(ów) Excel kontaktów:")
    for f in files:
        print(f"  - {f.get('name')} ({f.get('modifiedTime')})")

    if args.dry_run:
        return 0

    data_root = resolve_data_root(args.campaign_dir, campaign="pl")
    w = wyniki_dir(data_root)
    w.mkdir(parents=True, exist_ok=True)
    canonical = w / gdrive._PL_CANONICAL_KONTAKTE_XLSX

    out, stale = gdrive.consolidate_all_kontakte_xlsx_from_drive(
        service,
        canonical,
        upload_folder_id,
        campaign="pl",
        logger=logger,
        delete_old=not args.keep_old_copies,
    )
    if out is None:
        print("Brak danych do scalenia.")
        return 1

    if args.no_upload:
        print(f"Lokalnie: {out}")
        return 0

    print(f"Upload zbiorczego: {out.name}")
    gdrive._upload_file(
        service, MediaFileUpload, out, upload_folder_id, version_xlsx=False
    )
    if stale:
        gdrive.delete_stale_kontakte_xlsx_on_drive(service, stale)
    print(
        f"Gotowe: jeden plik na Drive ({out.name}).\n"
        f"https://drive.google.com/drive/folders/{upload_folder_id}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
