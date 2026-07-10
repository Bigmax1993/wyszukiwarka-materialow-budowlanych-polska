# Google Drive — wyniki kampanii PL

## Kampania PL (materiały budowlane) — produkcja

Folder w chmurze: [PL Materialy Budowlane](https://drive.google.com/drive/folders/1O15CdN0TH8rx74sPP5C1GuYSweX81IGw)

| Secret | Opis |
|--------|------|
| `GDRIVE_FOLDER_ID_PL` | ID folderu Drive (`1O15CdN0TH8rx74sPP5C1GuYSweX81IGw`) |

| Plik / folder | Opis |
|---------------|------|
| `pl_materialy_cache.json` | Cache (wersja `pl_enrichment_v2`) |
| `pl_materialy_kontakte.xlsx` | Excel kontaktów |
| `pl_materialy_scraper.log` | Log |
| `pl_materialy_wojewodztwo_rotation.json` | Stan rotacji województw |
| `wyslane/*.eml` | Kopie wysłanych maili |

| Sposób | Kiedy |
|--------|--------|
| **GitHub Actions** | Workflow `Sync wyniki Google Drive PL` (poniedziałek 11:00 Europe/Warsaw) |
| **Lokalnie** | `python scripts/gdrive_upload_wyniki.py --campaign pl` |
| **PC + Drive for desktop** | `KANBUD_DATA_DIR` → folder `PL Materialy Budowlane Wyniki` |

Artefakt źródłowy sync: `pl-materialy-wyniki-thu` (niedzielny backfill). Szczegóły: [`docs/GITHUB_ACTIONS.md`](GITHUB_ACTIONS.md).

### Upload z GitHub Actions (OAuth)

```powershell
pip install -r requirements-drive.txt
python scripts/gdrive_oauth_setup.py
```

Skrypt ustawi secrets `GDRIVE_OAUTH_*`. Kolejne runy CI uploadują na folder PL.

## Stała reguła sync (GitHub Actions)

| Reguła | Wartość |
|--------|---------|
| **Kiedy** | **Poniedziałek 11:00** (Europe/Warsaw) |
| **Cron** | `0 11 * * 1` |
| **Źródło danych** | Artefakt **`pl-materialy-wyniki-thu`** |
| **Kolejność fallback** | `thu` → `mon` → `tue` → `fri` |

Lokalny skrypt `scripts/upload_wyniki_to_drive.ps1` używa tej samej kolejności artefaktów co workflow CI.
