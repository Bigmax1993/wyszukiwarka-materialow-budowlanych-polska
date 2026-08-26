# GitHub Actions — kampania PL

Repozytorium: [wyszukiwarka-materialow-budowlanych-polska](https://github.com/Bigmax1993/wyszukiwarka-materialow-budowlanych-polska)

Kampania UA (osobne repo): [wyszukiwarka-materialow-budowlanych-ukraina](https://github.com/Bigmax1993/wyszukiwarka-materialow-budowlanych-ukraina)

## Workflowy

| Workflow | Plik | Trigger | Co robi |
|----------|------|---------|---------|
| **Tests** | `tests.yml` | push, PR | smoke PL + pytest + `test_repo_isolation` |
| **CI Deploy** | `ci-deploy.yml` | push `master`, ręcznie | smoke PL + secrets + dry-run maili |
| **PL discovery** | `pl_materialy_pi.yml` | cron, ręcznie | Discovery pon–pt → verify Excel vs JSON → `pl-materialy-wyniki-pi` |
| **PL niedziela backfill** | `pl_materialy_thu.yml` | cron, ręcznie | Crawl/verify + backfill + **refill braków** (Serper+Claude) → Drive → walidacja JSON → `pl-materialy-wyniki-thu` |
| **PL poniedzialek prep** | `pl_materialy_mon.yml` | cron, ręcznie | Rebuild Excel + verify JSON → `pl-materialy-wyniki-mon` |
| **PL poniedzialek send** | `pl_materialy_tue.yml` | cron, ręcznie | Wysyłka partia 1 (300) → `pl-materialy-wyniki-tue` |
| **PL wtorek send** | `pl_materialy_fri.yml` | cron, ręcznie | Wysyłka partia 2 → `pl-materialy-wyniki-fri` |
| **Sync wyniki Google Drive PL** | `sync-google-drive-pl.yml` | cron pon 11:00, ręcznie | Upload `Wyniki/` → folder PL |
| **PL full Excel from artifact** | `pl_full_excel_from_artifact.yml` | ręcznie | Pełny Excel z cache (**contacts + website_crawl + enrich + verify**) → Drive |
| **PL refill missing Excel contacts** | `pl_refill_missing_contacts.yml` | ręcznie | Braki e-mail/telefon/adres → Serper + crawl Claude + luźny regex → nadpisz Excel (+ Drive) |
| **PL rebuild Excel** | `pl_materialy_rebuild_excel.yml` | ręcznie | Rebuild z artefaktu + verify JSON → Drive |
| **PL consolidate Excel Drive** | `pl_consolidate_drive_xlsx.yml` | ręcznie | Scal wszystkie xlsx z folderu Drive → jeden plik PL |

Concurrency: **`pl-pipeline`** (w tym repo) — równoległe runy discovery/refill/full Excel kolejkuje się.

## Excel i JSON — reguły

1. **Jeden plik** `pl_materialy_kontakte.xlsx` na Drive (append po URL; bez kolumn odpowiedzi/cen).
2. **Kolumny tylko po polsku:** Nazwa firmy, Adres, Województwo, Telefon, E-mail, Strona www, URL, Kategorie materiałów, WWW sprawdzone, Mała firma, Generalny wykonawca, Znacznik GU, Status.
3. **Źródła wierszy:** `contacts` + **`website_crawl`** (e-mail/telefon/nazwa) + `claude_row_enrichment` + `claude_page_verify`.
4. **Po zapisie Excela** (koniec discovery / rebuild / backfill): `scripts/verify_excel_from_json.py` — porównuje z JSON, uzupełnia puste pola, **nadpisuje** plik (bez kasowania istniejących wierszy).
5. **Gdy brakuje pól w JSON/Excelu:** `scripts/refill_missing_excel_contacts.py` — Serper o firmę → crawl → Claude + `RELAXED_CONTACT_REGEX` → zapis cache + Excel.

| Skrypt | Rola |
|--------|------|
| `scripts/rebuild_excel_full_from_cache.py` | Pełny Excel z artefaktu (crawl slim bez `page_text`) |
| `scripts/verify_excel_from_json.py` | Weryfikacja / uzupełnienie vs JSON |
| `scripts/refill_missing_excel_contacts.py` | Aktywne dociągnięcie braków (API) |
| `scripts/consolidate_drive_xlsx_pl.py` | Scalenie wszystkich xlsx na Drive |

Env: `VERIFY_EXCEL_AFTER_SAVE` (`1` domyślnie przy finalnym zapisie scrapera), `RELAXED_CONTACT_REGEX=1`, `REFILL_MISSING_LIMIT` (np. `30`–`50`).

## Harmonogram cron (Europe/Warsaw)

| Dzień | Workflow | Cron | Godzina |
|-------|----------|------|---------|
| Poniedziałek | discovery 1 | `0 22 * * 1` | **22:00** |
| Wtorek | discovery 2 | `0 20 * * 2` | **20:00** |
| Czwartek | discovery 3 | `0 0 * * 4` | **00:00** |
| Piątek | discovery 4 | `0 1 * * 5` | **01:00** |
| Piątek | discovery 5 | `0 21 * * 5` | **21:00** |
| Niedziela | backfill + refill | `30 10 * * 0` | **10:30** |
| Poniedziałek | sync Drive | `0 11 * * 1` | **11:00** |
| Poniedziałek | prep | `0 12 * * 1` | **12:00** |
| Poniedziałek | send 1 | `0 14 * * 1` | **14:00** |
| Wtorek | send 2 | `0 14 * * 2` | **14:00** |

Offset +5h względem UA — osobne repozytorium, osobny `pl-pipeline`.

## Sekrety

| Secret | Wymagany | Opis |
|--------|----------|------|
| `SERPER_API_KEY` | tak | API Serper (discovery + refill) |
| `ANTHROPIC_API_KEY` | tak | Claude API (verify / extract / refill) |
| `MAIL_USER`, `MAIL_PASSWORD` | tak | SMTP |
| `MAIL_SENDER_NAME` | tak | Maksym Swinczak |
| `GDRIVE_FOLDER_ID_PL` | tak | `1O15CdN0TH8rx74sPP5C1GuYSweX81IGw` |
| `GDRIVE_OAUTH_*` | zalecany | OAuth upload |

**Nie ustawiaj** `GDRIVE_FOLDER_ID_UA` w tym repo.

## Artefakty

```
pon→pi | wt→pi | czw→pi | pt→pi (×2) → nd→thu → sync PL → pon prep→mon → pon send→tue → wt send→fri
```

Dodatkowo: `pl-materialy-full-excel-from-artifact`, `pl-materialy-wyniki-refill`, `pl-materialy-wyniki-rebuild`.

**PL send:** bez załącznika; tel. **516513965**; maile po polsku.

## Ręczne uruchomienie

```powershell
gh workflow run "CI Deploy" -R Bigmax1993/wyszukiwarka-materialow-budowlanych-polska
gh workflow run "PL discovery" -R Bigmax1993/wyszukiwarka-materialow-budowlanych-polska
gh workflow run "PL discovery" -R Bigmax1993/wyszukiwarka-materialow-budowlanych-polska -f discovery_phase=mon
gh workflow run "PL niedziela backfill" -R Bigmax1993/wyszukiwarka-materialow-budowlanych-polska
gh workflow run "PL full Excel from GitHub artifact" -R Bigmax1993/wyszukiwarka-materialow-budowlanych-polska
gh workflow run "PL refill missing Excel contacts" -R Bigmax1993/wyszukiwarka-materialow-budowlanych-polska -f limit=30 -f upload_drive=true
gh workflow run "Sync wyniki Google Drive PL" -R Bigmax1993/wyszukiwarka-materialow-budowlanych-polska
gh workflow run "PL poniedzialek prep" -R Bigmax1993/wyszukiwarka-materialow-budowlanych-polska
gh workflow run "PL poniedzialek send" -R Bigmax1993/wyszukiwarka-materialow-budowlanych-polska -f force_resend=true
gh workflow run "PL wtorek send" -R Bigmax1993/wyszukiwarka-materialow-budowlanych-polska -f force_resend=true
```

Lokalnie (refill / pełny Excel):

```powershell
python scripts/rebuild_excel_full_from_cache.py
python scripts/verify_excel_from_json.py --campaign pl --wyniki Wyniki
$env:RELAXED_CONTACT_REGEX="1"
python scripts/refill_missing_excel_contacts.py --limit 20
# albo:
python pl_materialy_scraper.py --refill-missing-contacts --limit 20
```

Pełny łańcuch: `scripts/run_full_pipeline_gha.ps1`

Harmonogram PC: [`schedule/pl/PLAN_5_DNI_PL.md`](../schedule/pl/PLAN_5_DNI_PL.md)  
Kampania: [`docs/PL_MATERIALY.md`](PL_MATERIALY.md) · Drive: [`docs/GOOGLE_DRIVE.md`](GOOGLE_DRIVE.md)
