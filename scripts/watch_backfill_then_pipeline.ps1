#Requires -Version 5.1
param(
    [string]$BackfillRunId = "27134963915"
)

$ErrorActionPreference = "Stop"
$Repo = "Bigmax1993/Wyszukiwarka-partnerow"

Write-Host "Czekam na backfill (run $BackfillRunId)..."
Write-Host "URL: https://github.com/$Repo/actions/runs/$BackfillRunId"
gh run watch $BackfillRunId -R $Repo --exit-status
if ($LASTEXITCODE -ne 0) {
    throw "Backfill nie powiodl sie (run $BackfillRunId)"
}
Write-Host "Backfill OK - reszta pipeline (sync, prep, send)..." -ForegroundColor Green
& powershell -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot "run_full_pipeline_gha.ps1") -SkipDiscovery -SkipBackfill
