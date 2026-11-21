# Start the AmCraX dashboard: API (port 8000) + Vite frontend (port 5173).
#
#   scripts\start_amcrax.ps1 [-NoBrowser] [-ApiPort 8000] [-FrontendPort 5173]
#
# * API: if http://127.0.0.1:<ApiPort>/api/health already answers it is REUSED (and left alone by stop_amcrax.ps1).
#   Otherwise uvicorn is started detached WITHOUT --reload (reload kills the console group on Windows).
# * Frontend: "vite" dev server, detached, stdout -> logs\frontend_dev.log, stderr -> logs\frontend_dev.err.log.
# * PIDs of the processes THIS script started are recorded in logs\amcrax_pids.json; stop_amcrax.ps1 stops only those.
# Aspen Plus is never started here; it is only started when a simulation job with engine "aspen" is submitted.
param(
    [switch]$NoBrowser,
    [int]$ApiPort = 8000,
    [int]$FrontendPort = 5173
)
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'env.ps1')
$Root = $env:AMCRAX_ROOT
$Logs = Join-Path $Root 'logs'
New-Item -ItemType Directory -Force $Logs | Out-Null
$PidFile = Join-Path $Logs 'amcrax_pids.json'
$ApiUrl = "http://127.0.0.1:$ApiPort"
$FeUrl  = "http://localhost:$FrontendPort"

function Test-Http($url, $timeoutSec = 3) {
    try { return ((Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec $timeoutSec).StatusCode -eq 200) } catch { return $false }
}
function Wait-Http($url, $seconds) {
    $end = (Get-Date).AddSeconds($seconds)
    while ((Get-Date) -lt $end) { if (Test-Http $url 2) { return $true }; Start-Sleep -Milliseconds 700 }
    return $false
}
function Get-ProcInfo($proc) { @{ pid = $proc.Id; start_utc = $proc.StartTime.ToUniversalTime().ToString('o') } }

# ---- already started by an earlier run?
if (Test-Path $PidFile) {
    $old = Get-Content $PidFile -Raw | ConvertFrom-Json
    $alive = @()
    foreach ($k in 'api', 'frontend') {
        $e = $old.$k
        if ($e -and $e.pid) { $p = Get-Process -Id $e.pid -ErrorAction SilentlyContinue; if ($p) { $alive += $k } }
    }
    if ($alive.Count -gt 0 -and (Test-Http $FeUrl)) {
        Write-Host "[start] AmCraX is already running (started earlier: $($alive -join ', ')). Dashboard: $FeUrl"
        if (-not $NoBrowser) { Start-Process $FeUrl }
        exit 0
    }
}

$record = [ordered]@{ started_utc = (Get-Date).ToUniversalTime().ToString('o'); api = $null; frontend = $null; api_reused = $false; frontend_reused = $false }

# ---- API
if (Test-Http "$ApiUrl/api/health") {
    Write-Host "[start] API already answers on $ApiUrl - reusing it (it will NOT be stopped by stop_amcrax.ps1)."
    $record.api_reused = $true
} else {
    Write-Host "[start] starting API on $ApiUrl (uvicorn, no --reload) ..."
    $py = Join-Path $Root '.venv\Scripts\python.exe'
    if (-not (Test-Path $py)) { Write-Host '[start] ERROR .venv not found - run scripts\setup.ps1 first.' -ForegroundColor Red; exit 1 }
    $p = Start-Process -FilePath $py -ArgumentList @('-m', 'uvicorn', 'amcrax.api.main:app', '--host', '127.0.0.1', '--port', "$ApiPort") `
        -WorkingDirectory $Root -WindowStyle Hidden -PassThru `
        -RedirectStandardOutput (Join-Path $Logs 'api_stdout.log') -RedirectStandardError (Join-Path $Logs 'api_stderr.log')
    $record.api = Get-ProcInfo $p
    $record | ConvertTo-Json -Depth 4 | Set-Content $PidFile -Encoding utf8
    if (-not (Wait-Http "$ApiUrl/api/health" 40)) {
        Write-Host "[start] ERROR API did not answer within 40 s. See logs\api_stderr.log" -ForegroundColor Red; exit 1
    }
    Write-Host "[start] API is up (pid $($p.Id))."
}

# ---- frontend
$feDir = Join-Path $Root 'frontend'
if (Test-Http $FeUrl) {
    Write-Host "[start] something already answers on $FeUrl - reusing it."
    $record.frontend_reused = $true
} else {
    if (-not (Test-Path (Join-Path $feDir 'node_modules'))) { Write-Host '[start] ERROR frontend\node_modules missing - run scripts\setup.ps1 first.' -ForegroundColor Red; exit 1 }
    $node = (Get-Command node -ErrorAction Stop).Source
    $vite = Join-Path $feDir 'node_modules\vite\bin\vite.js'
    Write-Host "[start] starting frontend on $FeUrl (vite dev server) ..."
    $p = Start-Process -FilePath $node -ArgumentList @(('"' + $vite + '"'), '--port', "$FrontendPort", '--strictPort') `
        -WorkingDirectory $feDir -WindowStyle Hidden -PassThru `
        -RedirectStandardOutput (Join-Path $Logs 'frontend_dev.log') -RedirectStandardError (Join-Path $Logs 'frontend_dev.err.log')
    $record.frontend = Get-ProcInfo $p
    $record | ConvertTo-Json -Depth 4 | Set-Content $PidFile -Encoding utf8
    if (-not (Wait-Http $FeUrl 40)) {
        Write-Host "[start] ERROR frontend did not answer within 40 s. See logs\frontend_dev.log and logs\frontend_dev.err.log" -ForegroundColor Red; exit 1
    }
    Write-Host "[start] frontend is up (pid $($p.Id))."
}
$record | ConvertTo-Json -Depth 4 | Set-Content $PidFile -Encoding utf8

Write-Host ''
Write-Host "AmCraX dashboard: $FeUrl   (API docs: $ApiUrl/docs)" -ForegroundColor Green
Write-Host 'Stop what this script started with: scripts\stop_amcrax.ps1'
if (-not $NoBrowser) { Start-Process $FeUrl }
exit 0
