# Wyszukiwarka partnerów — kampania GU (bundesweit)

Repozytorium: [Bigmax1993/Wyszukiwarka-partnerow](https://github.com/Bigmax1993/Wyszukiwarka-partnerow) (private)

Zawiera **wyłącznie** kampanię **GU Bauunternehmen** (Generalunternehmer / Filialbau DE, Serper → www → Excel → maile MFG).

**Moduł główny:** `de_gu_bauunternehmen_scraper.py`  
**Słowa kluczowe:** `de_gu_keywords.py` (frazy per Bundesland)  
**Wykluczenia MFG:** `de_contractor_exclusions.py`

## Szybki start (lokalnie)

```powershell
git clone https://github.com/Bigmax1993/Wyszukiwarka-partnerow.git
cd Wyszukiwarka-partnerow
pip install -r requirements.txt
$env:KANBUD_PROJECT_ROOT = "$PWD\libs"
python de_gu_bauunternehmen_scraper.py --test
```

## Różnice względem DE Ost

| | DE Ost | GU bundesweit |
|---|--------|----------------|
| Geo | BB / SN / TH | cała DE (fale po Bundesland) |
| Frazy Serper | Ost + miasta | per Bundesland (fala 1: NRW, BY, BW) |
| Cel kontaktów | 70 | **150** |
| Gemini (www/Excel) | włączone | **wyłączone** |
| Pliki wyników | `de_ost_*` | `de_gu_bauunternehmen_*` |

## Wyniki

| Plik / folder | Opis |
|---------------|------|
| `Wyniki/de_gu_bauunternehmen_cache.json` | Cache Serper + kontakty |
| `Wyniki/de_gu_bauunternehmen_kontakte.xlsx` | Excel |
| `Wyniki/de_gu_bauunternehmen_scraper.log` | Log |
| `wyslane/` | Kopie wysłanych maili (.eml) |

**Google Drive:** [folder wyników GU](https://drive.google.com/drive/folders/1tP8oUi72t4EHDbE9GnHFdvfNtNsJe4xf) — instrukcja: [`docs/GOOGLE_DRIVE.md`](docs/GOOGLE_DRIVE.md)

## Uruchomienie scrapera

```powershell
$env:KANBUD_PROJECT_ROOT = "$PWD\libs"

python de_gu_bauunternehmen_scraper.py --test
python de_gu_bauunternehmen_scraper.py --run-config run_config\welle_nrw_by_bw.json
python de_gu_bauunternehmen_scraper.py --backfill-emails-from-cache
python de_gu_bauunternehmen_scraper.py --send-emails-only
python de_gu_bauunternehmen_scraper.py --dry-run-email --send-emails-only
```

### Rotacja Bundesland (domyślnie — 1 land / sobota)

```powershell
python de_gu_bauunternehmen_scraper.py --rotate-bundesland
python de_gu_bauunternehmen_scraper.py --rotation-status
```

Kolejność: NRW → Bayern → BW → Niedersachsen → Hessen → Sachsen → … (16 landów, cykl w `gu_bundesland_rotation.py`).

### Ręcznie wiele landów

```powershell
python de_gu_bauunternehmen_scraper.py --bundesland NRW,BY,BW
python de_gu_bauunternehmen_scraper.py --run-config run_config\welle_nrw_by_bw.json
```

## Limity

- Serper: **300** zapytań / dzień  
- E-mail: **300** / dzień, **2** / domena / dzień  
- Jedna fala (~96 fraz) ≈ **1–3 dni** Serpera

## Harmonogram 5 dni

Jeden obrót na **jedną falę** (1 Bundesland / tydzień). Szczegóły: [`schedule/PLAN_5_DNI.md`](schedule/PLAN_5_DNI.md)

| Dzień | Godzina (PL) | PC (Task Scheduler) | GitHub Actions |
|-------|--------------|---------------------|----------------|
| **Sobota** | **20:10** | `run_sroda.ps1` | `GU sobota discovery` |
| **Niedziela** | 06:00 | `run_czwartek.ps1` | `GU niedziela backfill` |
| **Poniedziałek** | 08:00 | `run_poniedzialek_prep.ps1` | `GU poniedzialek prep` |
| **Poniedziałek** | **12:00** | `run_poniedzialek_send.ps1` | `GU poniedzialek send` (partia 1) |
| **Wtorek** | **09:00** | `run_wtorek.ps1` | `GU wtorek send` (partia 2) |

Rejestracja zadań Windows:

```powershell
powershell -ExecutionPolicy Bypass -File "schedule\register_tasks_5_dni.ps1"
```

## GitHub Actions

CI, testy, pipeline 5 dni i upload na Drive — [`docs/GITHUB_ACTIONS.md`](docs/GITHUB_ACTIONS.md)

Sekrety (Settings → Secrets → Actions):

| Secret | Wymagany | Opis |
|--------|----------|------|
| `SERPER_API_KEY` | tak | API Serper |
| `MAIL_USER`, `MAIL_PASSWORD` | tak (pon+wt) | SMTP + IMAP |
| `GDRIVE_SERVICE_ACCOUNT_JSON` | opcjonalny | **Cały** plik JSON konta usługi (nie klucz `AIza...`) |

Setup Drive: `scripts/setup_gdrive_github_secret.ps1` lub [`docs/GOOGLE_DRIVE.md`](docs/GOOGLE_DRIVE.md)

## Maile MFG

- Treść: `mfg_gu_inquiry_email_de.py`  
- Załącznik PPTX: `mfg_gu_email_attachment.py` (Google Slides → PPTX; bez pliku lokalnego wysyłka się nie powiedzie)  
- Cc: tylko z `MAIL_CC` w `.env` (bez automatycznego `office@mfg-fliesen.de`)

## Struktura repo

```
├── de_gu_bauunternehmen_scraper.py
├── libs/                    # mail_transport, scraper_email_replies, …
├── schedule/                # run_sroda / czwartek / piatek
├── run_config/
├── scripts/                 # gdrive_upload_wyniki.py, setup_gdrive_github_secret.ps1
├── .github/workflows/
└── docs/
```
