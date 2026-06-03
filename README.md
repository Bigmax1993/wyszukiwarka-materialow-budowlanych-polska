# Wyszukiwarka partnerĂłw â€” kampania GU (bundesweit)

Repozytorium zawiera **wyĹ‚Ä…cznie** moduĹ‚ `Gu Baunterhnehmen` (Generalunternehmer / Filialbau DE).

## Uruchomienie

```powershell
pip install -r requirements.txt
$env:KANBUD_PROJECT_ROOT = "$PWD\libs"
python de_gu_bauunternehmen_scraper.py --test
```

Harmonogram: `schedule/PLAN_3_DNI.md`
# Kampania: GU Bauunternehmen — całe Niemcy (bundesweit)

**Moduł:** `de_gu_bauunternehmen_scraper.py`  
**Słowa kluczowe Serper:** `de_gu_keywords.py` (frazy per **Bundesland**)

**Wykluczeni kontrahenci** (lista MFG / mail Izabela): `../de_contractor_exclusions.py`

Ten sam profil firm co DE Ost: **Generalunternehmer / Filialbau**, Neubau/Umbau marketów, dowód projektów (referencje lub zdjęcia). Bez operatorów sieci (REWE sklep itd.).

## Różnice względem „Niemcy wschodnie sklepy”

| | DE Ost | GU bundesweit |
|---|--------|----------------|
| Geo | BB / SN / TH | **Wyłączone** (cała DE) |
| Frazy Serper | Ost + miasta wschodnie | **Per Bundesland** (fala 1: NRW, BY, BW) |
| Cel kontaktów | 70 | **150** |
| Gemini na www/Excel | włączone | **wyłączone** (szybciej, mniej 429) |
| Cache / Excel | `de_ost_*` | `de_gu_bauunternehmen_*` |

## Wyniki

Domyślnie: folder kampanii `Wyniki/`. Po ustawieniu **`KANBUD_GOOGLE_DRIVE_GU_PATH`** (lub auto-wykryciu) — zapis na [Google Drive](https://drive.google.com/drive/folders/1tP8oUi72t4EHDbE9GnHFdvfNtNsJe4xf?usp=drive_link): JSON, Excel, log, `wyslane/`. Instrukcja: `../docs/GOOGLE_DRIVE_WYNIKI.md`.

| Plik | Opis |
|------|------|
| `Wyniki/de_gu_bauunternehmen_kontakte.xlsx` | Excel |
| `Wyniki/de_gu_bauunternehmen_cache.json` | Cache |
| `Wyniki/de_gu_bauunternehmen_scraper.log` | Log |
| `wyslane/` | Kopie wysłanych maili |

## Uruchomienie

```powershell
$env:KANBUD_PROJECT_ROOT = "$env:USERPROFILE\Documents\piasek Gdansk"
cd "C:\Users\kanbu\Documents\Automatyczna wyszukiwarka piasku i wysylka zapytania\Gu Baunterhnehmen"

python de_gu_bauunternehmen_scraper.py --test
python de_gu_bauunternehmen_scraper.py
python de_gu_bauunternehmen_scraper.py --dry-run-email
```

### Fala po Bundesland

```powershell
# Tylko NRW
python de_gu_bauunternehmen_scraper.py --bundesland NRW

# NRW + Bayern + BW (domyślna fala 1)
python de_gu_bauunternehmen_scraper.py --bundesland NRW,BY,BW

# Konfiguracja JSON
python de_gu_bauunternehmen_scraper.py --run-config run_config\welle_nrw_by_bw.json
```

### Cache / maile

```powershell
python de_gu_bauunternehmen_scraper.py --backfill-emails-from-cache
python de_gu_bauunternehmen_scraper.py --rebuild-from-cache
python de_gu_bauunternehmen_scraper.py --send-emails-only
```

## Limity (jak DE Ost)

- Serper: **300** zapytań / dzień  
- E-mail: **300** / dzień, **2** / domena / dzień  

Przy ~96 frazach na falę pełny przebieg listi ≈ **1–3 dni** Serpera.

## Harmonogram 3 dni (środa → czwartek → piątek)

Jeden obrót pipeline’u na **jedną falę** (np. NRW+BY+BW). Szczegóły: `../schedule/PLAN_3_DNI.md`

| Dzień | Godzina | Skrypt |
|-------|---------|--------|
| Środa | **20:10** | `../schedule/run_sroda.ps1` — discovery |
| Czwartek | 06:00 | `../schedule/run_czwartek.ps1` — backfill + Excel |
| Piątek | 09:00 | `../schedule/run_piatek.ps1` — `--send-emails-only` (okno 8–18 Berlin) |

Rejestracja w Task Scheduler:

```powershell
powershell -ExecutionPolicy Bypass -File "..\schedule\register_tasks_3_dni.ps1"
```

Zmienne środowiskowe: `..\.env.example`. Stary skrypt all-in-one: `../schedule/run_job.ps1`.

## Regeneracja scrapera

Po zmianach w `de_ost_einzelhandel_scraper.py` (szablon):

```powershell
python _build_gu_scraper.py
```

## Klucze API

`SERPER_API_KEY`, `MAIL_USER`, `MAIL_PASSWORD` — `.env` w **piasek Gdansk**.

