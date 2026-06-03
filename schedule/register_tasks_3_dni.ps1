# Rejestracja 3 zadan w Harmonogramie zadan Windows (sroda / czwartek / piatek).
# Uruchom PowerShell jako administrator.

param(
    [switch]$Unregister
)

$ScheduleDir = $PSScriptRoot
$Pwsh = (Get-Command powershell.exe).Source

function Register-WeekdayTask {
    param(
        [string]$Name,
        [string]$Script,
        [string]$Weekday,
        [string]$Time
    )
    $action = New-ScheduledTaskAction -Execute $Pwsh -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$Script`""
    $trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek $Weekday -At $Time
    $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
    Register-ScheduledTask -TaskName $Name -Action $action -Trigger $trigger -Settings $settings -Force | Out-Null
    Write-Host "OK: $Name -> $Weekday $Time"
}

$tasks = @(
    @{ Name = "Kanbud_GU_Sroda_Discovery"; Script = Join-Path $ScheduleDir "run_sroda.ps1"; Day = "Wednesday"; Time = "20:10" }
    @{ Name = "Kanbud_GU_Czwartek_Backfill"; Script = Join-Path $ScheduleDir "run_czwartek.ps1"; Day = "Thursday"; Time = "06:00" }
    @{ Name = "Kanbud_GU_Piatek_Send"; Script = Join-Path $ScheduleDir "run_piatek.ps1"; Day = "Friday"; Time = "09:00" }
)

if ($Unregister) {
    foreach ($t in $tasks) {
        Unregister-ScheduledTask -TaskName $t.Name -Confirm:$false -ErrorAction SilentlyContinue
        Write-Host "Usunieto: $($t.Name)"
    }
    exit 0
}

foreach ($t in $tasks) {
    Register-WeekdayTask -Name $t.Name -Script $t.Script -Weekday $t.Day -Time $t.Time
}

Write-Host "Gotowe. Sprawdz taskschd.msc (Kanbud_GU_*)"
