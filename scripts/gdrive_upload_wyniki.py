# -*- coding: utf-8 -*-
"""
Upload folderu Wyniki/ (+ opcjonalnie wyslane/) do Google Drive.

Konto usługowe nie ma własnej przestrzeni dyskowej — pliki muszą trafić na
Shared Drive (dysk zespołowy) albo upload w imieniu użytkownika (delegacja DWD).

Zmienne:
  GDRIVE_SERVICE_ACCOUNT_JSON / GDRIVE_SERVICE_ACCOUNT_FILE
  GDRIVE_FOLDER_ID — docelowy folder (domyślnie GU Bauunternehmen)
  GDRIVE_SHARED_DRIVE_ID — opcjonalnie ID dysku współdzielonego (auto-wykrywanie, jeśli puste)
  GDRIVE_IMPERSONATE_EMAIL — opcjonalnie e-mail użytkownika Workspace (domain-wide delegation)
  GDRIVE_VERSION_XLSX — 0 (domyślnie): jeden plik .xlsx, nadpisywanie po merge (append wierszy)
  GDRIVE_APPEND_XLSX — 1 (domyślnie): przed uploadem scala lokalny Excel z plikiem na Drive
  GDRIVE_CONSOLIDATE_ALL_XLSX — 1 (domyślnie dla PL): scala WSZYSTKIE Excel z folderu Drive
    do jednego pl_materialy_kontakte.xlsx (append wierszy / polskie kolumny), usuwa stare kopie

Na Google Drive trafia tylko Excel (i opcjonalnie wyslane/*.eml).
Pliki .json i .log pozostają wyłącznie w artefaktach GitHub Actions.
"""
from __future__ import annotations

import argparse
import json
import logging
import mimetypes
import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path

_PL_CANONICAL_KONTAKTE_XLSX = "pl_materialy_kontakte.xlsx"

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from campaign_data_paths import (  # noqa: E402
    GOOGLE_DRIVE_GU_FOLDER_ID,
    GOOGLE_DRIVE_PL_FOLDER_ID,
    resolve_data_root,
    wyniki_dir,
    wyslane_dir,
)

# Pełny dostęp do Drive (wymagany dla Shared Drive i nadpisywania plików).
SCOPES = ("https://www.googleapis.com/auth/drive",)

_DRIVE_API_OPTS = {
    "supportsAllDrives": True,
    "supportsTeamDrives": True,
}
_LIST_OPTS = {
    **_DRIVE_API_OPTS,
    "includeItemsFromAllDrives": True,
}

_GU_FOLDER_NAME = "GU Bauunternehmen Wyniki"

# Cache, logi i stan rotacji — tylko artefakty GitHub, nie Drive.
_GDRIVE_SKIP_SUFFIXES = frozenset({".json", ".log"})


def _skip_gdrive_upload(path: Path) -> bool:
    return path.suffix.lower() in _GDRIVE_SKIP_SUFFIXES


def _gdrive_version_xlsx_enabled() -> bool:
    raw = (os.environ.get("GDRIVE_VERSION_XLSX") or "0").strip().lower()
    return raw not in ("0", "false", "no", "off")


def _gdrive_append_xlsx_enabled() -> bool:
    raw = (os.environ.get("GDRIVE_APPEND_XLSX") or "1").strip().lower()
    return raw not in ("0", "false", "no", "off")


def _gdrive_consolidate_all_xlsx_enabled() -> bool:
    raw = (os.environ.get("GDRIVE_CONSOLIDATE_ALL_XLSX") or "1").strip().lower()
    return raw not in ("0", "false", "no", "off")


def is_pl_kontakte_xlsx_name(name: str) -> bool:
    """True dla pl_materialy_kontakte.xlsx i starych kopii z datą / aliasów."""
    low = (name or "").strip().lower()
    if not low.endswith(".xlsx"):
        return False
    if "pl_materialy" in low and "kontakte" in low:
        return True
    if low == _PL_CANONICAL_KONTAKTE_XLSX:
        return True
    if "_kontakte_" in low or low.endswith("_kontakte.xlsx"):
        return True
    return False


def _upload_stamp() -> str:
    try:
        from zoneinfo import ZoneInfo

        tz = ZoneInfo(os.environ.get("SCRAPER_TIMEZONE", "Europe/Warsaw"))
        return datetime.now(tz).strftime("%Y-%m-%d_%H%M")
    except Exception:
        return datetime.now().strftime("%Y-%m-%d_%H%M")


def versioned_xlsx_upload_name(filename: str, *, stamp: str | None = None) -> str:
    """de_gu_bauunternehmen_kontakte.xlsx → de_gu_bauunternehmen_kontakte_2026-06-08_1405.xlsx"""
    path = Path(filename)
    if path.suffix.lower() != ".xlsx":
        return path.name
    tag = stamp or _upload_stamp()
    return f"{path.stem}_{tag}{path.suffix}"


