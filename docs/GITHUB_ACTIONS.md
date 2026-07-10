# GitHub Actions — kampania PL

Repozytorium: [wyszukiwarka-materialow-budowlanych-polska](https://github.com/Bigmax1993/wyszukiwarka-materialow-budowlanych-polska)

## Workflowy (aktywne)

| Workflow | Plik | Trigger | Co robi |
|----------|------|---------|---------|
| **Tests** | `tests.yml` | push, PR | smoke `--test` PL + regresja pytest |
| **CI Deploy** | `ci-deploy.yml` | push | smoke PL + walidacja secretów + dry-run maili PL |
| **PL discovery** | `pl_materialy_pi.yml` | cron, ręcznie | Discovery pon–pt → `pl-materialy-wyniki-pi` |
| **PL niedziela backfill** | `pl_materialy_thu.yml` | cron, ręcznie | Crawl www + Excel → `pl-materialy-wyniki-thu` |
| **PL poniedzialek prep** | `pl_materialy_mon.yml` | cron, ręcznie | Rebuild Excel → `pl-materialy-wyniki-mon` |
| **PL poniedzialek send** | `pl_materialy_tue.yml` | cron, ręcznie | Wysyłka partia 1 (do 300) → `pl-materialy-wyniki-tue` |
| **PL wtorek send** | `pl_materialy_fri.yml` | cron, ręcznie | Wysyłka partia 2 → `pl-materialy-wyniki-fri` |
| **Sync wyniki Google Drive PL** | `sync-google-drive-pl.yml` | cron pon 11:00 PL, ręcznie | Upload `Wyniki/` → folder PL |

## Harmonogram cron (Europe/Warsaw)

| Dzień | Workflow | Cron | Godzina |
|-------|----------|------|---------|
| **Poniedziałek** | discovery część 1 | `0 22 * * 1` | **22:00** |
| **Wtorek** | discovery część 2 | `0 20 * * 2` | **20:00** |
| **Czwartek** | discovery część 3 | `0 0 * * 4` | **00:00** |
| **Piątek** | discovery część 4 | `0 1 * * 5` | **01:00** |
| **Piątek** | discovery część 5 | `0 21 * * 5` | **21:00** |
| **Niedziela** | backfill | `30 10 * * 0` | **10:30** |
| **Poniedziałek** | sync Drive PL | `0 11 * * 1` | **11:00** |
| **Poniedziałek** | prep | `0 12 * * 1` | **12:00** |
| **Poniedziałek** | send 1 | `0 14 * * 1` | **14:00** |
| **Wtorek** | send 2 | `0 14 * * 2` | **14:00** |

Wysyłka w oknie **8–18** czasu warszawskiego (bez `DISABLE_SEND_WINDOW` w workflowach send).

## Sekrety

| Secret | Wymagany | Opis |
|--------|----------|------|
| `SERPER_API_KEY` | discovery | API Serper |
| `ANTHROPIC_API_KEY` | discovery + backfill | Claude API |
| `MAIL_USER` | send | SMTP |
| `MAIL_PASSWORD` | send | SMTP |
| `GDRIVE_FOLDER_ID_PL` | sync Drive | ID folderu Drive (`1O15CdN0TH8rx74sPP5C1GuYSweX81IGw`) |
| `GDRIVE_OAUTH_*` | sync Drive (OAuth) | Patrz [`GOOGLE_DRIVE.md`](GOOGLE_DRIVE.md) |

Modele Claude (domyślnie w kodzie, opcjonalnie env):

| Zadanie | Tier | Domyślny model | Env |
|---------|------|----------------|-----|
| Frazy Serper, cleanup Excel | `fast` | `claude-haiku-4-5` | `CLAUDE_MODEL_FAST` |
| Weryfikacja www, wyciąganie maili | `verify` | `claude-sonnet-4-6` | `CLAUDE_MODEL_VERIFY` |

## Artefakty

```
pon→pi | wt→pi | czw→pi | pt→pi (×2) → niedziela→thu → sync Drive PL → pon prep→mon → pon send→tue → wt send→fri
```

**PL send:** bez załącznika; telefon **516513965**; maile po polsku.

Concurrency: `pl-pipeline`.

Ręczne uruchomienie:

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
