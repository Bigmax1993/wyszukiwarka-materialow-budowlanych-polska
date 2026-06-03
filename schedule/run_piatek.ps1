# PIĄTEK — dzień 3: wysyłka maili (okno 8–18 wg Europe/Berlin).
# Task Scheduler: piątek 09:00
# Przed produkcją: w run_config wyłącz dry_run_email i włącz enable_auto_email (lub użyj --send-emails-only).

. "$PSScriptRoot\_common.ps1"
Enter-GuCampaign

$env:SCRAPER_TIMEZONE = "Europe/Berlin"
Remove-Item Env:DISABLE_SEND_WINDOW -ErrorAction SilentlyContinue
Remove-Item Env:SEND_WINDOW_START_HOUR -ErrorAction SilentlyContinue
Remove-Item Env:SEND_WINDOW_END_HOUR -ErrorAction SilentlyContinue

Write-Host "[PIATEK] Wysylka maili (--send-emails-only, okno 8-18 Berlin)..."
python de_gu_bauunternehmen_scraper.py --send-emails-only @args
