# -*- coding: utf-8 -*-
"""
Buduje pełny pl_materialy_kontakte.xlsx z artefaktu Wyniki:
  - istniejący Excel
  - contacts (wszystkie, bez filtra eligible)
  - website_crawl (e-mail/telefon/nazwa ze stron)
  - claude_row_enrichment (adres/telefon/nazwa)
  - claude_page_verify (verified + łańcuchy)
Bez kolumn odpowiedzi/cen.
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

from email_targeting import is_public_portal_url  # noqa: E402

_JUNK_VERIFY_REASONS = frozenset(
    {
        "mediaportal",
        "marketplace_ogloszenia",
        "excluded_non_supplier_role",
    }
)
_JUNK_COMPANY_NAMES = frozenset(
    {
        "biuro obsługi klienta",
        "biuro obslugi klienta",
        "kontakt",
        "contact",
        "home",
        "strona główna",
        "strona glowna",
    }
)


def _s(v) -> str:
    return str(v or "").strip()


def _load_json_section(cache: dict, name: str) -> dict:
    raw = cache.get(name) or {}
    return raw if isinstance(raw, dict) else {}


def _crawl_pages(entry) -> dict:
    if entry is None:
        return {}
    if hasattr(entry, "pages"):
        pages = getattr(entry, "pages", None) or {}
        return pages if isinstance(pages, dict) else {}
    if isinstance(entry, dict):
        pages = entry.get("pages") or {}
        return pages if isinstance(pages, dict) else {}
    return {}


def _pick_company_name(names: list[str], fallback_url: str) -> str:
    ranked = sorted(
        (n for n in names if n and n.lower() not in _JUNK_COMPANY_NAMES),
        key=len,
        reverse=True,
    )
    if ranked:
        return ranked[0]
    host = fallback_url.replace("https://", "").replace("http://", "").split("/")[0]
    return host or fallback_url


def _pick_phone(phones: list[str]) -> str:
    scored: list[tuple[int, str]] = []
    for raw in phones:
        ph = _s(raw)
        if not ph:
            continue
        digits = sum(1 for c in ph if c.isdigit())
        if digits < 7:
            continue
        # odrzuć daty / ID typu 0-06-2026
        if digits <= 8 and any(y in ph for y in ("2024", "2025", "2026", "2027")):
            continue
        scored.append((digits, ph))
    if not scored:
        return ""
    scored.sort(key=lambda x: (-x[0], len(x[1])))
    return scored[0][1]


def aggregate_crawl_contact(url: str, entry) -> dict | None:
    """Z jednej witryny website_crawl → pola kontaktu (bez page_text)."""
    website = _s(url)
    if not website or is_public_portal_url(website):
        return None
    pages = _crawl_pages(entry)
    emails: list[str] = []
    phones: list[str] = []
    names: list[str] = []
    for pv in pages.values():
        if not isinstance(pv, dict):
            continue
        for e in pv.get("emails") or []:
            e = _s(e).lower()
            if e and "@" in e and e not in emails:
                emails.append(e)
        for ph in pv.get("phones") or []:
            ph = _s(ph)
            if ph and ph not in phones:
                phones.append(ph)
        cn = _s(pv.get("company_name"))
        if cn and cn not in names:
            names.append(cn)
    phone = _pick_phone(phones)
    name = _pick_company_name(names, website)
    if not emails and not phone and not (name and name != website):
        return None
    email_joined = ", ".join(emails)
    target = emails[0] if emails else ""
    return {
        "company_name_clean": name,
        "company_name": name,
        "company_name_raw": name,
        "official_website": website,
        "email_target": target,
        "emails_found": email_joined,
        "phones_found": phone,
        "phone": phone,
        "full_address": "",
        "address": "",
        "retail_verified": False,
    }


def rows_from_website_crawl(crawl: dict) -> list[dict]:
    rows: list[dict] = []
    for url, entry in (crawl or {}).items():
        info = aggregate_crawl_contact(url, entry)
        if not info:
            continue
        website = info["official_website"]
        rows.append(
            {
                "url": website,
                "www": website,
                "official_website": website,
                "nazwa": info["company_name_clean"],
                "company_name_clean": info["company_name_clean"],
                "company_name_raw": info["company_name_clean"],
                "adres": "",
                "full_address": "",
                "telefon": info["phones_found"],
                "phones_found": info["phones_found"],
                "email_target": info["email_target"],
                "emails_found": info["emails_found"],
                "retail_verified": False,
                "is_small_firm": True,
            }
        )
    return rows


def apply_crawl_to_rows(rows: list[dict], crawl: dict) -> int:
    """Uzupełnia puste e-mail/telefon/nazwę z website_crawl."""
    by_url = {}
    for r in rows:
        u = _s(r.get("url") or r.get("www") or r.get("official_website")).lower()
        if u:
            by_url[u] = r
    filled = 0
    for url, entry in (crawl or {}).items():
        info = aggregate_crawl_contact(url, entry)
        if not info:
            continue
        key = info["official_website"].lower()
        row = by_url.get(key)
        if not row:
            continue
        mapping = {
            "nazwa": info["company_name_clean"],
            "company_name_clean": info["company_name_clean"],
            "email_target": info["email_target"],
            "emails_found": info["emails_found"],
            "telefon": info["phones_found"],
            "phones_found": info["phones_found"],
            "www": info["official_website"],
            "official_website": info["official_website"],
        }
        for field, val in mapping.items():
            if val and not _s(row.get(field)):
                row[field] = val
                filled += 1
    return filled


def rows_from_enrichment(enrich: dict) -> list[dict]:
    rows: list[dict] = []
    for url, info in enrich.items():
        if not isinstance(info, dict):
            continue
        website = _s(info.get("website") or info.get("url") or url)
        if is_public_portal_url(website):
            continue
        name = _s(info.get("company_name_clean") or info.get("nazwa"))
        if not website and not name:
            continue
        phone = _s(info.get("phone") or info.get("telefon") or info.get("phones_found"))
        if "," in phone:
            phone = phone.split(",", 1)[0].strip()
        rows.append(
            {
                "url": _s(info.get("url") or website),
                "www": website,
                "official_website": website,
                "nazwa": name,
                "company_name_clean": name,
                "company_name_raw": name,
                "adres": _s(info.get("address") or info.get("adres") or info.get("full_address")),
                "full_address": _s(
                    info.get("address") or info.get("adres") or info.get("full_address")
                ),
                "telefon": phone,
                "phones_found": phone,
                "bundesland": _s(info.get("bundesland") or info.get("wojewodztwo")),
                "retail_chains_found": _s(
                    info.get("handelsketten") or info.get("retail_chains_found")
                ),
                "email_target": _s(info.get("email_target") or info.get("email")),
                "emails_found": _s(info.get("emails_found") or ""),
                "retail_verified": True,
                "is_small_firm": True,
            }
        )
    return rows


def rows_from_verified(verify: dict, *, include_unverified_suppliers: bool = True) -> list[dict]:
    """verified=true + (opcjonalnie) inne nie-portalowe z łańcuchami / GU."""
    rows: list[dict] = []
    for url, info in verify.items():
        if not isinstance(info, dict):
            continue
        website = _s(url)
        if not website or is_public_portal_url(website):
            continue
        reason = _s(info.get("verification_reason")).lower()
        verified = info.get("verified") is True
        if not verified:
            if not include_unverified_suppliers:
                continue
            if any(reason.startswith(j) or reason == j for j in _JUNK_VERIFY_REASONS):
                continue
            chains = info.get("retail_chains") or []
            has_chains = (
                bool(chains)
                if not isinstance(chains, list)
                else any(str(x).strip() for x in chains)
            )
            if not has_chains and not info.get("gu_marker") and not info.get("is_gu"):
                continue
        chains = info.get("retail_chains") or []
        if isinstance(chains, list):
            chains_s = ", ".join(str(x) for x in chains if str(x).strip())
        else:
            chains_s = _s(chains)
        claude = info.get("claude") if isinstance(info.get("claude"), dict) else {}
        name = _s(
            info.get("company_name_clean")
            or info.get("company_name")
            or claude.get("company_name")
        )
        rows.append(
            {
                "url": website,
                "www": website,
                "official_website": website,
                "nazwa": name or website,
                "company_name_clean": name or website,
                "company_name_raw": name or website,
                "adres": _s(info.get("full_address") or info.get("address")),
                "full_address": _s(info.get("full_address") or info.get("address")),
                "telefon": _s(info.get("phones_found") or info.get("phone")),
                "phones_found": _s(info.get("phones_found") or info.get("phone")),
                "bundesland": _s(info.get("bundesland")),
                "email_target": _s(info.get("email_target")),
                "emails_found": _s(info.get("emails_found")),
                "retail_chains_found": chains_s,
                "retail_verified": verified,
                "gu_marker": _s(info.get("gu_marker")),
                "is_gu": bool(info.get("is_gu")),
                "is_small_firm": bool(info.get("is_small_firm", True)),
                "verification_reason": _s(info.get("verification_reason")),
            }
        )
    return rows


def apply_enrichment_to_rows(rows: list[dict], enrich: dict) -> int:
    """Dopisuje puste pola z enrichment po URL."""
    by_url = {}
    for r in rows:
        u = _s(r.get("url") or r.get("www") or r.get("official_website")).lower()
        if u:
            by_url[u] = r
    filled = 0
    for url, info in enrich.items():
        if not isinstance(info, dict):
            continue
        key = _s(info.get("url") or info.get("website") or url).lower()
        row = by_url.get(key)
        if not row:
            continue
        mapping = {
            "nazwa": _s(info.get("company_name_clean")),
            "company_name_clean": _s(info.get("company_name_clean")),
            "adres": _s(info.get("address")),
            "full_address": _s(info.get("address")),
            "telefon": _s(info.get("phone")),
            "phones_found": _s(info.get("phone")),
            "bundesland": _s(info.get("bundesland")),
            "www": _s(info.get("website")),
            "official_website": _s(info.get("website")),
            "retail_chains_found": _s(info.get("handelsketten")),
            "email_target": _s(info.get("email_target") or info.get("email")),
        }
        for field, val in mapping.items():
            if val and not _s(row.get(field)):
                row[field] = val
                filled += 1
    return filled


def stream_slim_website_crawl(cache_path: Path, logger: logging.Logger | None = None) -> dict:
    """website_crawl bez page_text (ijson) — oszczędza RAM przy GB cache."""
    log = logger or logging.getLogger("full_excel_enriched")
    try:
        import ijson
    except ImportError:
        log.warning("ijson niedostępny — website_crawl puste")
        return {}
    out: dict = {}
    try:
        with cache_path.open("rb") as f:
            for url, entry in ijson.kvitems(f, "website_crawl"):
                if not isinstance(entry, dict):
                    continue
                pages_in = entry.get("pages") or {}
                slim_pages = {}
                if isinstance(pages_in, dict):
                    for pu, pv in pages_in.items():
                        if not isinstance(pv, dict):
                            continue
                        slim_pages[pu] = {
                            k: pv.get(k)
                            for k in ("emails", "phones", "company_name", "contact_urls")
                            if k in pv
                        }
                out[_s(url)] = {"pages": slim_pages}
    except Exception as e:
        log.warning("stream website_crawl fail: %s", e)
        return {}
    log.info("website_crawl slim: %s witryn", len(out))
    return out


def dedupe_pipeline_rows(rows: list[dict]) -> list[dict]:
    from scripts.excel_from_json_validate import normalize_url_key

    best: dict[str, dict] = {}
    order: list[str] = []
    for row in rows:
        url = _s(row.get("url") or row.get("www") or row.get("official_website"))
        nk = normalize_url_key(url) or url or f"row:{id(row)}"
        if nk not in best:
            best[nk] = dict(row)
            order.append(nk)
            continue
        cur = best[nk]
        for key, val in row.items():
            if val in (None, "", [], {}):
                continue
            if isinstance(val, str) and not val.strip():
                continue
            if cur.get(key) in (None, "", [], {}):
                cur[key] = val
    return [best[k] for k in order]


def build_full_rows(scraper, cache: dict, existing_rows: list[dict], logger: logging.Logger):
    # Wszystkie contacts — bez filtra eligible (pełny Excel).
    contacts_rows = []
    for place_url, info in (cache.get("contacts") or {}).items():
        row = scraper.row_from_cache_contact(place_url, info, require_eligible=False)
        if row:
            contacts_rows.append(row)
    enrich = _load_json_section(cache, "claude_row_enrichment")
    verify = _load_json_section(cache, "claude_page_verify")
    crawl = _load_json_section(cache, "website_crawl")
    enrich_rows = rows_from_enrichment(enrich)
    verify_rows = rows_from_verified(verify, include_unverified_suppliers=True)
    crawl_rows = rows_from_website_crawl(crawl)

    merged = scraper.merge_pipeline_rows(list(existing_rows), contacts_rows)
    merged = scraper.merge_pipeline_rows(merged, crawl_rows)
    merged = scraper.merge_pipeline_rows(merged, enrich_rows)
    merged = scraper.merge_pipeline_rows(merged, verify_rows)
    filled_en = apply_enrichment_to_rows(merged, enrich)
    filled_cr = apply_crawl_to_rows(merged, crawl)
    before = len(merged)
    merged = dedupe_pipeline_rows(merged)

    logger.info(
        "Źródła: excel=%s contacts=%s crawl=%s enrich=%s verify=%s → merged=%s "
        "(dedupe %s→%s, uzupełniono enrich=%s crawl=%s)",
        len(existing_rows),
        len(contacts_rows),
        len(crawl_rows),
        len(enrich_rows),
        len(verify_rows),
        len(merged),
        before,
        len(merged),
        filled_en,
        filled_cr,
    )
    return merged


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Pełny Excel PL z cache + crawl + enrichment + verify"
    )
    parser.add_argument("--cache", type=Path, default=Path("Wyniki/pl_materialy_cache.json"))
    parser.add_argument("--xlsx", type=Path, default=Path("Wyniki/pl_materialy_kontakte.xlsx"))
    parser.add_argument("--eligible-only", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    logger = logging.getLogger("full_excel_enriched")

    import pl_materialy_scraper as scraper
    from scripts.verify_excel_from_json import load_cache_without_website_crawl

    cache_path = args.cache
    if not cache_path.is_file():
        hits = list(Path(".").rglob("pl_materialy_cache.json"))
        if not hits:
            raise SystemExit("Brak pl_materialy_cache.json")
        cache_path = hits[0]

    xlsx_path = args.xlsx
    if not xlsx_path.is_file():
        hits = list(Path(".").rglob("pl_materialy_kontakte.xlsx"))
        if hits:
            xlsx_path = hits[0]

    scraper.CACHE_FILE = cache_path
    scraper.OUTPUT_DIR = xlsx_path.parent if xlsx_path else Path("Wyniki")
    scraper.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    scraper.OUTPUT_FILE = scraper.OUTPUT_DIR / "pl_materialy_kontakte.xlsx"

    logger.info("CACHE=%s size=%s", cache_path, cache_path.stat().st_size)
    # Bez pełnego website_crawl (page_text = GB) — slim stream + reszta z JSON.
    cache = load_cache_without_website_crawl(cache_path)
    for k in (
        "contacts",
        "claude_row_enrichment",
        "claude_page_verify",
        "website_crawl",
    ):
        cache.setdefault(k, {})
    cache["website_crawl"] = stream_slim_website_crawl(cache_path, logger)

    existing, _ = scraper.load_existing_output(scraper.OUTPUT_FILE, logger)
    if xlsx_path.is_file() and xlsx_path.resolve() != scraper.OUTPUT_FILE.resolve():
        extra, _ = scraper.load_existing_output(xlsx_path, logger)
        existing = scraper.merge_pipeline_rows(existing, extra)

    merged = build_full_rows(scraper, cache, existing, logger)
    export = scraper.build_export_rows(
        merged, logger=logger, cache=cache, require_eligible=args.eligible_only
    )
    with_mail = sum(1 for r in export if _s(r.get("E-mail")))
    with_addr = sum(1 for r in export if _s(r.get("Adres")))
    logger.info(
        "export=%s with_email=%s with_address=%s eligible=%s",
        len(export),
        with_mail,
        with_addr,
        args.eligible_only,
    )
    scraper.ENABLE_CLAUDE_ROW_CLEANUP = False
    scraper.save_excel(
        merged,
        scraper.OUTPUT_FILE,
        logger,
        cache=cache,
        require_eligible=args.eligible_only,
    )
    logger.info("WROTE %s bytes=%s", scraper.OUTPUT_FILE, scraper.OUTPUT_FILE.stat().st_size)
    # Verify już jest w workflow; lokalnie nie kasuj wierszy drugą rundą bez crawl fill.
    if (os.environ.get("VERIFY_EXCEL_AFTER_SAVE") or "1").strip().lower() not in (
        "0",
        "false",
        "no",
        "off",
    ):
        try:
            from scripts.verify_excel_from_json import run_verify_after_excel_save

            logger.info("Weryfikacja Excel vs JSON (uzupełnienie braków)…")
            run_verify_after_excel_save(scraper.OUTPUT_DIR, "pl", logger)
        except Exception as e:
            logger.warning("verify_excel_from_json pominięte: %s", e)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
