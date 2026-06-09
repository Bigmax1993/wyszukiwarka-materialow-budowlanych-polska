#Requires -Version 5.1
param(
    [Parameter(Mandatory = $true)]
    [string]$DiscoveryRunId,
    [switch]$ForceResend
)

$ErrorActionPreference = "Stop"
$Repo = "Bigmax1993/Wyszukiwarka-partnerow"
$Log = Join-Path (Split-Path $PSScriptRoot -Parent) "Wyniki\gha_pipeline_run.log"

function Write-Log([string]$Msg) {
    $line = "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] $Msg"
    Write-Host $line
    try {
        Add-Content -Path $Log -Value $line -Encoding UTF8 -ErrorAction Stop
    } catch {
        # log moze byc zablokowany przez inny proces — nie przerywaj pipeline
    }
}

function Wait-Workflow([string]$Name, [string]$RunId) {
    Write-Log "Czekam: $Name (run $RunId)"
    Write-Log "URL: https://github.com/$Repo/actions/runs/$RunId"
    gh run watch $RunId -R $Repo --exit-status
    if ($LASTEXITCODE -ne 0) {
        throw "Workflow $Name nie powiodl sie (run $RunId)"
    }
    Write-Log "OK: $Name"
}

function Start-Workflow([string]$Name, [hashtable]$Fields = @{}) {
    Write-Log "Start: $Name"
    if ($Fields.Count -gt 0) {
        $wfArgs = @()
        foreach ($k in $Fields.Keys) {
            $wfArgs += "-f"
            $wfArgs += "${k}=$($Fields[$k])"
        }
        gh workflow run $Name -R $Repo @wfArgs
    } else {
        gh workflow run $Name -R $Repo
    }
    Start-Sleep -Seconds 15
    $runId = gh run list -R $Repo --workflow=$Name -L 1 --json databaseId -q ".[0].databaseId"
    if (-not $runId) { throw "Brak run ID dla $Name" }
    Wait-Workflow $Name $runId
}

Write-Log "=== Pelny pipeline GHA (discovery juz trwa: $DiscoveryRunId) ==="
Wait-Workflow "GU sobota discovery" $DiscoveryRunId
Start-Workflow "Sync wyniki Google Drive"

$pipeArgs = @("-ExecutionPolicy", "Bypass", "-File", (Join-Path $PSScriptRoot "run_full_pipeline_gha.ps1"), "-SkipDiscovery")
if ($ForceResend) { $pipeArgs += "-ForceResend" }
& powershell @pipeArgs

Write-Log "=== Pipeline GHA zakonczony pomyslnie ==="
