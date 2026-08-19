# -*- coding: utf-8 -*-
"""
Pobiera (juz sciagniete) artefakty GHA, scala cache JSON, buduje jeden Excel,
waliduje vs JSON (uzupelnia braki w petli) i zapisuje Wyniki/.
"""
from __future__ import annotations

import argparse
import json
import logging
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.excel_from_json_validate import (  # noqa: E402
    fill_export_from_json,
    json_contact_has_needed_data,
    merge_contacts_maps,
    pipeline_row_from_json,
    verify_and_fill_until_complete,
)
from scripts.recover_pi_cache_contacts import recover_contacts_from_cache_file  # noqa: E402

import pl_materialy_scraper as scraper  # noqa: E402
from libs.scraper_email_replies import ReplySyncConfig, write_excel_with_reply_styles  # noqa: E402


def _iter_artifact_dirs(src: Path) -> list[Path]:
    return sorted(p for p in src.iterdir() if p.is_dir())


def _wyniki_dir(art: Path) -> Path:
    return art / "Wyniki" if (art / "Wyniki").is_dir() else art


def collect_contacts(src: Path, logger: logging.Logger) -> dict[str, dict]:
    merged: dict[str, dict] = {}
    for art in _iter_artifact_dirs(src):
        wdir = _wyniki_dir(art)
        for cache_path in wdir.glob("*_cache.json"):
            contacts = recover_contacts_from_cache_file(cache_path)
            logger.info("%s: contacts=%s", cache_path.name, len(contacts))
            merged = merge_contacts_maps(merged, contacts)
    needed = {}
    for url, info in merged.items():
        if not json_contact_has_needed_data(url, info):
            continue
        if scraper.is_public_portal_url(url) or scraper.is_public_portal_url(
            (info or {}).get("official_website") or ""
        ):
            continue
        needed[url] = info
    logger.info(
        "JSON po scaleniu: %s contacts, z tego %s z danymi do Excela",
        len(merged),
        len(needed),
    )
    return needed


