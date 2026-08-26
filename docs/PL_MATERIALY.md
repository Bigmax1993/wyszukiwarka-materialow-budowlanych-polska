# Kampania PL — materiały budowlane (Polska)

Scraper B2B: hurtownie, składy i dystrybutorzy materiałów budowlanych w Polsce.

Repozytorium: [wyszukiwarka-materialow-budowlanych-polska](https://github.com/Bigmax1993/wyszukiwarka-materialow-budowlanych-polska)

| Element | Wartość |
|---------|---------|
| Scraper | `pl_materialy_scraper.py` |
| Run config | `run_config/pl_materialy.json` |
| Cache | `Wyniki/pl_materialy_cache.json` |
| Excel | `Wyniki/pl_materialy_kontakte.xlsx` (kolumny tylko PL) |
| Drive | `GDRIVE_FOLDER_ID_PL` = `1O15CdN0TH8rx74sPP5C1GuYSweX81IGw` |

Harmonogram: [schedule/pl/PLAN_5_DNI_PL.md](../schedule/pl/PLAN_5_DNI_PL.md)  
GitHub Actions: [docs/GITHUB_ACTIONS.md](GITHUB_ACTIONS.md) · Drive: [docs/GOOGLE_DRIVE.md](GOOGLE_DRIVE.md)

## Pipeline

```
Serper (gl=pl) → filtr dostawcy → discovery (pon–pt)
  → crawl www + Claude verify
  → Excel (contacts + website_crawl + enrich)
  → verify_excel_from_json (uzupełnij braki z JSON, nadpisz)
  → [opcjonalnie] refill_missing (Serper + Claude + luźny regex)
  → Drive / maile PL
```

### Flagi CLI (skraper)

| Flaga | Opis |
|-------|------|
| `--serper-only-discovery` | Discovery bez wysyłki |
| `--rebuild-from-cache` | Excel z cache (+ verify po zapisie) |
| `--backfill-emails-from-cache` | Przelicz e-maile w contacts |
| `--verify-pending-contacts` | Ponowna weryfikacja www |
| `--refill-missing-contacts [--limit N]` | Braki pól → Serper + crawl + Claude |

### Excel

- Jeden arkusz **Kontakte** z polskimi nagłówkami (bez kolumn odpowiedzi/cen).
- Pełny rebuild: `python scripts/rebuild_excel_full_from_cache.py`
- Weryfikacja vs JSON: `python scripts/verify_excel_from_json.py --campaign pl`

## Testy

```powershell
python pl_materialy_scraper.py --test
python -m pytest tests/ -q
```

Ważniejsze testy regresji Excel/JSON: `test_excel_from_json_validate`, `test_excel_polish_headers`, `test_relaxed_contact_regex`, `test_pl_materialy_integration`.

## Maile

- Język: polski
- Telefon: **516513965**
- Bez załączników
- Limity: 300/dzień, 2/domena/dzień
