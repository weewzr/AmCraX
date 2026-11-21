# Stop the processes that scripts\start_amcrax.ps1 started (and ONLY those), using logs\amcrax_pids.json.
# An API that start_amcrax.ps1 merely reused (already running) is left untouched.
# The recorded start time is compared with the live process so that a recycled PID is never killed.
$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
$PidFile = Join-Path $Root 'logs\amcrax_pids.json'
if (-not (Test-Path $PidFile)) { Write-Host '[stop] logs\amcrax_pids.json not found - nothing started by start_amcrax.ps1 to stop.'; exit 0 }
$rec = Get-Content $PidFile -Raw | ConvertFrom-Json

foreach ($k in 'frontend', 'api') {
    $e = $rec.$k
    if (-not $e -or -not $e.pid) {
        $reused = $rec."${k}_reused"
        if ($reused) { Write-Host "[stop] $k was already running before start_amcrax.ps1 - left running." }
        continue
    }
    $p = Get-Process -Id $e.pid -ErrorAction SilentlyContinue
    if (-not $p) { Write-Host "[stop] $k (pid $($e.pid)) is not running any more."; continue }
    $recorded = [datetime]::Parse($e.start_utc).ToUniversalTime()
    if ([math]::Abs(($p.StartTime.ToUniversalTime() - $recorded).TotalSeconds) -gt 2) {
        Write-Host "[stop] pid $($e.pid) now belongs to a different process - not touching it." -ForegroundColor Yellow; continue
    }
    & taskkill.exe /PID $e.pid /T /F | Out-Null     # /T: also the child processes (venv launcher -> python, node children)
    Write-Host "[stop] $k stopped (pid $($e.pid) and children)."
}
Remove-Item $PidFile -Force
Write-Host '[stop] done.'
exit 0
