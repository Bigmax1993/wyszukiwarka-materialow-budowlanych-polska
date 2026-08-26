# Google Drive — wyniki kampanii PL

## Kampania PL (materiały budowlane) — produkcja

Folder w chmurze: [PL Materialy Budowlane](https://drive.google.com/drive/folders/1O15CdN0TH8rx74sPP5C1GuYSweX81IGw)

| Secret | Opis |
|--------|------|
| `GDRIVE_FOLDER_ID_PL` | ID folderu Drive (`1O15CdN0TH8rx74sPP5C1GuYSweX81IGw`) |

| Plik / folder | Gdzie |
|---------------|--------|
| `pl_materialy_kontakte.xlsx` | **Google Drive** (jeden plik — append wierszy, bez kopii z datą) |
| `wyslane/*.eml` | **Google Drive** (kopie wysłanych maili) |
| `pl_materialy_cache.json` | **GitHub Actions** (artefakt `pl-materialy-wyniki-*`) + zwykle też na Drive |
| `pl_materialy_scraper.log` | **GitHub Actions** (artefakt) |
| `pl_materialy_wojewodztwo_rotation.json` | **GitHub Actions** (artefakt) |

| Sposób | Kiedy |
|--------|--------|
| **GitHub Actions** | Niedzielny backfill (`PL niedziela backfill`): upload → weryfikacja Excel vs JSON → ponowny upload. Dodatkowo poniedziałek 11:00 `Sync wyniki Google Drive PL`. |
| **Ręcznie (GHA)** | `PL rebuild Excel`, `PL refill missing Excel contacts`, `PL consolidate Excel Drive`, `PL audit Excel completeness` |
| **Lokalnie** | `python scripts/gdrive_upload_wyniki.py --campaign pl` |
| **PC + Drive for desktop** | `KANBUD_DATA_DIR` → folder `PL Materialy Budowlane Wyniki` |

Artefakt źródłowy sync: `pl-materialy-wyniki-thu` (niedzielny backfill). Szczegóły: [`docs/GITHUB_ACTIONS.md`](GITHUB_ACTIONS.md).

### Excel — jeden plik, append

| Zmienna | Domyślnie | Opis |
|---------|-----------|------|
| `GDRIVE_VERSION_XLSX` | `0` | Bez kopii z datą — zawsze ten sam `pl_materialy_kontakte.xlsx` |
| `GDRIVE_APPEND_XLSX` | `1` | Przed uploadem: pobierz Excel z Drive, dopisz nowe wiersze (po URL), nadpisz plik |
| `GDRIVE_CONSOLIDATE_ALL_XLSX` | `1` | **Scala wszystkie** Excel z folderu Drive do jednego zbiorczego; nagłówki wyłącznie po polsku; usuwa stare kopie |

Jednorazowe scalenie:

```powershell
pip install -r requirements-drive.txt
python scripts/consolidate_drive_xlsx_pl.py
python scripts/consolidate_drive_xlsx_pl.py --dry-run
```

### Kolumny arkusza Kontakte (PL)

Nazwa firmy, Adres, Województwo, Telefon, E-mail, Strona www, URL, Kategorie materiałów, WWW sprawdzone, Mała firma, Generalny wykonawca, Znacznik GU, Status.

Wartości bool: **`tak` / `nie`**.

**Bez kolumn CRM** (odpowiedź, cena, status maila, …) — przy consolidate/upload są usuwane (`is_reply_export_column`).

Sztywny cleanup wiersza (Claude): [KILLER_PROMPT_EXCEL_FILL_PL.md](KILLER_PROMPT_EXCEL_FILL_PL.md).

Stare pliki `pl_materialy_kontakte_2026-*_*.xlsx` są usuwane automatycznie przy consolidate.

### Co Excel zawiera, a czego nie

| Źródło | W Excelu? |
|--------|-----------|
| Kontakty z e-mailem (pipeline export) | tak |
| Enrichment / verified firmy | często (po rebuild/full excel) |
| Pełny `website_crawl` (setki URL bez kontaktu) | **nie** — to nie jest dump crawla |

Audyt kompletności (Drive vs artefakt): workflow **PL audit Excel completeness**.

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
| **Kolejność fallback** | `thu` → `mon` → `tue` → `fri` → `pi` |

Lokalny skrypt `scripts/upload_wyniki_to_drive.ps1` używa tej samej kolejności artefaktów co workflow CI.
