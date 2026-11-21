# Start the AmCraX API on http://localhost:8000 in the foreground (does not start Aspen Plus).
# For a detached, auto-restarting development server use start_api_dev.ps1 instead.
. "$PSScriptRoot\env.ps1"
Set-Location (Split-Path -Parent $PSScriptRoot)
python -m uvicorn amcrax.api.main:app --host 127.0.0.1 --port 8000 @args
