# Dot-source this file to put the AmCraX toolchain on PATH for the current PowerShell command:
#   . "<project root>\scripts\env.ps1"
# Afterwards `python`, `pip`, `pytest`, `node`, `npm`, `npx`, `git` and `pandoc` resolve to the project
# toolchain: the Python venv in .venv plus the portable tools in %LOCALAPPDATA%\AmCraX-tools.
$AmcraxRoot  = Split-Path -Parent $PSScriptRoot
$AmcraxTools = Join-Path $env:LOCALAPPDATA 'AmCraX-tools'
$env:PATH = (Join-Path $AmcraxRoot '.venv\Scripts') + ';' +
            (Join-Path $AmcraxTools 'node') + ';' +
            (Join-Path $AmcraxTools 'git\cmd') + ';' +
            (Join-Path $AmcraxTools 'pandoc') + ';' + $env:PATH
$env:PYTHONUTF8 = '1'
$env:AMCRAX_ROOT = $AmcraxRoot
