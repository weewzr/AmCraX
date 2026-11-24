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
# Rust toolchain (rustup with the x86_64-pc-windows-gnu host and the wasm32-unknown-unknown target), if it is
# installed in the portable tools folder. A system-wide Rust installation on PATH works as well.
$AmcraxRust = Join-Path $AmcraxTools 'rust'
if (Test-Path (Join-Path $AmcraxRust 'cargo\bin\cargo.exe')) {
    $env:RUSTUP_HOME = Join-Path $AmcraxRust 'rustup'
    $env:CARGO_HOME  = Join-Path $AmcraxRust 'cargo'
    $env:PATH = (Join-Path $AmcraxRust 'cargo\bin') + ';' + $env:PATH
    # The GNU host needs dlltool for crates that import Windows libraries; rustup ships it in this folder.
    $selfContained = Join-Path $AmcraxRust 'rustup\toolchains\stable-x86_64-pc-windows-gnu\lib\rustlib\x86_64-pc-windows-gnu\bin\self-contained'
    if (Test-Path (Join-Path $selfContained 'dlltool.exe')) { $env:PATH = $env:PATH + ';' + $selfContained }
}
