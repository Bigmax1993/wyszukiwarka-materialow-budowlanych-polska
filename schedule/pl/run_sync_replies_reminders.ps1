# PL materiały: IMAP + przypomnienia (co 3 dni)
$RepoRoot = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
Set-Location $RepoRoot
python pl_sync_replies_and_reminders.py @args
