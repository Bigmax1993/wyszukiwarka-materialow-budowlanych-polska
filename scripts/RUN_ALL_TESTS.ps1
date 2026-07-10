#Requires -Version 5.1
<#
Pelna bateria testow lokalnych (PL, zgodnie z tests.yml).

  powershell -ExecutionPolicy Bypass -File scripts\RUN_ALL_TESTS.ps1
#>
$ErrorActionPreference = "Stop"
$Root = Split-Path $PSScriptRoot -Parent
Set-Location $Root
$env:KANBUD_PROJECT_ROOT = Join-Path $Root "libs"
$env:PYTHONUTF8 = "1"
$env:PYTHONPATH = $env:KANBUD_PROJECT_ROOT

$failed = @()
$passed = @()

function Test-Step {
    param([string]$Name, [scriptblock]$Block)
    Write-Host "`n>> $Name" -ForegroundColor Cyan
    try {
        & $Block
        if ($LASTEXITCODE -and $LASTEXITCODE -ne 0) { throw "exit $LASTEXITCODE" }
        $script:passed += $Name
        Write-Host "OK: $Name" -ForegroundColor Green
    } catch {
        $script:failed += "${Name}: $_"
        Write-Host "FAIL: $Name - $_" -ForegroundColor Red
    }
}

Test-Step "py_compile (aktywne moduly)" {
    Get-ChildItem -Recurse -Filter *.py |
        Where-Object { $_.FullName -notmatch '\\\.venv\\' } |
        ForEach-Object {
            python -m py_compile $_.FullName
            if ($LASTEXITCODE -ne 0) { throw $_.FullName }
        }
}

Test-Step "smoke --test (PL materialy)" { python pl_materialy_scraper.py --test }

Test-Step "regresja PL materialy" {
    python -m unittest tests.test_pl_materialy_regression -v
}

Test-Step "pytest PL (jednostkowe + integracyjne)" {
    python -m pytest `
        tests/test_pl_inquiry_email_pl.py `
        tests/test_pl_materialy_integration.py `
        -q
}

Test-Step "pl_wojewodztwo_rotation" {
    python -c @"
from pathlib import Path
import tempfile
from pl_wojewodztwo_rotation import (
    load_rotation_state, peek_next_wojewodztwo, commit_rotation_after_run,
    rotation_state_path, WOJEWODZTWO_ROTATION_ORDER,
)
d = Path(tempfile.mkdtemp())
p = rotation_state_path(d)
s = load_rotation_state(p)
woj = peek_next_wojewodztwo(s)
assert woj in WOJEWODZTWO_ROTATION_ORDER
commit_rotation_after_run(p, s, woj)
"@
}

Test-Step "pl_materialy - brak zalacznikow" {
    python -c @"
import pl_materialy_scraper as pl
assert pl.get_email_attachments_pl_materialy() == []
assert pl.PL_EMAIL_ALLOW_ATTACHMENTS is False
"@
}

Test-Step "gdrive_upload_wyniki --help" {
    python scripts/gdrive_upload_wyniki.py --help | Out-Null
}

Write-Host "`n======== PODSUMOWANIE ========" -ForegroundColor Yellow
Write-Host "Passed: $($passed.Count)"
$passed | ForEach-Object { Write-Host "  + $_" }
if ($failed.Count) {
    Write-Host "Failed: $($failed.Count)" -ForegroundColor Red
    $failed | ForEach-Object { Write-Host "  - $_" }
    exit 1
}
Write-Host "Wszystkie testy OK (PL)" -ForegroundColor Green
