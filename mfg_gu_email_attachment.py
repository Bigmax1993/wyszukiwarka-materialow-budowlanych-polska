# -*- coding: utf-8 -*-
"""
Stały załącznik PPTX do maili MFG (DE Ost + GU bundesweit).

Źródło (Google Slides):
  https://docs.google.com/presentation/d/12h0_knRQVTU9sRg9kqh8dxjSiuuKx0TA/edit

Kolejność szukania pliku:
  1. MFG_EMAIL_ATTACHMENT_PATH (env)
  2. Lokalny cache w Wyniki/ (po eksporcie z Drive API)
  3. C:\\Users\\kanbu\\Documents\\Prezentacja\\MFG_Moderner Fliesenboden.pptx
  4. Pobranie z Google Drive API (Slides → PPTX), jeśli GDRIVE_SERVICE_ACCOUNT_JSON
"""
from __future__ import annotations

import io
import logging
import os
from pathlib import Path

GOOGLE_SLIDES_PRESENTATION_ID = "12h0_knRQVTU9sRg9kqh8dxjSiuuKx0TA"
GOOGLE_SLIDES_URL = (
    "https://docs.google.com/presentation/d/"
    f"{GOOGLE_SLIDES_PRESENTATION_ID}/edit"
)

ATTACHMENT_FILENAME = "MFG_Referenzliste_Einzelhandel.pptx"
LEGACY_ATTACHMENT_PATH = Path(
    r"C:\Users\kanbu\Documents\Prezentacja\MFG_Moderner Fliesenboden.pptx"
)

DRIVE_READONLY_SCOPES = ("https://www.googleapis.com/auth/drive.readonly",)
PPTX_MIME = "application/vnd.openxmlformats-officedocument.presentationml.presentation"


def _env_attachment_path() -> Path | None:
    raw = (os.environ.get("MFG_EMAIL_ATTACHMENT_PATH") or "").strip()
    if not raw:
        return None
    p = Path(raw).expanduser()
    return p if p.is_file() else None


def _cache_attachment_path(campaign_dir: Path) -> Path:
    from campaign_data_paths import resolve_data_root, wyniki_dir

    root = resolve_data_root(campaign_dir)
    return wyniki_dir(root) / ATTACHMENT_FILENAME


def _download_slides_pptx(dest: Path, logger: logging.Logger | None = None) -> bool:
    """Eksport Google Slides → PPTX (konto usługi z dostępem do prezentacji)."""
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaIoBaseDownload
    except ImportError:
        if logger:
            logger.warning("Brak google-api-python-client — nie pobrano PPTX ze Slides.")
        return False

    import json

    raw = (os.environ.get("GDRIVE_SERVICE_ACCOUNT_JSON") or "").strip()
    path = (os.environ.get("GDRIVE_SERVICE_ACCOUNT_FILE") or "").strip()
    creds = None
    if raw:
        info = json.loads(raw)
        creds = service_account.Credentials.from_service_account_info(
            info, scopes=DRIVE_READONLY_SCOPES
        )
    elif path and Path(path).is_file():
        creds = service_account.Credentials.from_service_account_file(
            path, scopes=DRIVE_READONLY_SCOPES
        )
    if creds is None:
        return False

    dest.parent.mkdir(parents=True, exist_ok=True)
    service = build("drive", "v3", credentials=creds, cache_discovery=False)
    request = service.files().export_media(
        fileId=GOOGLE_SLIDES_PRESENTATION_ID,
        mimeType=PPTX_MIME,
    )
    buffer = io.BytesIO()
    downloader = MediaIoBaseDownload(buffer, request)
    done = False
    while not done:
        _status, done = downloader.next_chunk()
    dest.write_bytes(buffer.getvalue())
    if logger:
        logger.info(
            "Pobrano załącznik ze Slides → %s (%.1f MB)",
            dest,
            dest.stat().st_size / (1024 * 1024),
        )
    return dest.is_file() and dest.stat().st_size > 1000


def resolve_mfg_email_attachment(campaign_dir: Path) -> Path | None:
    """Zwraca ścieżkę do PPTX lub None."""
    env_p = _env_attachment_path()
    if env_p:
        return env_p
    cache_p = _cache_attachment_path(campaign_dir)
    if cache_p.is_file():
        return cache_p
    if LEGACY_ATTACHMENT_PATH.is_file():
        return LEGACY_ATTACHMENT_PATH
    return None


def ensure_mfg_email_attachment(
    campaign_dir: Path,
    logger: logging.Logger | None = None,
) -> Path | None:
    """
    Gwarantuje lokalny PPTX — pobiera ze Slides, jeśli trzeba.
    Zwraca Path lub None (wysyłka powinna się wtedy nie udać).
    """
    existing = resolve_mfg_email_attachment(campaign_dir)
    if existing:
        return existing

    cache_p = _cache_attachment_path(campaign_dir)
    if _download_slides_pptx(cache_p, logger):
        return cache_p

    if logger:
        logger.error(
            "Brak załącznika PPTX. Udostępnij Slides %s kontu usługi Google "
            "lub ustaw MFG_EMAIL_ATTACHMENT_PATH / umieść plik w %s",
            GOOGLE_SLIDES_URL,
            LEGACY_ATTACHMENT_PATH,
        )
    return None
