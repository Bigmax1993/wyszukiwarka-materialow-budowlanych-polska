# GitHub Actions — kampania PL

Repozytorium: [wyszukiwarka-materialow-budowlanych-polska](https://github.com/Bigmax1993/wyszukiwarka-materialow-budowlanych-polska)

Kampania UA (osobne repo): [wyszukiwarka-materialow-budowlanych-ukraina](https://github.com/Bigmax1993/wyszukiwarka-materialow-budowlanych-ukraina)

## Workflowy (8)

| Workflow | Plik | Trigger | Co robi |
|----------|------|---------|---------|
| **Tests** | `tests.yml` | push, PR | smoke PL + pytest + `test_repo_isolation` |
| **CI Deploy** | `ci-deploy.yml` | push | smoke PL + secrets + dry-run maili |
| **PL discovery** | `pl_materialy_pi.yml` | cron, ręcznie | Discovery pon–pt → `pl-materialy-wyniki-pi` |
| **PL niedziela backfill** | `pl_materialy_thu.yml` | cron, ręcznie | Crawl www + Excel → `pl-materialy-wyniki-thu` |
| **PL poniedzialek prep** | `pl_materialy_mon.yml` | cron, ręcznie | Rebuild Excel → `pl-materialy-wyniki-mon` |
| **PL poniedzialek send** | `pl_materialy_tue.yml` | cron, ręcznie | Wysyłka partia 1 (300) → `pl-materialy-wyniki-tue` |
| **PL wtorek send** | `pl_materialy_fri.yml` | cron, ręcznie | Wysyłka partia 2 → `pl-materialy-wyniki-fri` |
| **Sync wyniki Google Drive PL** | `sync-google-drive-pl.yml` | cron pon 11:00, ręcznie | Upload `Wyniki/` → folder PL |

## Harmonogram cron (Europe/Warsaw)

| Dzień | Workflow | Cron | Godzina |
|-------|----------|------|---------|
| Poniedziałek | discovery 1 | `0 22 * * 1` | **22:00** |
| Wtorek | discovery 2 | `0 20 * * 2` | **20:00** |
| Czwartek | discovery 3 | `0 0 * * 4` | **00:00** |
| Piątek | discovery 4 | `0 1 * * 5` | **01:00** |
| Piątek | discovery 5 | `0 21 * * 5` | **21:00** |
| Niedziela | backfill | `30 10 * * 0` | **10:30** |
| Poniedziałek | sync Drive | `0 11 * * 1` | **11:00** |
| Poniedziałek | prep | `0 12 * * 1` | **12:00** |
| Poniedziałek | send 1 | `0 14 * * 1` | **14:00** |
| Wtorek | send 2 | `0 14 * * 2` | **14:00** |

Offset +5h względem UA — osobne repozytorium, osobny `pl-pipeline`.

## Sekrety

| Secret | Wymagany | Opis |
|--------|----------|------|
| `SERPER_API_KEY` | tak | API Serper |
| `ANTHROPIC_API_KEY` | tak | Claude API |
| `MAIL_USER`, `MAIL_PASSWORD` | tak | SMTP |
| `MAIL_SENDER_NAME` | tak | Maksym Swinczak |
| `GDRIVE_FOLDER_ID_PL` | tak | `1O15CdN0TH8rx74sPP5C1GuYSweX81IGw` |
| `GDRIVE_OAUTH_*` | zalecany | OAuth upload |

**Nie ustawiaj** `GDRIVE_FOLDER_ID_UA` w tym repo.

## Artefakty

```
pon→pi | wt→pi | czw→pi | pt→pi (×2) → nd→thu → sync PL → pon prep→mon → pon send→tue → wt send→fri
```

**PL send:** bez załącznika; tel. **516513965**; maile po polsku.

## Ręczne uruchomienie

```powershell
gh workflow run "PL discovery" -R Bigmax1993/wyszukiwarka-materialow-budowlanych-polska
gh workflow run "PL discovery" -R Bigmax1993/wyszukiwarka-materialow-budowlanych-polska -f discovery_phase=mon
gh workflow run "PL niedziela backfill" -R Bigmax1993/wyszukiwarka-materialow-budowlanych-polska
gh workflow run "Sync wyniki Google Drive PL" -R Bigmax1993/wyszukiwarka-materialow-budowlanych-polska
gh workflow run "PL poniedzialek prep" -R Bigmax1993/wyszukiwarka-materialow-budowlanych-polska
gh workflow run "PL poniedzialek send" -R Bigmax1993/wyszukiwarka-materialow-budowlanych-polska -f force_resend=true
gh workflow run "PL wtorek send" -R Bigmax1993/wyszukiwarka-materialow-budowlanych-polska -f force_resend=true
```

Pełny łańcuch: `scripts/run_full_pipeline_gha.ps1`

Harmonogram PC: [`schedule/pl/PLAN_5_DNI_PL.md`](../schedule/pl/PLAN_5_DNI_PL.md)  
Kampania: [`docs/PL_MATERIALY.md`](PL_MATERIALY.md)
