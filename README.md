# Wyszukiwarka materiałów budowlanych — Polska (PL)

Repozytorium: [wyszukiwarka-materialow-budowlanych-polska](https://github.com/Bigmax1993/wyszukiwarka-materialow-budowlanych-polska)

Kampania siostrzana (Ukraina): [wyszukiwarka-materialow-budowlanych-ukraina](https://github.com/Bigmax1993/wyszukiwarka-materialow-budowlanych-ukraina)

**Produkcja:** `pl_materialy` — hurtownie i składy budowlane w Polsce (GitHub Actions + opcjonalnie Task Scheduler PC).

---

## Pipeline

**Serper (gl=pl) → crawl www → Claude verify (PL) → Excel → maile PL**

Szczegóły: [`docs/PL_MATERIALY.md`](docs/PL_MATERIALY.md)

| Moduł | Plik |
|-------|------|
| Scraper | `pl_materialy_scraper.py` |
| Frazy per województwo | `pl_wojewodztwo_keywords.py` |
| Rotacja województw | `pl_wojewodztwo_rotation.py` |
| Filtr dostawców | `pl_materialy_supplier_filter.py` |
| Prompty Claude PL | `pl_claude_prompts.py` |
| Treść maila PL | `pl_materialy_inquiry_email_pl.py` |

Maile po polsku, tel. **516513965**, **bez załączników**.

Wyniki: `Wyniki/pl_materialy_cache.json`, `pl_materialy_kontakte.xlsx`.

---

## Szybki start

```powershell
git clone https://github.com/Bigmax1993/wyszukiwarka-materialow-budowlanych-polska.git
cd wyszukiwarka-materialow-budowlanych-polska
pip install -r requirements.txt
$env:KANBUD_PROJECT_ROOT = "$PWD\libs"

python pl_materialy_scraper.py --test
python pl_materialy_scraper.py --run-config run_config\pl_materialy.json --serper-only-discovery --no-auto-email --rotate-wojewodztwo
python pl_materialy_scraper.py --rotation-status
python pl_materialy_scraper.py --dry-run-email --send-emails-only
```

Skopiuj `.env.example` → `.env` (lokalnie; na CI ustaw [GitHub Secrets](#github-secrets)).

---

## Testy

```powershell
$env:KANBUD_PROJECT_ROOT = "$PWD\libs"
python pl_materialy_scraper.py --test
python -m unittest tests.test_pl_materialy_regression -v
python -m pytest tests/test_pl_inquiry_email_pl.py tests/test_pl_materialy_integration.py tests/test_repo_isolation.py -q
```

Pełna bateria: `powershell -ExecutionPolicy Bypass -File scripts\RUN_ALL_TESTS.ps1`

`tests/test_repo_isolation.py` — regresja: brak plików kampanii UA i `legacy/` w tym repo.

---

## Harmonogram

Szczegóły: [`schedule/pl/PLAN_5_DNI_PL.md`](schedule/pl/PLAN_5_DNI_PL.md), [`docs/GITHUB_ACTIONS.md`](docs/GITHUB_ACTIONS.md)

| Dzień | Godzina (Europe/Warsaw) | GitHub Actions |
|-------|------------------------|----------------|
| Pon–Pt | 22:00 / 20:00 / 00:00 / 01:00 / 21:00 | `PL discovery` |
| Niedziela | 10:30 | `PL niedziela backfill` |
| Poniedziałek | 11:00 / 12:00 / 14:00 | sync Drive → prep → send |
| Wtorek | 14:00 | `PL wtorek send` |

Offset +5h względem UA — pipeline PL w **osobnym repo**, bez kolizji cron.

Task Scheduler (PC):

```powershell
powershell -ExecutionPolicy Bypass -File schedule\pl\register_tasks_5_dni.ps1
```

Ręczny pełny pipeline GHA:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\run_full_pipeline_gha.ps1
```

---

## Limity

| Limit | Wartość |
|-------|---------|
| Serper | 1000 zapytań / dzień |
| E-mail | 300 / dzień, 2 / domena / dzień (pon + wt) |
| Rotacja | 1 województwo / tydzień |

---

## GitHub Actions

8 workflowów: `pl_materialy_{pi,thu,mon,tue,fri}.yml`, `sync-google-drive-pl.yml`, `tests.yml`, `ci-deploy.yml`.

Concurrency: `pl-pipeline` (w tym repo).

### GitHub Secrets

| Secret | Wymagany | Opis |
|--------|----------|------|
| `SERPER_API_KEY` | tak | API Serper |
| `ANTHROPIC_API_KEY` | tak | Claude API |
| `MAIL_USER`, `MAIL_PASSWORD` | tak (send) | SMTP / Gmail |
| `MAIL_SENDER_NAME` | tak | Maksym Świńczak |
| `GDRIVE_FOLDER_ID_PL` | tak | `1O15CdN0TH8rx74sPP5C1GuYSweX81IGw` |
| `GDRIVE_OAUTH_*` | zalecany | Upload OAuth |

**Nie ustawiaj** `GDRIVE_FOLDER_ID_UA` w tym repo.

Google Drive: [`docs/GOOGLE_DRIVE.md`](docs/GOOGLE_DRIVE.md)

---

## Struktura repo

```
├── pl_materialy_scraper.py
├── pl_wojewodztwo_rotation.py
├── run_config/pl_materialy.json
├── schedule/pl/
├── .github/workflows/pl_materialy_*.yml
├── docs/PL_MATERIALY.md
├── scripts/run_full_pipeline_gha.ps1
├── tests/test_pl_* + test_repo_isolation.py
└── Wyniki/
```
