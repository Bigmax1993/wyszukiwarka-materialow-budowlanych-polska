# -*- coding: utf-8 -*-
"""
Upload folderu Wyniki/ (+ opcjonalnie wyslane/) do Google Drive.

Wymaga konta usługi Google (JSON) z dostępem do folderu:
  https://drive.google.com/drive/folders/1tP8oUi72t4EHDbE9GnHFdvfNtNsJe4xf

Użycie:
  set GDRIVE_SERVICE_ACCOUNT_JSON=C:\\path\\service-account.json
  set KANBUD_DATA_DIR=G:\\My Drive\\GU Bauunternehmen Wyniki
  python scripts/gdrive_upload_wyniki.py

GitHub Actions: secret GDRIVE_SERVICE_ACCOUNT_JSON (cała treść JSON).
"""
from __future__ import annotations

import argparse
import json
import mimetypes
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from campaign_data_paths import (  # noqa: E402
    GOOGLE_DRIVE_GU_FOLDER_ID,
    resolve_data_root,
    wyniki_dir,
    wyslane_dir,
)

SCOPES = ("https://www.googleapis.com/auth/drive.file",)


def _load_credentials():
    try:
        from google.oauth2 import service_account
    except ImportError as e:
        raise SystemExit(
            "Zainstaluj: pip install google-api-python-client google-auth\n" + str(e)
        ) from e

    raw = (os.environ.get("GDRIVE_SERVICE_ACCOUNT_JSON") or "").strip()
    path = (os.environ.get("GDRIVE_SERVICE_ACCOUNT_FILE") or "").strip()
    if raw:
        info = json.loads(raw)
        return service_account.Credentials.from_service_account_info(info, scopes=SCOPES)
    if path and Path(path).is_file():
        return service_account.Credentials.from_service_account_file(path, scopes=SCOPES)
    raise SystemExit(
        "Ustaw GDRIVE_SERVICE_ACCOUNT_JSON (treść) lub GDRIVE_SERVICE_ACCOUNT_FILE (ścieżka)."
    )


def _drive_service(creds):
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload

    service = build("drive", "v3", credentials=creds, cache_discovery=False)
    return service, MediaFileUpload


def _find_or_create_folder(service, parent_id: str, name: str) -> str:
    q = (
        f"'{parent_id}' in parents and name = '{name.replace(chr(39), '')}' "
        f"and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
    )
    res = service.files().list(q=q, fields="files(id)", pageSize=1).execute()
    files = res.get("files") or []
    if files:
        return files[0]["id"]
    meta = {"name": name, "mimeType": "application/vnd.google-apps.folder", "parents": [parent_id]}
    created = service.files().create(body=meta, fields="id").execute()
    return created["id"]


def _upload_file(service, MediaFileUpload, local: Path, parent_id: str) -> str:
    mime, _ = mimetypes.guess_type(str(local))
    media = MediaFileUpload(str(local), mimetype=mime or "application/octet-stream", resumable=True)
    q = f"'{parent_id}' in parents and name = '{local.name}' and trashed = false"
    existing = service.files().list(q=q, fields="files(id)", pageSize=1).execute().get("files") or []
    body = {"name": local.name, "parents": [parent_id]}
    if existing:
        fid = existing[0]["id"]
        service.files().update(fileId=fid, media_body=media).execute()
        return fid
    created = service.files().create(body=body, media_body=media, fields="id").execute()
    return created["id"]


def upload_files_flat(service, MediaFileUpload, local_dir: Path, drive_parent_id: str) -> int:
    """Pliki z Wyniki/ bezpośrednio do folderu Drive (json, xlsx, log)."""
    if not local_dir.is_dir():
        return 0
    count = 0
    for p in sorted(local_dir.iterdir()):
        if p.is_file():
            _upload_file(service, MediaFileUpload, p, drive_parent_id)
            print(f"  OK {p.name}")
            count += 1
    return count


def upload_folder_named(
    service, MediaFileUpload, local_dir: Path, drive_parent_id: str, drive_name: str
) -> int:
    """Podfolder na Drive (np. wyslane/)."""
    if not local_dir.is_dir():
        return 0
    sub_id = _find_or_create_folder(service, drive_parent_id, drive_name)
    count = 0
    for p in sorted(local_dir.iterdir()):
        if p.is_file():
            _upload_file(service, MediaFileUpload, p, sub_id)
            print(f"  OK {drive_name}/{p.name}")
            count += 1
    return count


def main() -> int:
    parser = argparse.ArgumentParser(description="Upload Wyniki do Google Drive")
    parser.add_argument(
        "--campaign-dir",
        type=Path,
        default=ROOT / "Gu Baunterhnehmen",
        help="Katalog kampanii (do resolve_data_root)",
    )
    parser.add_argument(
        "--folder-id",
        default=os.environ.get("GDRIVE_FOLDER_ID", GOOGLE_DRIVE_GU_FOLDER_ID),
    )
    args = parser.parse_args()

    creds = _load_credentials()
    service, MediaFileUpload = _drive_service(creds)
    data_root = resolve_data_root(args.campaign_dir)
    folder_id = args.folder_id

    total = 0
    w = wyniki_dir(data_root)
    if w.is_dir():
        print(f"Upload plikow z {w} -> Drive {folder_id}")
        total += upload_files_flat(service, MediaFileUpload, w, folder_id)
    s = wyslane_dir(data_root)
    if s.is_dir():
        print(f"Upload {s} -> Drive/wyslane/")
        total += upload_folder_named(service, MediaFileUpload, s, folder_id, "wyslane")

    print(f"Zakonczono. Plikow: {total}. Folder: https://drive.google.com/drive/folders/{folder_id}")
    return 0 if total >= 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