def _load_oauth_credentials():
    refresh = (os.environ.get("GDRIVE_OAUTH_REFRESH_TOKEN") or "").strip()
    if not refresh:
        return None
    client_id = (os.environ.get("GDRIVE_OAUTH_CLIENT_ID") or "").strip()
    client_secret = (os.environ.get("GDRIVE_OAUTH_CLIENT_SECRET") or "").strip()
    if not client_id or not client_secret:
        raise SystemExit(
            "Ustaw GDRIVE_OAUTH_CLIENT_ID i GDRIVE_OAUTH_CLIENT_SECRET "
            "(uruchom scripts/gdrive_oauth_setup.py)."
        )
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
    except ImportError as e:
        raise SystemExit("pip install google-auth\n" + str(e)) from e

    creds = Credentials(
        token=None,
        refresh_token=refresh,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
        scopes=list(SCOPES),
    )
    creds.refresh(Request())
    return creds


def _load_service_account_credentials():
    try:
        from google.oauth2 import service_account
    except ImportError as e:
        raise SystemExit(
            "Zainstaluj: pip install google-api-python-client google-auth\n" + str(e)
        ) from e

    raw = (os.environ.get("GDRIVE_SERVICE_ACCOUNT_JSON") or "").strip()
    path = (os.environ.get("GDRIVE_SERVICE_ACCOUNT_FILE") or "").strip()
    if raw:
        if raw.startswith("AIza"):
            raise SystemExit(
                "GDRIVE_SERVICE_ACCOUNT_JSON wyglada na klucz API (AIza...). "
                "Wklej caly plik JSON z Konta uslugi -> Klucze (type=service_account)."
            )
        try:
            info = json.loads(raw)
        except json.JSONDecodeError as e:
            raise SystemExit(
                f"GDRIVE_SERVICE_ACCOUNT_JSON nie jest poprawnym JSON: {e}. "
                "W GitHub Secrets wklej cala tresc pobranego pliku .json."
            ) from e
        if info.get("type") != "service_account" or not info.get("client_email"):
            raise SystemExit(
                "JSON musi byc kluczem konta uslugowego (type=service_account, client_email)."
            )
        creds = service_account.Credentials.from_service_account_info(info, scopes=SCOPES)
    elif path and Path(path).is_file():
        creds = service_account.Credentials.from_service_account_file(path, scopes=SCOPES)
    else:
        raise SystemExit(
            "Ustaw GDRIVE_SERVICE_ACCOUNT_JSON (treść) lub GDRIVE_SERVICE_ACCOUNT_FILE (ścieżka)."
        )

    impersonate = (os.environ.get("GDRIVE_IMPERSONATE_EMAIL") or "").strip()
    if impersonate:
        creds = creds.with_subject(impersonate)
        print(f"Delegacja DWD: upload w imieniu {impersonate}")
    return creds


def _load_credentials():
    oauth = _load_oauth_credentials()
    if oauth is not None:
        print("OAuth: upload na Twoj Dysk Google (folder udostepniony uzytkownikowi)")
        return oauth, True
    return _load_service_account_credentials(), False


def _drive_service(creds):
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload

    service = build("drive", "v3", credentials=creds, cache_discovery=False)
    return service, MediaFileUpload


def _folder_metadata(service, folder_id: str) -> dict:
    return (
        service.files()
        .get(
            fileId=folder_id,
            fields="id,name,driveId,mimeType,parents",
            **_DRIVE_API_OPTS,
        )
        .execute()
    )


def _list_shared_drives(service) -> list[dict]:
    drives: list[dict] = []
    page_token = None
    while True:
        res = (
            service.drives()
            .list(pageSize=100, pageToken=page_token, fields="nextPageToken,drives(id,name)")
            .execute()
        )
        drives.extend(res.get("drives") or [])
        page_token = res.get("nextPageToken")
        if not page_token:
            break
    return drives


def _find_folder_in_parent(service, parent_id: str, name: str) -> str | None:
    safe_name = name.replace("'", "\\'")
    q = (
        f"'{parent_id}' in parents and name = '{safe_name}' "
        f"and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
    )
    res = (
        service.files()
        .list(q=q, fields="files(id)", pageSize=1, corpora="allDrives", **_LIST_OPTS)
        .execute()
    )
    files = res.get("files") or []
    return files[0]["id"] if files else None


def _create_folder(service, parent_id: str, name: str, *, drive_id: str | None = None) -> str:
    meta: dict = {
        "name": name,
        "mimeType": "application/vnd.google-apps.folder",
        "parents": [parent_id],
    }
    if drive_id:
        meta["driveId"] = drive_id
    created = service.files().create(body=meta, fields="id", **_DRIVE_API_OPTS).execute()
    return created["id"]


