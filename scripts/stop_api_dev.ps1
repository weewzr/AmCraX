# Stop the AmCraX API development server started by start_api_dev.ps1.
$root = Split-Path -Parent $PSScriptRoot
New-Item -ItemType File -Force (Join-Path $root 'logs\api_supervisor.stop') | Out-Null
"Stop requested; the supervisor exits within a few seconds."
