# AmCraX bootstrap for a fresh Windows machine. Idempotent: safe to run again at any time.
#
#   powershell -ExecutionPolicy Bypass -File scripts\setup.ps1 [-Force] [-SkipFrontend]
#
# Steps
#   1. find Python 3.12 (PATH, py launcher, or %LOCALAPPDATA%\AmCraX-tools\python*) and Node (PATH or %LOCALAPPDATA%\AmCraX-tools\node)
#   2. create .venv if it does not exist
#   3. pip install -r requirements.txt   (no-op when everything is already installed)
#   4. pip install -e backend            (skipped when "amcrax" already resolves to backend\)
#   5. npm ci in frontend                (skipped when frontend\node_modules exists, unless -Force)
# Nothing here starts Aspen Plus.
param(
    [switch]$Force,          # re-create nothing, but run "npm ci" and the editable install even if they look done
    [switch]$SkipFrontend    # do not touch the frontend
)
$ErrorActionPreference = 'Stop'
$Root  = Split-Path -Parent $PSScriptRoot
$Tools = Join-Path $env:LOCALAPPDATA 'AmCraX-tools'
$Venv  = Join-Path $Root '.venv'
$VenvPy = Join-Path $Venv 'Scripts\python.exe'

function Write-Step($msg) { Write-Host "[setup] $msg" -ForegroundColor Cyan }
function Write-Ok($msg)   { Write-Host "[setup] OK  $msg" -ForegroundColor Green }
function Stop-Setup($msg) { Write-Host "[setup] ERROR $msg" -ForegroundColor Red; exit 1 }

function Test-Python312($exe, $exeArgs) {
    try {
        $v = & $exe @exeArgs -c "import sys; print('%d.%d' % sys.version_info[:2])" 2>$null
        return ($LASTEXITCODE -eq 0 -and $v -eq '3.12')
    } catch { return $false }
}

# ---------------------------------------------------------------- 1. interpreters
$basePy = $null; $baseArgs = @()
if (Test-Path $VenvPy) {
    Write-Ok "virtual environment exists: $Venv"
} else {
    Write-Step 'looking for Python 3.12'
    $candidates = @()
    $candidates += ,@('python', @())
    $candidates += ,@('py', @('-3.12'))
    Get-ChildItem $Tools -Directory -Filter 'python*' -ErrorAction SilentlyContinue | ForEach-Object {
        $candidates += ,@((Join-Path $_.FullName 'python.exe'), @())
    }
    $pyUser = Join-Path $env:LOCALAPPDATA 'Programs\Python\Python312\python.exe'
    $candidates += ,@($pyUser, @())
    foreach ($c in $candidates) {
        if ((Get-Command $c[0] -ErrorAction SilentlyContinue) -and (Test-Python312 $c[0] $c[1])) { $basePy = $c[0]; $baseArgs = $c[1]; break }
    }
    if (-not $basePy) { Stop-Setup 'Python 3.12 not found. Install it from https://www.python.org/downloads/ (per-user install is enough) and re-run.' }
    Write-Ok "Python 3.12 found: $basePy"
}

$node = Get-Command node -ErrorAction SilentlyContinue
if (-not $node) {
    $toolNode = Join-Path $Tools 'node\node.exe'
    if (Test-Path $toolNode) { $env:PATH = (Join-Path $Tools 'node') + ';' + $env:PATH; $node = Get-Command node -ErrorAction SilentlyContinue }
}
if (-not $SkipFrontend) {
    if (-not $node) { Stop-Setup 'Node.js not found on PATH or in %LOCALAPPDATA%\AmCraX-tools\node. Install Node 24 LTS (https://nodejs.org) or use -SkipFrontend.' }
    $nodeVer = (& node --version)
    if (-not $nodeVer.StartsWith('v24')) { Write-Host "[setup] WARNING Node $nodeVer found; the project was developed with Node 24 LTS." -ForegroundColor Yellow } else { Write-Ok "Node $nodeVer" }
}

# ---------------------------------------------------------------- 2. venv
if (-not (Test-Path $VenvPy)) {
    Write-Step "creating virtual environment in $Venv"
    & $basePy @baseArgs -m venv $Venv
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path $VenvPy)) { Stop-Setup 'venv creation failed.' }
    Write-Ok 'virtual environment created'
}

# ---------------------------------------------------------------- 3. requirements
Write-Step 'pip install -r requirements.txt (already-satisfied packages are left alone)'
& $VenvPy -m pip install --disable-pip-version-check --quiet -r (Join-Path $Root 'requirements.txt')
if ($LASTEXITCODE -ne 0) { Stop-Setup 'pip install -r requirements.txt failed.' }
Write-Ok 'Python requirements satisfied'

# ---------------------------------------------------------------- 4. editable amcrax package
$amcraxFile = & $VenvPy -c "import amcrax, sys; print(amcrax.__file__)" 2>$null
$backendDir = Join-Path $Root 'backend'
if (-not $Force -and $LASTEXITCODE -eq 0 -and $amcraxFile -and $amcraxFile.StartsWith($backendDir, [StringComparison]::OrdinalIgnoreCase)) {
    Write-Ok "amcrax already installed in editable mode ($amcraxFile)"
} else {
    Write-Step 'pip install -e backend'
    & $VenvPy -m pip install --disable-pip-version-check --quiet -e $backendDir
    if ($LASTEXITCODE -ne 0) { Stop-Setup 'pip install -e backend failed.' }
    Write-Ok 'amcrax installed (editable)'
}

# ---------------------------------------------------------------- 5. frontend
if ($SkipFrontend) {
    Write-Step 'frontend skipped (-SkipFrontend)'
} else {
    $fe = Join-Path $Root 'frontend'
    if ((Test-Path (Join-Path $fe 'node_modules')) -and -not $Force) {
        Write-Ok 'frontend\node_modules exists - npm ci skipped (use -Force to reinstall)'
    } else {
        Write-Step 'npm ci in frontend'
        Push-Location $fe
        try { & npm ci --no-audit --no-fund; if ($LASTEXITCODE -ne 0) { Stop-Setup 'npm ci failed.' } } finally { Pop-Location }
        Write-Ok 'frontend dependencies installed'
    }
}

# ---------------------------------------------------------------- summary
$com = $false
try { $com = Test-Path 'Registry::HKEY_CLASSES_ROOT\Apwn.Document.41.0' } catch {}
if ($com) { Write-Ok 'Aspen Plus V15 COM ProgID Apwn.Document.41.0 is registered (live simulation possible; a licence seat is still required)' }
else      { Write-Host '[setup] NOTE Aspen Plus V15 COM ProgID not registered: the dashboard will run in SNAPSHOT / Python-model mode (see docs/installation.md).' -ForegroundColor Yellow }
Write-Host '[setup] Done. Next: scripts\start_amcrax.ps1' -ForegroundColor Green
exit 0
