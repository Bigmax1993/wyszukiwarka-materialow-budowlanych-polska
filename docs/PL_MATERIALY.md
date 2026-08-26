# Kampania PL — materiały budowlane (Polska)

Scraper B2B: hurtownie, składy i dystrybutorzy materiałów budowlanych w Polsce.

Repozytorium: [wyszukiwarka-materialow-budowlanych-polska](https://github.com/Bigmax1993/wyszukiwarka-materialow-budowlanych-polska)

| Element | Wartość |
|---------|---------|
| Scraper | `pl_materialy_scraper.py` |
| Run config | `run_config/pl_materialy.json` |
| Cache | `Wyniki/pl_materialy_cache.json` |
| Excel | `Wyniki/pl_materialy_kontakte.xlsx` |
| Drive folder | `GDRIVE_FOLDER_ID_PL` = `1O15CdN0TH8rx74sPP5C1GuYSweX81IGw` |

- Harmonogram: [schedule/pl/PLAN_5_DNI_PL.md](../schedule/pl/PLAN_5_DNI_PL.md)
- GitHub Actions: [GITHUB_ACTIONS.md](GITHUB_ACTIONS.md)
- Google Drive: [GOOGLE_DRIVE.md](GOOGLE_DRIVE.md)
- Killer prompt (cleanup wiersza): [KILLER_PROMPT_EXCEL_FILL_PL.md](KILLER_PROMPT_EXCEL_FILL_PL.md)

## Pipeline

```
Serper (gl=pl) → filtr dostawcy → crawl www → Claude verify/extract (PL)
  → cache JSON → Excel Kontakte → maile PL (bez załączników)
```

Excel **nie** jest pełnym zrzutem `website_crawl` (~setki URL). To eksport **kontaktów** (wiersze z danymi do maila), budowany z:

- `contacts` w cache
- enrichment / page verify
- opcjonalnie refill braków (Serper + crawl + Claude)
- weryfikacja `verify_excel_from_json` po zapisie

## Kolumny arkusza Kontakte (sztywno, PL)

| Kolumna | Zawartość |
|---------|-----------|
| Nazwa firmy | Oficjalna nazwa + forma prawna |
| Adres | ul. …, XX-XXX Miasto |
| Województwo | Jedno z 16 |
| Telefon | Jeden numer +48… |
| E-mail | Jeden adres firmowy |
| Strona www | `https://domena.pl` (root) |
| URL | = Strona www |
| Kategorie materiałów | cement, piasek, … |
| WWW sprawdzone / Mała firma / Generalny wykonawca | `tak` \| `nie` |
| Znacznik GU | marker lub puste |
| Status | status pipeline (`sent`, …) |

Kolumny odpowiedzi CRM / cen **nie** trafiają do Excela PL (celowo usuwane przy consolidate/upload).

Bool w Excelu: wyłącznie `tak` / `nie`.

## Uzupełnianie braków i QA

| Narzędzie | Opis |
|-----------|------|
| Killer row-cleanup | `pl_claude_prompts.build_row_cleanup_prompt` — sztywny format, zero portali/halucynacji |
| `scripts/refill_missing_excel_contacts.py` | Serper → crawl → Claude + luźniejszy regex PL |
| `scripts/verify_excel_from_json.py` | Uzupełnij puste pola z JSON cache, nadpisz Excel |
| `scripts/rebuild_excel_full_from_cache.py` | Pełny Excel z cache + enrichment + verified |
| `PL audit Excel completeness` | Drive Excel vs artefakt (contacts / xlsx) |

## Testy

```powershell
$env:KANBUD_PROJECT_ROOT = "$PWD\libs"
python pl_materialy_scraper.py --test
python -m unittest tests.test_pl_materialy_regression -v
python -m pytest tests/ -q
powershell -ExecutionPolicy Bypass -File scripts\RUN_ALL_TESTS.ps1
```

## Maile

- Język: polski
- Telefon: **516513965**
- Bez załączników
- Limity: 300/dzień, 2/domena/dzień (pon + wt)
