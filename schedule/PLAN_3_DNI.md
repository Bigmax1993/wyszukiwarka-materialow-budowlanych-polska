# Plan 3 dni: środa → czwartek → piątek (fala GU NRW+BY+BW)

Jeden **obrót** pipeline’u na **jedną falę** (~96 zapytań Serper). Cała kampania bundesweit = wiele takich tygodni.

## Tabela

| Dzień | Godzina (propozycja) | Skrypt | Co robi |
|-------|----------------------|--------|---------|
| **Środa** | **18:00** | `run_sroda.ps1` | Discovery: Serper + strony www → `Wyniki/de_gu_bauunternehmen_cache.json` |
| **Czwartek** | 06:00 | `run_czwartek.ps1` | Backfill e-maili + Excel (bez nowego Serpera) |
| **Piątek** | 09:00 | `run_piatek.ps1` | Wysyłka maili (`--send-emails-only`, okno **8–18** czas niemiecki) |

## Środa — discovery

- `run_config\welle_nrw_by_bw.json`: `enable_auto_email: false`, `dry_run_email: true` (zostaw na środę).
- Limit Serper: **300/dzień** — jedna fala mieści się w środę.
- Start **18:00** — skan trwa wieczorem i w nocy (zwykle **2–8 h**); komputer nie może iść w uśpienie do rana (albo do końca joba).

```powershell
powershell -ExecutionPolicy Bypass -File "...\schedule\run_sroda.ps1"
```

## Czwartek — backfill + Excel

- Dopina `email_target` (Punycode, scoring) i odświeża `de_gu_bauunternehmen_kontakte.xlsx`.
- Jeśli środa **nie skończyła** skanu: najpierw ponów `run_sroda.ps1`, dopiero potem czwartek.

```powershell
powershell -ExecutionPolicy Bypass -File "...\schedule\run_czwartek.ps1"
```

## Piątek — wysyłka

- **Bez** `DISABLE_SEND_WINDOW` — maile tylko **8:00–18:00** (Berlin).
- Limit: **300 maili/dzień**, **2/domena/dzień**; pełna sesja ~**2–4 h**.
- Na produkcję: w `welle_nrw_by_bw.json` ustaw `dry_run_email: false` i `enable_auto_email: true`, albo trzymaj tylko `--send-emails-only` (jak w skrypcie).

```powershell
powershell -ExecutionPolicy Bypass -File "...\schedule\run_piatek.ps1"
```

## Task Scheduler (Windows)

Zarejestruj 3 zadania (uruchom jako użytkownik z .env i Pythonem w PATH):

```powershell
powershell -ExecutionPolicy Bypass -File "...\schedule\register_tasks_3_dni.ps1"
```

Usunięcie: `register_tasks_3_dni.ps1 -Unregister`

## Kolejny tydzień

| Tydzień | Środa | Czwartek | Piątek |
|---------|-------|----------|--------|
| 1 | Fala 1 NRW+BY+BW | backfill | wysyłka |
| 2 | Fala 2 (np. HE, NI, RP) — nowy `run_config` | backfill | wysyłka + reszta limitu z tygodnia 1 |
| … | kolejne Bundesländer | … | … |

## GitHub Actions (opcjonalnie)

Trzy workflow z cronem: `0 16 * * 3`, `30 3 * * 4`, `0 7 * * 5` (UTC ≈ **18:00** środa CEST / 05:30 czw / 09:00 pt) — patrz `.github/workflows/de_gu_wed.yml` itd.

## Pierwszy tydzień kampanii

- **Piątek tygodnia 1**: wysyłka tylko z kontaktów zebrane w **środę–czwartek** (może być mniej niż 300).
- Od **tygodnia 2** piątek wysyła też zaległe z poprzednich fal, jeśli zostały w cache.
