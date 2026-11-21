# Start the AmCraX API development server (detached, auto-restarting on backend code changes).
. "$PSScriptRoot\env.ps1"
$pyw = Join-Path $env:AMCRAX_ROOT '.venv\Scripts\pythonw.exe'
Start-Process -FilePath $pyw -ArgumentList ('"' + (Join-Path $PSScriptRoot 'dev_api_supervisor.py') + '"') -WorkingDirectory $env:AMCRAX_ROOT -WindowStyle Hidden
"API supervisor started; server at http://127.0.0.1:8000 (log: logs\uvicorn_dev.log). Stop with scripts\stop_api_dev.ps1"
