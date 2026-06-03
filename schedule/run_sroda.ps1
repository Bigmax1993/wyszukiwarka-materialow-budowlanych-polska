# ŚRODA — dzień 1: discovery (Serper + www), bez wysyłki maili.
# Task Scheduler: środa 20:10

. "$PSScriptRoot\_common.ps1"
Enter-GuCampaign

$env:SCRAPER_TIMEZONE = "Europe/Warsaw"
Remove-Item Env:DISABLE_SEND_WINDOW -ErrorAction SilentlyContinue
Remove-Item Env:SCRAPER_IGNORE_SEND_WINDOW -ErrorAction SilentlyContinue

$config = if ($args.Count -gt 0) { $args[0] } else { $DefaultRunConfig }
Write-Host "[SRODA] Discovery: $config"
python de_gu_bauunternehmen_scraper.py --run-config $config @args
