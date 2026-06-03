# CZWARTEK — dzień 2: backfill e-maili + przebudowa Excela (bez Serpera, bez wysyłki).
# Task Scheduler: czwartek 06:00
# Jeśli środa nie skończyła discovery — najpierw dokończ: run_sroda.ps1, potem ten skrypt.

. "$PSScriptRoot\_common.ps1"
Enter-GuCampaign

$env:SCRAPER_TIMEZONE = "Europe/Warsaw"
Remove-Item Env:DISABLE_SEND_WINDOW -ErrorAction SilentlyContinue

Write-Host "[CZWARTEK] Backfill e-maili z cache..."
python de_gu_bauunternehmen_scraper.py --backfill-emails-from-cache

Write-Host "[CZWARTEK] Rebuild Excel z cache..."
python de_gu_bauunternehmen_scraper.py --rebuild-from-cache