def _resolve_shared_drive_upload_folder(service, preferred_folder_id: str) -> tuple[str, str]:
    """
    Zwraca (folder_id, shared_drive_id) do uploadu na Shared Drive.
    """
    configured_drive = (os.environ.get("GDRIVE_SHARED_DRIVE_ID") or "").strip()
    drives = _list_shared_drives(service)
    if configured_drive:
        drive_ids = {d["id"] for d in drives}
        if configured_drive not in drive_ids and drives:
            print(
                f"Uwaga: GDRIVE_SHARED_DRIVE_ID={configured_drive} niedostepny; "
                f"uzywam {drives[0]['name']}"
            )
            shared_drive_id = drives[0]["id"]
        elif configured_drive in drive_ids or not drives:
            shared_drive_id = configured_drive
        else:
            raise SystemExit(
                "Brak dostepnych Shared Drives dla konta uslugowego. "
                "Dodaj je jako czlonka dysku wspoldzielonego (Content manager)."
            )
    elif drives:
        shared_drive_id = drives[0]["id"]
        print(f"Shared Drive: {drives[0].get('name', shared_drive_id)}")
    else:
        raise SystemExit(
            "Konto uslugowe nie widzi zadnego Shared Drive.\n"
            "Najprosciej: uruchom na PC  python scripts/gdrive_oauth_setup.py\n"
            "(OAuth na Twoj folder — bez Shared Drive).\n"
            "Albo: dysk wspoldzielony + e-mail konta uslugowego jako Content manager."
        )

    try:
        meta = _folder_metadata(service, preferred_folder_id)
        if meta.get("driveId"):
            print(f"Folder docelowy jest na Shared Drive: {meta.get('name', preferred_folder_id)}")
            return preferred_folder_id, meta["driveId"]
    except Exception:
        pass

    existing = _find_folder_in_parent(service, shared_drive_id, _GU_FOLDER_NAME)
    if existing:
        print(f"Uzywam folderu na Shared Drive: {_GU_FOLDER_NAME} ({existing})")
        return existing, shared_drive_id

    created = _create_folder(
        service, shared_drive_id, _GU_FOLDER_NAME, drive_id=shared_drive_id
    )
    print(f"Utworzono folder na Shared Drive: {_GU_FOLDER_NAME} ({created})")
    return created, shared_drive_id


def _resolve_upload_folder(service, folder_id: str, *, use_oauth: bool) -> str:
    """Ustal folder, do którego można uploadować (OAuth / Shared Drive / impersonacja)."""
    if use_oauth:
        print(f"OAuth -> folder {folder_id}")
        return folder_id
    try:
        meta = _folder_metadata(service, folder_id)
        if meta.get("driveId"):
            print(f"Upload na Shared Drive (folder: {meta.get('name', folder_id)})")
            return folder_id
    except Exception as exc:
        print(f"Nie mozna odczytac folderu {folder_id}: {exc}")

    if (os.environ.get("GDRIVE_IMPERSONATE_EMAIL") or "").strip():
        print(f"Upload przez delegacje do folderu {folder_id}")
        return folder_id

    print(
        "Folder jest na 'Moim dysku' — konto uslugowe nie moze tam zapisywac plikow. "
        "Przelaczam na Shared Drive..."
    )
    upload_id, _drive = _resolve_shared_drive_upload_folder(service, folder_id)
    return upload_id


def _find_or_create_folder(service, parent_id: str, name: str) -> str:
    existing = _find_folder_in_parent(service, parent_id, name)
    if existing:
        return existing
    return _create_folder(service, parent_id, name)


def _upload_file(
    service,
    MediaFileUpload,
    local: Path,
    parent_id: str,
    *,
    version_xlsx: bool | None = None,
) -> str:
    mime, _ = mimetypes.guess_type(str(local))
    media = MediaFileUpload(str(local), mimetype=mime or "application/octet-stream", resumable=True)
    use_version = _gdrive_version_xlsx_enabled() if version_xlsx is None else version_xlsx
    drive_name = (
        versioned_xlsx_upload_name(local.name)
        if use_version and local.suffix.lower() == ".xlsx"
        else local.name
    )
    if use_version and local.suffix.lower() == ".xlsx":
        body = {"name": drive_name, "parents": [parent_id]}
        created = (
            service.files()
            .create(body=body, media_body=media, fields="id", **_DRIVE_API_OPTS)
            .execute()
        )
        return created["id"]

    safe_name = drive_name.replace("'", "\\'")
    q = f"'{parent_id}' in parents and name = '{safe_name}' and trashed = false"
    existing = (
        service.files()
        .list(q=q, fields="files(id)", pageSize=1, corpora="allDrives", **_LIST_OPTS)
        .execute()
        .get("files")
        or []
    )
    body = {"name": drive_name, "parents": [parent_id]}
    if existing:
        fid = existing[0]["id"]
        service.files().update(fileId=fid, media_body=media, **_DRIVE_API_OPTS).execute()
        return fid
    created = service.files().create(body=body, media_body=media, fields="id", **_DRIVE_API_OPTS).execute()
    return created["id"]