def copy_supporting_files(src: Path, wyniki: Path, wyslane: Path, logger: logging.Logger) -> None:
    wyniki.mkdir(parents=True, exist_ok=True)
    wyslane.mkdir(parents=True, exist_ok=True)
    best_cache: tuple[int, Path] | None = None
    best_rot: Path | None = None
    eml_n = 0
    for art in _iter_artifact_dirs(src):
        wdir = _wyniki_dir(art)
        sdir = art / "wyslane"
        for cache_path in wdir.glob("*_cache.json"):
            size = cache_path.stat().st_size
            if best_cache is None or size > best_cache[0]:
                best_cache = (size, cache_path)
        for rot in wdir.glob("*_rotation.json"):
            best_rot = rot
        if sdir.is_dir():
            for eml in sdir.rglob("*.eml"):
                dest = wyslane / eml.name
                if not dest.exists() or eml.stat().st_size > dest.stat().st_size:
                    shutil.copy2(eml, dest)
                    eml_n += 1
    if best_cache:
        dest = wyniki / "pl_materialy_cache.json"
        shutil.copy2(best_cache[1], dest)
        logger.info("Cache bazowy: %s (%s MB)", dest.name, best_cache[0] // (1024 * 1024))
    if best_rot:
        shutil.copy2(best_rot, wyniki / best_rot.name)
    logger.info("Skopiowano .eml: %s", eml_n)


def write_validated_excel(
    contacts: dict[str, dict],
    xlsx_path: Path,
    cache: dict,
    logger: logging.Logger,
) -> tuple[int, list[dict]]:
    rows = [pipeline_row_from_json(url, info) for url, info in contacts.items()]
    export_rows = scraper.build_export_rows(
        rows, logger=logger, cache=cache, require_eligible=False
    )
    export_rows, n_fill = fill_export_from_json(contacts, export_rows)
    logger.info("Uzupelnienie z JSON (runda 0): %s zmian", n_fill)
    export_rows, gaps, rounds = verify_and_fill_until_complete(contacts, export_rows)
    logger.info("Weryfikacja po %s rundach: luk=%s, wierszy=%s", rounds, len(gaps), len(export_rows))
    if gaps:
        export_rows, n_fill = fill_export_from_json(contacts, export_rows)
        logger.info("Doliczona runda: +%s zmian, ponowna weryfikacja", n_fill)
        export_rows, gaps, _ = verify_and_fill_until_complete(contacts, export_rows)
    state_rows = scraper.build_bundesland_rows(rows)
    cfg = ReplySyncConfig(
        cache_path=scraper.CACHE_FILE,
        xlsx_path=xlsx_path,
        lang="pl",
        campaign_id="pl_materialy",
    )
    sheets = {
        "Info": scraper.build_excel_info_sheet_rows(),
        "Kontakte": export_rows,
        "Wojewodztwa": state_rows,
    }
    write_excel_with_reply_styles(xlsx_path, sheets, cache, cfg, logger)

    extra_rounds = 0
    gaps_after: list[dict] = []
    loaded_export = export_rows
    for disk_round in range(5):
        loaded, _ = scraper.load_existing_output(xlsx_path, logger)
        loaded_export = scraper.build_export_rows(
            loaded, logger=logger, cache=cache, require_eligible=False
        )
        loaded_export, gaps_after, fill_rounds = verify_and_fill_until_complete(
            contacts, loaded_export
        )
        extra_rounds += fill_rounds
        if fill_rounds or gaps_after:
            logger.warning(
                "Po odczycie dysku (runda %s) uzupelniono JSON: rund=%s luki=%s — zapis",
                disk_round + 1,
                fill_rounds,
                len(gaps_after),
            )
            write_excel_with_reply_styles(
                xlsx_path,
                {
                    "Info": scraper.build_excel_info_sheet_rows(),
                    "Kontakte": loaded_export,
                    "Wojewodztwa": state_rows,
                },
                cache,
                cfg,
                logger,
            )
            if fill_rounds:
                continue
        break
    logger.info(
        "Weryfikacja koncowa: wierszy=%s luki=%s rund_dysku=%s",
        len(loaded_export),
        len(gaps_after),
        extra_rounds,
    )
    return len(loaded_export), gaps_after


def overlay_merged_contacts_into_cache(cache_path: Path, contacts: dict[str, dict]) -> dict:
    """Zostawia duzy cache z artefaktu; dopisuje scalony contacts do osobnego JSON."""
    sidecar = cache_path.with_name("pl_materialy_contacts_merged.json")
    sidecar.write_text(
        json.dumps({"contacts": contacts}, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    return {"contacts": contacts}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--src", type=Path, required=True, help="Katalog z rozpakowanymi artefaktami")
    parser.add_argument("--wyniki", type=Path, default=ROOT / "Wyniki")
    parser.add_argument("--wyslane", type=Path, default=ROOT / "wyslane")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    logger = logging.getLogger("rebuild_excel_all")

    copy_supporting_files(args.src, args.wyniki, args.wyslane, logger)
    contacts = collect_contacts(args.src, logger)
    if not contacts:
        raise SystemExit("Brak contacts JSON z danymi do Excela")

    cache_path = args.wyniki / "pl_materialy_cache.json"
    cache = overlay_merged_contacts_into_cache(cache_path, contacts)
    logger.info("Zapisano scalony contacts JSON obok cache")
    xlsx = args.wyniki / "pl_materialy_kontakte.xlsx"
    n_rows, gaps = write_validated_excel(contacts, xlsx, cache, logger)
    if gaps:
        print(f"VERIFY_FAIL rows={n_rows} gaps={len(gaps)}")
        for g in gaps[:20]:
            print(f"  {g['url']}: {g['reason']} {g['columns']}")
        return 1
    print(f"VERIFY_OK rows={n_rows} contacts_json={len(contacts)} file={xlsx}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
