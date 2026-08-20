param(
    [string]$TaskPrefix = "CALI-TPC",
    [string]$RepoRoot = "R:\TPC_Triple_Predicate_Cubed",
    [string]$HealthScript = "R:\tpc_substrate\health_check.ps1"
)

$ErrorActionPreference = "Stop"

$startupTaskName = "$TaskPrefix-API-Startup"
$healthTaskName = "$TaskPrefix-Health-Daily"
$batPath = Join-Path $RepoRoot "start_tpc_api.bat"

if (-not (Test-Path $batPath)) {
    throw "Missing startup script: $batPath"
}
if (-not (Test-Path $HealthScript)) {
    throw "Missing health script: $HealthScript"
}

$startupAction = New-ScheduledTaskAction -Execute "cmd.exe" -Argument "/c \"$batPath\""
$startupTrigger = New-ScheduledTaskTrigger -AtStartup
$startupSettings = New-ScheduledTaskSettingsSet -StartWhenAvailable

$startupTaskArgs = @{
    TaskName = $startupTaskName
    Action = $startupAction
    Trigger = $startupTrigger
    Settings = $startupSettings
    Description = "Start TPC governance API on boot"
    Force = $true
}

$healthAction = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NoProfile -ExecutionPolicy Bypass -File \"$HealthScript\""
$healthTrigger = New-ScheduledTaskTrigger -Daily -At 3:00AM
$healthSettings = New-ScheduledTaskSettingsSet -StartWhenAvailable

$healthTaskArgs = @{
    TaskName = $healthTaskName
    Action = $healthAction
    Trigger = $healthTrigger
    Settings = $healthSettings
    Description = "Run daily health check for TPC governance API"
    Force = $true
}

$registered = @()

try {
    Register-ScheduledTask @startupTaskArgs -ErrorAction Stop | Out-Null
    $registered += $startupTaskName
}
catch {
    Write-Warning "Failed to register ${startupTaskName}: $($_.Exception.Message)"
}

try {
    Register-ScheduledTask @healthTaskArgs -ErrorAction Stop | Out-Null
    $registered += $healthTaskName
}
catch {
    Write-Warning "Failed to register ${healthTaskName}: $($_.Exception.Message)"
}

if ($registered.Count -gt 0) {
    Write-Output ("Registered tasks: " + ($registered -join ", "))
} else {
    throw "No tasks were registered. Re-run PowerShell as Administrator and try again."
}
