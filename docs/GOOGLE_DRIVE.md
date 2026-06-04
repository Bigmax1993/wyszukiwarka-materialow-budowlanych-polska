# Google Drive — wyniki kampanii GU

Folder w chmurze: [GU Bauunternehmen](https://drive.google.com/drive/folders/1tP8oUi72t4EHDbE9GnHFdvfNtNsJe4xf)

ID folderu: `1tP8oUi72t4EHDbE9GnHFdvfNtNsJe4xf`

## Co trafia na Drive

| Plik / folder | Opis |
|---------------|------|
| `de_gu_bauunternehmen_cache.json` | Cache |
| `de_gu_bauunternehmen_kontakte.xlsx` | Excel |
| `de_gu_bauunternehmen_scraper.log` | Log |
| `wyslane/*.eml` | Kopie wysłanych maili |

Folder może być **pusty** przed pierwszym uruchomieniem scrapera — pliki powstają automatycznie.

## Sposoby uploadu

| Sposób | Kiedy |
|--------|--------|
| **GitHub Actions** | Workflow `Sync wyniki Google Drive` (po piątku / ręcznie) |
| **Lokalnie** | `python scripts/gdrive_upload_wyniki.py --campaign-dir .` |
| **PC + Drive for desktop** | Zmienna `KANBUD_GOOGLE_DRIVE_GU_PATH` → zapis na bieżąco |

## Konto usługi Google (jednorazowo)

1. [Google Cloud Console](https://console.cloud.google.com/) → projekt → włącz **Google Drive API**.
2. **Administracja → Konta usługi** → utwórz konto (np. `gu-wyniki-upload`) → **Klucze** → **JSON** (pobierz plik).
3. **Nie używaj** klucza API (`AIza...`) z sekcji „Dane logowania” — potrzebny jest **plik JSON** z `type: service_account`.
4. **GitHub Actions (wymagane):** konto usługowe **nie ma własnej przestrzeni** na „Moim dysku”.
   - Utwórz **dysk współdzielony** (Shared Drive) w Google Workspace.
   - Dodaj e-mail konta usługi (`...@....iam.gserviceaccount.com`) jako **Content manager** (Zarządzanie treścią).
   - Skrypt sam utworzy folder `GU Bauunternehmen Wyniki` i wgra pliki (albo użyje folderu, jeśli już jest na Shared Drive).
   - Opcjonalnie: secret **`GDRIVE_SHARED_DRIVE_ID`** = ID dysku (z URL dysku współdzielonego).
   - Alternatywa (Workspace): delegacja domeny + secret **`GDRIVE_IMPERSONATE_EMAIL`** = Twój e-mail firmowy.
5. Folder na „Moim dysku” możesz nadal udostępnić do podglądu; upload z CI i tak trafi na Shared Drive.
6. GitHub: secret **`GDRIVE_SERVICE_ACCOUNT_JSON`** = cała treść pliku JSON.

### Automatyczny setup secretu (PC)

```powershell
# Po pobraniu JSON — skopiuj do secrets\gdrive-service-account.json lub zostaw w Pobranych
cd Wyszukiwarka-partnerow
.\scripts\setup_gdrive_github_secret.ps1
```

## Załącznik PPTX (piątek, GitHub Actions)

Prezentacja: [Google Slides MFG](https://docs.google.com/presentation/d/12h0_knRQVTU9sRg9kqh8dxjSiuuKx0TA/edit)

Runner GitHub **nie ma** lokalnego pliku PPTX. Udostępnij Slides e-mailowi konta usługi (**Przeglądający**), albo ustaw `MFG_EMAIL_ATTACHMENT_PATH` lokalnie.

Moduł: `mfg_gu_email_attachment.py` — **wysyłka bez PPTX kończy się błędem**.

## Zmienne środowiskowe

| Zmienna | Opis |
|---------|------|
| `GDRIVE_SERVICE_ACCOUNT_JSON` | Treść JSON (GitHub Actions / env) |
| `GDRIVE_SERVICE_ACCOUNT_FILE` | Ścieżka do pliku JSON (lokalnie) |
| `GDRIVE_FOLDER_ID` | Domyślnie ID folderu GU powyżej |
| `GDRIVE_SHARED_DRIVE_ID` | ID dysku współdzielonego (opcjonalnie) |
| `GDRIVE_IMPERSONATE_EMAIL` | E-mail użytkownika Workspace — delegacja DWD (opcjonalnie) |
| `KANBUD_GOOGLE_DRIVE_GU_PATH` | Lokalna ścieżka Drive for desktop |
