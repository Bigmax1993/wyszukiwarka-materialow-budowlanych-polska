# Rejestracja zadan Harmonogramu Windows — kampania PL (+5h wzgledem UA).
param([switch]$Unregister)

$ScheduleDir = $PSScriptRoot
$Pwsh = (Get-Command powershell.exe).Source

function Register-WeekdayTask {
    param([string]$Name, [string]$Script, [string]$Weekday, [string]$Time)
    $action = New-ScheduledTaskAction -Execute $Pwsh -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$Script`""
    $trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek $Weekday -At $Time
    $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
    Register-ScheduledTask -TaskName $Name -Action $action -Trigger $trigger -Settings $settings -Force | Out-Null
    Write-Host "OK: $Name -> $Weekday $Time"
}

$tasks = @(
    @{ Name = "Kanbud_PL_Poniedzialek_Discovery"; Script = Join-Path $ScheduleDir "run_poniedzialek_discovery.ps1"; Day = "Monday"; Time = "22:00" }
    @{ Name = "Kanbud_PL_Wtorek_Discovery"; Script = Join-Path $ScheduleDir "run_wtorek_discovery.ps1"; Day = "Tuesday"; Time = "20:00" }
    @{ Name = "Kanbud_PL_Sroda_Discovery"; Script = Join-Path $ScheduleDir "run_sroda_discovery.ps1"; Day = "Thursday"; Time = "00:00" }
    @{ Name = "Kanbud_PL_Czwartek_Discovery"; Script = Join-Path $ScheduleDir "run_czwartek_discovery.ps1"; Day = "Friday"; Time = "01:00" }
    @{ Name = "Kanbud_PL_Piatek_Discovery"; Script = Join-Path $ScheduleDir "run_piatek_discovery.ps1"; Day = "Friday"; Time = "21:00" }
    @{ Name = "Kanbud_PL_Niedziela_Backfill"; Script = Join-Path $ScheduleDir "run_niedziela_backfill.ps1"; Day = "Sunday"; Time = "10:30" }
    @{ Name = "Kanbud_PL_Poniedzialek_Prep"; Script = Join-Path $ScheduleDir "run_poniedzialek_prep.ps1"; Day = "Monday"; Time = "12:00" }
    @{ Name = "Kanbud_PL_Poniedzialek_Send"; Script = Join-Path $ScheduleDir "run_poniedzialek_send.ps1"; Day = "Monday"; Time = "14:00" }
    @{ Name = "Kanbud_PL_Wtorek_Send"; Script = Join-Path $ScheduleDir "run_wtorek_send.ps1"; Day = "Tuesday"; Time = "14:00" }
)

$reminderScript = Join-Path $ScheduleDir "run_sync_replies_reminders.ps1"
$reminderAction = New-ScheduledTaskAction -Execute $Pwsh -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$reminderScript`" --send"
$reminderTrigger = New-ScheduledTaskTrigger -Daily -DaysInterval 3 -At "10:00"
$reminderSettings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable

if ($Unregister) {
    foreach ($t in $tasks) {
        Unregister-ScheduledTask -TaskName $t.Name -Confirm:$false -ErrorAction SilentlyContinue
        Write-Host "Usunieto: $($t.Name)"
    }
    Unregister-ScheduledTask -TaskName "Kanbud_PL_Sync_Replies_Reminders" -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "Usunieto: Kanbud_PL_Sync_Replies_Reminders"
    exit 0
}

foreach ($t in $tasks) { Register-WeekdayTask @t }
Register-ScheduledTask -TaskName "Kanbud_PL_Sync_Replies_Reminders" -Action $reminderAction -Trigger $reminderTrigger -Settings $reminderSettings -Force | Out-Null
Write-Host "OK: Kanbud_PL_Sync_Replies_Reminders -> co 3 dni 10:00 (--send)"
Write-Host "Gotowe. Sprawdz taskschd.msc (Kanbud_PL_*)"
