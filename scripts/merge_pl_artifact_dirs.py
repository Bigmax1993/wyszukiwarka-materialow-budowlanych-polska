# -*- coding: utf-8 -*-
"""Scala Wyniki + wyslane z kilku pobranych artefaktów pipeline PL."""
from __future__ import annotations

import argparse
import logging
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pl_materialy_scraper as scraper  # noqa: E402


def _copy_eml(src: Path, dest: Path) -> int:
    dest.mkdir(parents=True, exist_ok=True)
    n = 0
    if not src.is_dir():
        return 0
    for p in src.rglob("*.eml"):
        if not p.is_file():
            continue
        target = dest / p.name
        if not target.exists() or p.stat().st_size > target.stat().st_size:
            shutil.copy2(p, target)
            n += 1
    return n


def merge_artifact_dirs(src: Path, wyniki: Path, wyslane: Path, logger: logging.Logger) -> None:
    wyniki.mkdir(parents=True, exist_ok=True)
    wyslane.mkdir(parents=True, exist_ok=True)
    merged_rows: list[dict] = []
    best_cache: Path | None = None
    best_cache_size = -1
    best_rotation: Path | None = None
    eml_copied = 0

    for art in sorted(p for p in src.iterdir() if p.is_dir()):
        wdir = art / "Wyniki" if (art / "Wyniki").is_dir() else art
        sdir = art / "wyslane"
        logger.info("Merge z %s", art.name)
        for xlsx in sorted(wdir.glob("*_kontakte.xlsx")):
            rows, _ = scraper.load_existing_output(xlsx, logger)
            before = len(merged_rows)
            merged_rows = scraper.merge_pipeline_rows(merged_rows, rows)
            logger.info("  %s: +%s (razem %s)", xlsx.name, len(merged_rows) - before, len(merged_rows))
        for cache in wdir.glob("*_cache.json"):
            size = cache.stat().st_size
            if size > best_cache_size:
                best_cache = cache
                best_cache_size = size
        for rot in wdir.glob("*_rotation.json"):
            best_rotation = rot
        eml_copied += _copy_eml(sdir, wyslane)

    if not merged_rows:
        raise SystemExit("Brak wierszy Excel do scalenia — puste artefakty?")

    out_xlsx = wyniki / "pl_materialy_kontakte.xlsx"
    cache_obj = scraper.load_cache(logger) if best_cache is None else None
    if best_cache is not None:
        shutil.copy2(best_cache, wyniki / best_cache.name)
        logger.info("Cache: %s (%s MB)", best_cache.name, best_cache_size // (1024 * 1024))
        try:
            cache_obj = scraper.load_cache(logger)
        except Exception:
            cache_obj = None
    if best_rotation is not None:
        shutil.copy2(best_rotation, wyniki / best_rotation.name)
    scraper.save_excel(merged_rows, out_xlsx, logger, cache=cache_obj)
    logger.info("Excel: %s wierszy → %s", len(merged_rows), out_xlsx)
    logger.info("Skopiowano .eml: %s", eml_copied)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--src", type=Path, required=True)
    parser.add_argument("--wyniki", type=Path, required=True)
    parser.add_argument("--wyslane", type=Path, required=True)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    merge_artifact_dirs(args.src, args.wyniki, args.wyslane, logging.getLogger("merge_pl"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
