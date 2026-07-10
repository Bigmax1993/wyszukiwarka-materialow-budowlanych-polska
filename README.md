# Wyszukiwarka materiałów budowlanych — Polska

Repozytorium: [wyszukiwarka-materialow-budowlanych-polska](https://github.com/Bigmax1993/wyszukiwarka-materialow-budowlanych-polska)

**Kampania produkcyjna:** PL materiały — hurtownie i składy budowlane w Polsce (GitHub Actions).

## Kampania PL

Pipeline: **Serper (gl=pl) → crawl www → Claude verify (PL) → Excel → maile PL**.

Szczegóły: [`docs/PL_MATERIALY.md`](docs/PL_MATERIALY.md)

| Moduł | Plik |
|-------|------|
| Scraper | `pl_materialy_scraper.py` |
| Frazy per województwo | `pl_wojewodztwo_keywords.py` |
| Rotacja województw | `pl_wojewodztwo_rotation.py` |
| Filtr dostawców | `pl_materialy_supplier_filter.py` |
| Prompty Claude PL | `pl_claude_prompts.py` |
| Contact extract PL | `pl_claude_contact_extract.py` |
| Treść maila PL | `pl_materialy_inquiry_email_pl.py` |

```powershell
git clone https://github.com/Bigmax1993/wyszukiwarka-materialow-budowlanych-polska.git
cd wyszukiwarka-materialow-budowlanych-polska
pip install -r requirements.txt
$env:KANBUD_PROJECT_ROOT = "$PWD\libs"

python pl_materialy_scraper.py --test
python pl_materialy_scraper.py --run-config run_config\pl_materialy.json --serper-only-discovery --no-auto-email --rotate-wojewodztwo
python pl_materialy_scraper.py --run-config run_config\pl_materialy.json --rebuild-from-cache
python pl_materialy_scraper.py --rotation-status
python pl_materialy_scraper.py --dry-run-email --send-emails-only
```

Testy:

```powershell
python -m unittest tests.test_pl_materialy_regression -v
python -m pytest tests/test_pl_materialy_integration.py tests/test_pl_inquiry_email_pl.py -q
powershell -ExecutionPolicy Bypass -File scripts\RUN_ALL_TESTS.ps1
```

Maile po polsku, tel. **516513965**. **Bez załączników**.

Wyniki: `Wyniki/pl_materialy_cache.json`, `pl_materialy_kontakte.xlsx`.

## Harmonogram (GitHub Actions + PC)

Szczegóły: [`schedule/pl/PLAN_5_DNI_PL.md`](schedule/pl/PLAN_5_DNI_PL.md), [`docs/GITHUB_ACTIONS.md`](docs/GITHUB_ACTIONS.md)

| Dzień | Godzina (Europe/Warsaw) | GitHub Actions |
|-------|------------------------|----------------|
| **Pon–Pt** | 22:00 / 20:00 / 00:00 / 01:00 / 21:00 | `PL discovery` |
| **Niedziela** | 10:30 | `PL niedziela backfill` |
| **Poniedziałek** | 11:00 / 12:00 / 14:00 | sync Drive → prep → send |
| **Wtorek** | 14:00 | `PL wtorek send` |

Task Scheduler (PC):

```powershell
powershell -ExecutionPolicy Bypass -File schedule\pl\register_tasks_5_dni.ps1
```

Ręczny pełny pipeline GHA:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\run_full_pipeline_gha.ps1
```

## Struktura repo

```
├── pl_materialy_scraper.py
├── pl_wojewodztwo_rotation.py
├── run_config/pl_materialy.json
├── schedule/pl/
├── .github/workflows/pl_materialy_*.yml
├── docs/PL_MATERIALY.md
└── tests/test_pl_*
```
