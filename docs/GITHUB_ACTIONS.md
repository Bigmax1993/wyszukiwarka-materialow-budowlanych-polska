# GitHub Actions — kampania PL

Repozytorium: [wyszukiwarka-materialow-budowlanych-polska](https://github.com/Bigmax1993/wyszukiwarka-materialow-budowlanych-polska)

Kampania UA (osobne repo): [wyszukiwarka-materialow-budowlanych-ukraina](https://github.com/Bigmax1993/wyszukiwarka-materialow-budowlanych-ukraina)

Concurrency: grupa **`pl-pipeline`** (kolejne joby PL czekają / nie kasują się wzajemnie agresywnie — `cancel-in-progress: false` na większości).

## Workflowy produkcyjne (harmonogram)

| Workflow | Plik | Trigger | Co robi |
|----------|------|---------|---------|
| **Tests** | `tests.yml` | push, PR | smoke PL + pytest + izolacja repo |
| **CI Deploy** | `ci-deploy.yml` | push `master`, ręcznie | smoke + secrets + dry-run maili |
| **PL discovery** | `pl_materialy_pi.yml` | cron, ręcznie | Discovery pon–pt → artefakt `pl-materialy-wyniki-pi` |
| **PL niedziela backfill** | `pl_materialy_thu.yml` | cron, ręcznie | Crawl + Excel → Drive → walidacja → `pl-materialy-wyniki-thu` |
| **PL poniedzialek prep** | `pl_materialy_mon.yml` | cron, ręcznie | Rebuild Excel → `pl-materialy-wyniki-mon` |
| **PL poniedzialek send** | `pl_materialy_tue.yml` | cron, ręcznie | Wysyłka partia 1 → `pl-materialy-wyniki-tue` |
| **PL wtorek send** | `pl_materialy_fri.yml` | cron, ręcznie | Wysyłka partia 2 → `pl-materialy-wyniki-fri` |
| **Sync wyniki Google Drive PL** | `sync-google-drive-pl.yml` | cron pon 11:00, ręcznie | Upload `Wyniki/` → folder PL |
| **PL sync odpowiedzi i przypomnienia** | `pl_materialy_reminders.yml` | cron / ręcznie | IMAP odpowiedzi + remindery |

## Workflowy utrzymania Excela / Drive (ręcznie)

| Workflow | Plik | Co robi |
|----------|------|---------|
| **PL rebuild Excel** | `pl_materialy_rebuild_excel.yml` | Rebuild z artefaktu + verify JSON + opcjonalny upload Drive |
| **PL rebuild Excel from Drive cache** | `pl_rebuild_excel_from_drive_cache.yml` | Pełny Excel z `pl_materialy_cache.json` na Drive |
| **PL full Excel from GitHub artifact** | `pl_full_excel_from_artifact.yml` | Excel z contacts + enrichment + verified (artefakt GHA) |
| **PL refill missing Excel contacts** | `pl_refill_missing_contacts.yml` | Uzupełnij braki: Serper + crawl + Claude + regex PL |
| **PL audit Excel completeness** | `pl_audit_excel_completeness.yml` | Porównaj Drive Excel vs artefakt (contacts / URL) |
| **PL consolidate Excel Drive** | `pl_consolidate_drive_xlsx.yml` | Scal wszystkie xlsx w folderze → jeden PL |
| **PL list Drive Excel** | `pl_list_drive_files.yml` | Lista plików w folderze Drive |
| **Restore Drive Excel before date** | `gdrive_restore_xlsx_before.yml` | Przywróć starszą wersję Excela |
| **PL backfill wyslane IMAP** | `pl_backfill_wyslane_imap.yml` | Backfill wysłanych `.eml` |
| **PL test email (jednorazowo)** | `pl_materialy_test_email.yml` | Jednorazowy test SMTP |

Dokumentacja kampanii / kolumn: [PL_MATERIALY.md](PL_MATERIALY.md) · killer cleanup: [KILLER_PROMPT_EXCEL_FILL_PL.md](KILLER_PROMPT_EXCEL_FILL_PL.md)

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
gh workflow run "CI Deploy" -R Bigmax1993/wyszukiwarka-materialow-budowlanych-polska
gh workflow run "PL discovery" -R Bigmax1993/wyszukiwarka-materialow-budowlanych-polska
gh workflow run "PL discovery" -R Bigmax1993/wyszukiwarka-materialow-budowlanych-polska -f discovery_phase=mon
gh workflow run "PL niedziela backfill" -R Bigmax1993/wyszukiwarka-materialow-budowlanych-polska
gh workflow run "Sync wyniki Google Drive PL" -R Bigmax1993/wyszukiwarka-materialow-budowlanych-polska
gh workflow run "PL poniedzialek prep" -R Bigmax1993/wyszukiwarka-materialow-budowlanych-polska
gh workflow run "PL poniedzialek send" -R Bigmax1993/wyszukiwarka-materialow-budowlanych-polska -f force_resend=true
gh workflow run "PL wtorek send" -R Bigmax1993/wyszukiwarka-materialow-budowlanych-polska -f force_resend=true

# Excel / Drive QA
gh workflow run "PL refill missing Excel contacts" -R Bigmax1993/wyszukiwarka-materialow-budowlanych-polska
gh workflow run "PL rebuild Excel" -R Bigmax1993/wyszukiwarka-materialow-budowlanych-polska -f upload_drive=true
gh workflow run "PL full Excel from GitHub artifact" -R Bigmax1993/wyszukiwarka-materialow-budowlanych-polska
gh workflow run "PL audit Excel completeness" -R Bigmax1993/wyszukiwarka-materialow-budowlanych-polska
gh workflow run "PL consolidate Excel Drive" -R Bigmax1993/wyszukiwarka-materialow-budowlanych-polska
```

Pełny łańcuch: `scripts/run_full_pipeline_gha.ps1`

Harmonogram PC: [`schedule/pl/PLAN_5_DNI_PL.md`](../schedule/pl/PLAN_5_DNI_PL.md)
