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


def _wyniki_dir(art: Path) -> Path:
    return art / "Wyniki" if (art / "Wyniki").is_dir() else art


def _artifact_roots(src: Path) -> list[Path]:
    if not src.is_dir():
        return []
    has_payload = (
        any(src.glob("*_cache.json"))
        or any(src.glob("*.xlsx"))
        or (src / "Wyniki").is_dir()
    )
    if has_payload:
        return [src]
    return sorted(p for p in src.iterdir() if p.is_dir())


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


def collect_raw_contacts(src: Path, logger: logging.Logger) -> dict[str, dict]:
    merged: dict[str, dict] = {}
    seen_xlsx: set[Path] = set()
    for art in _artifact_roots(src):
        wdir = _wyniki_dir(art)
        for cache_path in wdir.glob("*_cache.json"):
            contacts = recover_contacts_from_cache_file(cache_path)
            logger.info("%s: contacts=%s", cache_path.name, len(contacts))
            merged = merge_contacts_maps(merged, contacts)
        for xlsx in list(wdir.glob("*.xlsx")) + list(art.glob("*.xlsx")):
            resolved = xlsx.resolve()
            if resolved in seen_xlsx:
                continue
            seen_xlsx.add(resolved)
            rows, _ = scraper.load_existing_output(xlsx, logger)
            excel_contacts = {}
            for row in rows:
                url = _cell(row.get("url") or row.get("www") or row.get("official_website"))
                if not url:
                    continue
                excel_contacts[url] = pipeline_row_as_info(row)
            logger.info("%s: excel_rows=%s", xlsx.name, len(excel_contacts))
            merged = merge_contacts_maps(merged, excel_contacts)
    logger.info("JSON+Excel z %s: %s contacts", src, len(merged))
    return merged


def filter_needed_contacts(merged: dict[str, dict], logger: logging.Logger) -> dict[str, dict]:
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
        "JSON po filtrze: %s contacts, z tego %s z danymi do Excela",
        len(merged),
        len(needed),
    )
    return needed


def collect_contacts(src: Path, logger: logging.Logger) -> dict[str, dict]:
    return filter_needed_contacts(collect_raw_contacts(src, logger), logger)


def load_state_contacts(path: Path) -> dict[str, dict]:
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    if isinstance(data, dict) and isinstance(data.get("contacts"), dict):
        return data["contacts"]
    return data if isinstance(data, dict) else {}


def save_state_contacts(path: Path, contacts: dict[str, dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"contacts": contacts}, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )


def copy_supporting_files(src: Path, wyniki: Path, wyslane: Path, logger: logging.Logger) -> None:
    wyniki.mkdir(parents=True, exist_ok=True)
    wyslane.mkdir(parents=True, exist_ok=True)
    dest_cache = wyniki / "pl_materialy_cache.json"
    best_cache: tuple[int, Path] | None = None
    if dest_cache.is_file():
        best_cache = (dest_cache.stat().st_size, dest_cache)
    best_rot: Path | None = None
    eml_n = 0
    for art in _artifact_roots(src):
        wdir = _wyniki_dir(art)
        sdir = art / "wyslane"
        for cache_path in wdir.glob("*_cache.json"):
            size = cache_path.stat().st_size
            if cache_path.resolve() == dest_cache.resolve():
                continue
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
    if best_cache and best_cache[1].resolve() != dest_cache.resolve():
        shutil.copy2(best_cache[1], dest_cache)
        logger.info("Cache bazowy: %s (%s MB)", dest_cache.name, best_cache[0] // (1024 * 1024))
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


def finish_excel(contacts: dict[str, dict], wyniki: Path, logger: logging.Logger) -> int:
    if not contacts:
        raise SystemExit("Brak contacts JSON z danymi do Excela")
    cache_path = wyniki / "pl_materialy_cache.json"
    cache = overlay_merged_contacts_into_cache(cache_path, contacts)
    logger.info("Zapisano scalony contacts JSON obok cache")
    xlsx = wyniki / "pl_materialy_kontakte.xlsx"
    n_rows, gaps = write_validated_excel(contacts, xlsx, cache, logger)
    if gaps:
        print(f"VERIFY_FAIL rows={n_rows} gaps={len(gaps)}")
        for g in gaps[:20]:
            print(f"  {g['url']}: {g['reason']} {g['columns']}")
        return 1
    print(f"VERIFY_OK rows={n_rows} contacts_json={len(contacts)} file={xlsx}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--src", type=Path, help="Katalog z rozpakowanymi artefaktami")
    parser.add_argument("--state", type=Path, help="Plik stanu scalonych contacts JSON")
    parser.add_argument("--ingest", action="store_true", help="Dolacz jeden artefakt do stanu i zakoncz")
    parser.add_argument(
        "--from-state",
        nargs="?",
        const=True,
        default=False,
        help="Zbuduj Excel ze stanu JSON (opcjonalnie sciezka zamiast --state)",
    )
    parser.add_argument("--wyniki", type=Path, default=ROOT / "Wyniki")
    parser.add_argument("--wyslane", type=Path, default=ROOT / "wyslane")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    logger = logging.getLogger("rebuild_excel_all")

    if args.ingest:
        if not args.src or not args.state:
            raise SystemExit("--ingest wymaga --src i --state")
        copy_supporting_files(args.src, args.wyniki, args.wyslane, logger)
        merged = merge_contacts_maps(
            load_state_contacts(args.state),
            collect_raw_contacts(args.src, logger),
        )
        save_state_contacts(args.state, merged)
        print(f"INGEST_OK contacts={len(merged)} state={args.state}")
        return 0

    if args.from_state:
        state_path = args.state
        if args.from_state is not True:
            state_path = Path(args.from_state)
        if not state_path:
            raise SystemExit("--from-state wymaga --state albo sciezki")
        contacts = filter_needed_contacts(load_state_contacts(state_path), logger)
        return finish_excel(contacts, args.wyniki, logger)

    if not args.src:
        raise SystemExit("Podaj --src albo --from-state")
    copy_supporting_files(args.src, args.wyniki, args.wyslane, logger)
    contacts = collect_contacts(args.src, logger)
    return finish_excel(contacts, args.wyniki, logger)


if __name__ == "__main__":
    raise SystemExit(main())
