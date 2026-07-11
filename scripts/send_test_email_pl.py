# -*- coding: utf-8 -*-
"""Jednorazowa wysyłka testowa PL (Claude + SMTP)."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "libs") not in sys.path:
    sys.path.insert(0, str(ROOT / "libs"))

from scraper_run_config import apply_run_config_file, load_run_config_file  # noqa: E402

import pl_materialy_scraper as scraper  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Wyślij jeden testowy mail kampanii PL")
    parser.add_argument("--to", required=True, help="Adres odbiorcy")
    parser.add_argument(
        "--company",
        default="Test Bud Sp. z o.o.",
        help="Nazwa firmy do personalizacji treści",
    )
    parser.add_argument(
        "--run-config",
        default="run_config/pl_materialy.json",
        help="Plik run_config kampanii PL",
    )
    args = parser.parse_args()

    data = load_run_config_file(args.run_config, ROOT)
    apply_run_config_file(scraper, args.run_config, ROOT)
    scraper.apply_pl_run_config_extras(scraper, data)

    logger = scraper.setup_logging()
    cache = scraper.load_cache(logger)
    contact_info = {
        "company_name": args.company,
        "company_name_clean": args.company,
        "url": "https://example-bud.pl",
        "wojewodztwo": "mazowieckie",
        "adres": "ul. Testowa 1, 00-001 Warszawa",
        "page_snippet": "Generalny wykonawca — budownictwo mieszkaniowe i komercyjne.",
    }

    subject, body = scraper.generate_email_content(
        args.company,
        logger,
        cache=cache,
        contact_info=contact_info,
        place_url="https://example-bud.pl",
    )
    print(f"Temat: {subject}")
    print(f"Tresc (poczatek): {body[:240].replace(chr(10), ' ')}...")

    ok, info = scraper.send_email_pl_materialy(args.to, subject, body, logger)
    if not ok:
        raise SystemExit(f"BLAD wysylki: {info}")
    print(f"OK: wyslano na {args.to} ({info})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