def _find_drive_file_by_name(service, parent_id: str, name: str) -> dict | None:
    safe_name = name.replace("'", "\\'")
    q = f"'{parent_id}' in parents and name = '{safe_name}' and trashed = false"
    res = (
        service.files()
        .list(q=q, fields="files(id,name)", pageSize=1, corpora="allDrives", **_LIST_OPTS)
        .execute()
    )
    files = res.get("files") or []
    return files[0] if files else None


def _download_drive_file(service, file_id: str, dest: Path) -> None:
    from googleapiclient.http import MediaIoBaseDownload

    dest.parent.mkdir(parents=True, exist_ok=True)
    request = service.files().get_media(fileId=file_id, **_DRIVE_API_OPTS)
    with open(dest, "wb") as handle:
        downloader = MediaIoBaseDownload(handle, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()


# Kanoniczne nazwy arkuszy w zbiorczym Excel PL
_SHEET_INFO = "Info"
_SHEET_KONTAKTE = "Kontakte"
_SHEET_WOJEWODZTWA = "Wojewodztwa"
_SHEET_NAME_ALIASES = {
    "info": _SHEET_INFO,
    "kontakte": _SHEET_KONTAKTE,
    "kontakty": _SHEET_KONTAKTE,
    "baza firm": _SHEET_KONTAKTE,
    "wojewodztwa": _SHEET_WOJEWODZTWA,
    "województwa": _SHEET_WOJEWODZTWA,
    "bundeslaender": _SHEET_WOJEWODZTWA,
    "bundesländer": _SHEET_WOJEWODZTWA,
}
_BOOL_EXPORT_COLS = frozenset(
    {"WWW sprawdzone", "Mała firma", "Generalny wykonawca"}
)


def _canonical_sheet_name(name: str) -> str:
    raw = str(name or "").strip()
    if not raw:
        return ""
    return _SHEET_NAME_ALIASES.get(raw.lower(), raw)


def _normalize_export_row(rec: dict, scraper) -> dict:
    """Polskie nagłówki + tak/nie; bez kolumn odpowiedzi/cen (PL materiały)."""
    libs = ROOT / "libs"
    if str(libs) not in sys.path:
        sys.path.insert(0, str(libs))
    from scraper_email_replies import is_reply_export_column

    row = scraper.normalize_excel_record_headers(rec or {})
    out: dict = {}
    for key, val in row.items():
        if str(key).startswith("_"):
            continue
        if is_reply_export_column(key):
            continue
        if key in _BOOL_EXPORT_COLS:
            parsed = scraper.parse_excel_bool(val)
            if parsed is True:
                val = scraper.EXCEL_PL_YES
            elif parsed is False:
                val = scraper.EXCEL_PL_NO
        out[key] = val
    return out


def _row_dedupe_key(sheet: str, row: dict) -> str:
    if sheet == _SHEET_KONTAKTE:
        url = str(row.get("URL") or row.get("Strona www") or "").strip().lower()
        if url:
            return f"url:{url}"
        email = str(row.get("E-mail") or "").strip().lower()
        if email:
            return f"mail:{email}"
        name = str(row.get("Nazwa firmy") or "").strip().lower()
        return f"name:{name}|{row.get('Adres') or ''}"
    if sheet == _SHEET_WOJEWODZTWA:
        url = str(row.get("URL") or row.get("Strona www") or "").strip().lower()
        if url:
            return f"url:{url}"
        return "|".join(
            str(row.get(k) or "").strip().lower()
            for k in ("Nazwa firmy", "Województwo", "Adres")
        )
    if sheet == _SHEET_INFO:
        return str(row.get("Temat") or "").strip().lower()
    return "|".join(f"{k}={row.get(k)}" for k in sorted(row.keys()))


def _merge_sheet_row(existing: dict, incoming: dict) -> dict:
    out = dict(existing)
    for key, val in incoming.items():
        if val is None or str(val).strip() == "":
            continue
        cur = out.get(key)
        if cur is None or str(cur).strip() == "":
            out[key] = val
        elif isinstance(val, str) and isinstance(cur, str) and len(val) > len(cur):
            out[key] = val
    return out


def _append_sheet_rows(
    bucket: dict[str, dict],
    sheet: str,
    rows: list[dict],
    scraper,
) -> tuple[int, int]:
    added = updated = 0
    for raw in rows:
        row = _normalize_export_row(raw, scraper)
        if not any(str(v).strip() for v in row.values()):
            continue
        key = _row_dedupe_key(sheet, row)
        if not key or key in ("url:", "mail:", "name:|"):
            key = f"anon:{len(bucket)}:{hash(tuple(sorted(row.items())))}"
        if key in bucket:
            bucket[key] = _merge_sheet_row(bucket[key], row)
            updated += 1
        else:
            bucket[key] = row
            added += 1
    return added, updated


def read_xlsx_sheets_normalized(path: Path, scraper) -> dict[str, list[dict]]:
    """Czyta wszystkie arkusze Excela i normalizuje nazwy arkuszy + kolumn na PL."""
    import pandas as pd

    out: dict[str, list[dict]] = {}
    xl = pd.ExcelFile(path)
    for name in xl.sheet_names:
        canon = _canonical_sheet_name(name)
        if not canon:
            continue
        df = pd.read_excel(path, sheet_name=name)
        rows = [
            _normalize_export_row(r, scraper)
            for r in df.fillna("").to_dict(orient="records")
        ]
        out.setdefault(canon, []).extend(rows)
    return out


def order_sheet_columns(sheet: str, rows: list[dict], scraper) -> list[dict]:
    """Unia kolumn: najpierw kanoniczne PL, potem pozostałe (bez kolumn odpowiedzi/cen)."""
    if not rows:
        return rows
    libs = ROOT / "libs"
    if str(libs) not in sys.path:
        sys.path.insert(0, str(libs))
    from scraper_email_replies import is_reply_export_column, strip_reply_export_columns

    preferred: list[str] = []
    if sheet == _SHEET_KONTAKTE:
        preferred = list(scraper.EXPORT_COLUMNS)
    elif sheet == _SHEET_WOJEWODZTWA:
        preferred = ["Nazwa firmy", "Województwo", "Adres", "Strona www", "URL"]
    elif sheet == _SHEET_INFO:
        preferred = ["Temat", "Wartość"]
    cols: list[str] = []
    seen: set[str] = set()
    for col in preferred:
        if is_reply_export_column(col):
            continue
        if any(col in r for r in rows):
            cols.append(col)
            seen.add(col)
    extras = sorted(
        {
            k
            for r in rows
            for k in r.keys()
            if k not in seen
            and not str(k).startswith("_")
            and not is_reply_export_column(k)
        }
    )
    cols.extend(extras)
    cleaned = [strip_reply_export_columns(r) for r in rows]
    return [{c: r.get(c, "") for c in cols} for r in cleaned]


def write_consolidated_xlsx(
    path: Path,
    sheets: dict[str, list[dict]],
    *,
    scraper,
    logger: logging.Logger,
) -> None:
    """Zapis zbiorczego Excela: append po arkuszach, polskie kolumny, bez filtra eligible."""
    libs = ROOT / "libs"
    if str(libs) not in sys.path:
        sys.path.insert(0, str(libs))
    from scraper_email_replies import ReplySyncConfig, write_excel_with_reply_styles

    # Info: kanoniczny opis + unikalne tematy ze źródeł
    info_bucket: dict[str, dict] = {}
    _append_sheet_rows(info_bucket, _SHEET_INFO, scraper.build_excel_info_sheet_rows(), scraper)
    _append_sheet_rows(info_bucket, _SHEET_INFO, sheets.get(_SHEET_INFO) or [], scraper)

    payload = {
        _SHEET_INFO: order_sheet_columns(
            _SHEET_INFO, list(info_bucket.values()), scraper
        ),
        _SHEET_KONTAKTE: order_sheet_columns(
            _SHEET_KONTAKTE, sheets.get(_SHEET_KONTAKTE) or [], scraper
        ),
        _SHEET_WOJEWODZTWA: order_sheet_columns(
            _SHEET_WOJEWODZTWA, sheets.get(_SHEET_WOJEWODZTWA) or [], scraper
        ),
    }
    for name, rows in sheets.items():
        if name in payload:
            continue
        payload[name] = order_sheet_columns(name, rows, scraper)

    cfg = ReplySyncConfig(
        cache_path=scraper.CACHE_FILE,
        xlsx_path=path,
        lang="pl",
        campaign_id="pl_materialy",
        main_sheet_names=(_SHEET_KONTAKTE, "Kontakty", "Baza firm"),
        include_reply_export_columns=False,
    )
    cache = {}
    try:
        if scraper.CACHE_FILE.is_file():
            cache = scraper.load_cache(logger)
    except Exception:
        cache = {}
    path.parent.mkdir(parents=True, exist_ok=True)
    write_excel_with_reply_styles(path, payload, cache, cfg, logger)
    logger.info(
        "Zbiorczy Excel: Kontakte=%s Wojewodztwa=%s Info=%s inne=%s → %s",
        len(payload[_SHEET_KONTAKTE]),
        len(payload[_SHEET_WOJEWODZTWA]),
        len(payload[_SHEET_INFO]),
        len(payload) - 3,
        path.name,
    )


def _list_pl_kontakte_xlsx_on_drive(service, folder_id: str) -> list[dict]:
    """Wszystkie pliki Excel kontaktów PL w folderze Drive (w tym kopie z datą)."""
    q = (
        f"'{folder_id}' in parents and trashed = false and "
        f"mimeType = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'"
    )
    files: list[dict] = []
    page_token = None
    while True:
        res = (
            service.files()
            .list(
                q=q,
                fields="nextPageToken, files(id,name,modifiedTime)",
                pageSize=100,
                pageToken=page_token,
                corpora="allDrives",
                **_LIST_OPTS,
            )
            .execute()
        )
        for f in res.get("files") or []:
            if is_pl_kontakte_xlsx_name(f.get("name") or ""):
                files.append(f)
        page_token = res.get("nextPageToken")
        if not page_token:
            break
    files.sort(key=lambda f: (f.get("modifiedTime") or "", f.get("name") or ""))
    return files


def _delete_drive_file(service, file_id: str, name: str = "") -> None:
    service.files().delete(fileId=file_id, **_DRIVE_API_OPTS).execute()
    print(f"  Usunięto z Drive: {name or file_id}")


def append_kontakte_xlsx_from_drive(
    service,
    local_xlsx: Path,
    drive_parent_id: str,
    *,
    campaign: str,
    logger: logging.Logger,
) -> int:
    """
    Pobiera istniejący plik *_kontakte.xlsx z Drive, scala wiersze (append po URL)
    i zapisuje z powrotem lokalnie przed uploadem.
    """
    if not _gdrive_append_xlsx_enabled():
        return 0
    if campaign != "pl" or local_xlsx.suffix.lower() != ".xlsx":
        return 0
    if not local_xlsx.is_file():
        return 0

    remote = _find_drive_file_by_name(service, drive_parent_id, local_xlsx.name)
    if not remote:
        print(f"Drive append: brak {local_xlsx.name} — pierwszy upload")
        return 0

    import pl_materialy_scraper as scraper

    with tempfile.TemporaryDirectory(prefix="gdrive-append-") as tmp:
        remote_path = Path(tmp) / local_xlsx.name
        _download_drive_file(service, remote["id"], remote_path)
        drive_rows, _ = scraper.load_existing_output(remote_path, logger)
        local_rows, _ = scraper.load_existing_output(local_xlsx, logger)
        merged = scraper.merge_pipeline_rows(drive_rows, local_rows)
        added = max(0, len(merged) - len(drive_rows))
        cache = scraper.load_cache(logger)
        scraper.save_excel(merged, local_xlsx, logger, cache=cache)
        print(
            f"Drive append: {local_xlsx.name} "
            f"Drive={len(drive_rows)} + lokalne={len(local_rows)} "
            f"→ {len(merged)} (+{added} nowych wierszy)"
        )
        return added


def consolidate_all_kontakte_xlsx_from_drive(
    service,
    local_xlsx: Path,
    drive_parent_id: str,
    *,
    campaign: str,
    logger: logging.Logger,
    delete_old: bool = True,
) -> tuple[Path | None, list[dict]]:
    """
    Pobiera WSZYSTKIE Excel kontaktów z folderu Drive, robi append na każdym arkuszu
    (unia kolumn, polskie nagłówki), zapisuje jeden lokalny pl_materialy_kontakte.xlsx.

    Zwraca (ścieżka_kanoniczna | None, lista_plików_Drive_do_usunięcia_po_uploadzie).
    """
    if campaign != "pl":
        return None, []
    if not _gdrive_consolidate_all_xlsx_enabled():
        return None, []

    import pl_materialy_scraper as scraper
    from collections import OrderedDict

    canonical = local_xlsx.with_name(_PL_CANONICAL_KONTAKTE_XLSX)
    drive_files = _list_pl_kontakte_xlsx_on_drive(service, drive_parent_id)

    sheet_buckets: dict[str, OrderedDict[str, dict]] = {
        _SHEET_INFO: OrderedDict(),
        _SHEET_KONTAKTE: OrderedDict(),
        _SHEET_WOJEWODZTWA: OrderedDict(),
    }
    loaded_names: list[str] = []

    def _ingest_path(path: Path, label: str) -> None:
        try:
            wb = read_xlsx_sheets_normalized(path, scraper)
        except Exception as e:
            print(f"  Ostrzeżenie: {label}: {e}")
            return
        counts = []
        for sheet, rows in wb.items():
            bucket = sheet_buckets.setdefault(sheet, OrderedDict())
            added, updated = _append_sheet_rows(bucket, sheet, rows, scraper)
            counts.append(f"{sheet}+{added}/~{updated}")
        loaded_names.append(f"{label}[{', '.join(counts)}]")

    if local_xlsx.parent.is_dir():
        for path in sorted(local_xlsx.parent.glob("*_kontakte*.xlsx")):
            _ingest_path(path, f"lokalny:{path.name}")
    elif canonical.is_file():
        _ingest_path(canonical, f"lokalny:{canonical.name}")

    with tempfile.TemporaryDirectory(prefix="gdrive-consolidate-") as tmp:
        tmp_path = Path(tmp)
        for f in drive_files:
            name = f.get("name") or "remote.xlsx"
            dest = tmp_path / name
            try:
                _download_drive_file(service, f["id"], dest)
                _ingest_path(dest, name)
            except Exception as e:
                print(f"  Ostrzeżenie: pominięto {name}: {e}")

    if not drive_files and not any(sheet_buckets.values()):
        print("Drive consolidate: brak plików Excel do scalenia")
        return None, []

    merged_sheets = {k: list(v.values()) for k, v in sheet_buckets.items()}
    # Gdy brak arkusza Wojewodztwa — zbuduj z Kontakte (nazwa/woj/adres/www/url)
    if not merged_sheets.get(_SHEET_WOJEWODZTWA) and merged_sheets.get(_SHEET_KONTAKTE):
        woj: list[dict] = []
        seen = set()
        for r in merged_sheets[_SHEET_KONTAKTE]:
            row = {
                "Nazwa firmy": r.get("Nazwa firmy", ""),
                "Województwo": r.get("Województwo", ""),
                "Adres": r.get("Adres", ""),
                "Strona www": r.get("Strona www", ""),
                "URL": r.get("URL", ""),
            }
            key = _row_dedupe_key(_SHEET_WOJEWODZTWA, row)
            if key in seen:
                continue
            seen.add(key)
            woj.append(row)
        merged_sheets[_SHEET_WOJEWODZTWA] = woj

    canonical.parent.mkdir(parents=True, exist_ok=True)
    write_consolidated_xlsx(canonical, merged_sheets, scraper=scraper, logger=logger)
    n_kontakte = len(merged_sheets.get(_SHEET_KONTAKTE) or [])
    print(
        f"Drive consolidate: {len(drive_files)} plik(ów) z Drive "
        f"→ {n_kontakte} wierszy Kontakte → {canonical.name}"
    )
    if loaded_names:
        print("  Źródła: " + "; ".join(loaded_names))

    stale: list[dict] = []
    if delete_old:
        stale = [
            f
            for f in drive_files
            if (f.get("name") or "") != _PL_CANONICAL_KONTAKTE_XLSX
        ]
    return canonical, stale


def delete_stale_kontakte_xlsx_on_drive(service, drive_files: list[dict]) -> int:
    """Usuwa z Drive kopie Excel inne niż kanoniczna nazwa zbiorcza."""
    stale = [
        f
        for f in drive_files
        if (f.get("name") or "") != _PL_CANONICAL_KONTAKTE_XLSX
    ]
    if not stale:
        return 0
    print(f"Usuwam {len(stale)} starych kopii Excel z Drive (zostaje jeden zbiorczy):")
    n = 0
    for f in stale:
        try:
            _delete_drive_file(service, f["id"], f.get("name") or "")
            n += 1
        except Exception as e:
            print(f"  Nie usunięto {f.get('name')}: {e}")
    return n


def merge_wyniki_xlsx_from_drive(
    service,
    wyniki: Path,
    drive_parent_id: str,
    *,
    campaign: str,
    logger: logging.Logger,
    consolidate_all: bool | None = None,
) -> list[dict]:
    """
    Scala Excel z Drive z lokalnym Wyniki/.
    Dla PL domyślnie: wszystkie pliki Excel z folderu → jeden pl_materialy_kontakte.xlsx.
    Zwraca listę plików Drive do usunięcia po udanym uploadzie zbiorczego.
    """
    if not wyniki.is_dir():
        return []
    do_all = (
        _gdrive_consolidate_all_xlsx_enabled()
        if consolidate_all is None
        else consolidate_all
    )
    if campaign == "pl" and do_all:
        _path, stale = consolidate_all_kontakte_xlsx_from_drive(
            service,
            wyniki / _PL_CANONICAL_KONTAKTE_XLSX,
            drive_parent_id,
            campaign=campaign,
            logger=logger,
            delete_old=True,
        )
        return stale

    for path in sorted(wyniki.glob("*_kontakte.xlsx")):
        append_kontakte_xlsx_from_drive(
            service,
            path,
            drive_parent_id,
            campaign=campaign,
            logger=logger,
        )
    return []


def upload_files_flat(
    service,
    MediaFileUpload,
    local_dir: Path,
    drive_parent_id: str,
    *,
    campaign: str = "gu",
) -> int:
    if not local_dir.is_dir():
        return 0
    count = 0
    for p in sorted(local_dir.iterdir()):
        if not p.is_file():
            continue
        if _skip_gdrive_upload(p):
            print(f"  SKIP {p.name} (tylko GitHub artefakt)")
            continue
        # PL: na Drive tylko jeden zbiorczy Excel (bez kopii z datą).
        if (
            campaign == "pl"
            and p.suffix.lower() == ".xlsx"
            and is_pl_kontakte_xlsx_name(p.name)
            and p.name != _PL_CANONICAL_KONTAKTE_XLSX
        ):
            print(f"  SKIP {p.name} (używamy tylko {_PL_CANONICAL_KONTAKTE_XLSX})")
            continue
        _upload_file(service, MediaFileUpload, p, drive_parent_id)
        print(f"  OK {p.name}")
        count += 1
    return count


def upload_folder_named(
    service, MediaFileUpload, local_dir: Path, drive_parent_id: str, drive_name: str
) -> int:
    if not local_dir.is_dir():
        return 0
    sub_id = _find_or_create_folder(service, drive_parent_id, drive_name)
    count = 0
    for p in sorted(local_dir.iterdir()):
        if not p.is_file():
            continue
        if _skip_gdrive_upload(p):
            print(f"  SKIP {drive_name}/{p.name} (tylko GitHub artefakt)")
            continue
        _upload_file(service, MediaFileUpload, p, sub_id)
        print(f"  OK {drive_name}/{p.name}")
        count += 1
    return count


def _default_folder_id(campaign: str) -> str:
    explicit = (os.environ.get("GDRIVE_FOLDER_ID") or "").strip()
    if explicit:
        return explicit
    if campaign == "pl":
        return (os.environ.get("GDRIVE_FOLDER_ID_PL") or GOOGLE_DRIVE_PL_FOLDER_ID).strip()
    if campaign == "ua":
        return (os.environ.get("GDRIVE_FOLDER_ID_UA") or GOOGLE_DRIVE_GU_FOLDER_ID).strip()
    return GOOGLE_DRIVE_GU_FOLDER_ID


def main() -> int:
    parser = argparse.ArgumentParser(description="Upload Wyniki do Google Drive")
    parser.add_argument(
        "--campaign-dir",
        type=Path,
        default=ROOT,
        help="Katalog kampanii (do resolve_data_root)",
    )
    parser.add_argument(
        "--campaign",
        choices=("gu", "ua", "pl"),
        default="gu",
        help="Kampania: gu | ua | pl (folder Drive / resolve_data_root)",
    )
    parser.add_argument(
        "--folder-id",
        default=None,
    )
    parser.add_argument(
        "--consolidate-all-xlsx",
        action="store_true",
        help="Wymuś scalenie wszystkich Excel z Drive do jednego pliku (PL)",
    )
    parser.add_argument(
        "--no-consolidate-all-xlsx",
        action="store_true",
        help="Wyłącz scalanie wszystkich Excel (tylko append do kanonicznej nazwy)",
    )
    args = parser.parse_args()
    folder_id = (args.folder_id or _default_folder_id(args.campaign)).strip()

    if args.consolidate_all_xlsx:
        os.environ["GDRIVE_CONSOLIDATE_ALL_XLSX"] = "1"
    if args.no_consolidate_all_xlsx:
        os.environ["GDRIVE_CONSOLIDATE_ALL_XLSX"] = "0"

    creds, use_oauth = _load_credentials()
    service, MediaFileUpload = _drive_service(creds)
    data_root = resolve_data_root(args.campaign_dir, campaign=args.campaign)
    upload_folder_id = _resolve_upload_folder(service, folder_id, use_oauth=use_oauth)
    logger = logging.getLogger("gdrive_upload")

    total = 0
    stale_to_delete: list[dict] = []
    w = wyniki_dir(data_root)
    if w.is_dir():
        stale_to_delete = merge_wyniki_xlsx_from_drive(
            service,
            w,
            upload_folder_id,
            campaign=args.campaign,
            logger=logger,
        )
        print(f"Upload plikow z {w} -> Drive {upload_folder_id}")
        total += upload_files_flat(
            service,
            MediaFileUpload,
            w,
            upload_folder_id,
            campaign=args.campaign,
        )
        if stale_to_delete and total > 0:
            delete_stale_kontakte_xlsx_on_drive(service, stale_to_delete)
    s = wyslane_dir(data_root)
    if s.is_dir():
        print(f"Upload {s} -> Drive/wyslane/")
        total += upload_folder_named(service, MediaFileUpload, s, upload_folder_id, "wyslane")

    if total == 0:
        print(
            "Brak plikow do wyslania (puste Wyniki/). "
            "Uruchom najpierw pipeline discovery/backfill/send."
        )
        return 1

    print(
        f"Zakonczono. Plikow: {total}. Folder: "
        f"https://drive.google.com/drive/folders/{upload_folder_id}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
