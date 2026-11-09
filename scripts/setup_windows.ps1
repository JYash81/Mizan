$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Push-Location (Join-Path $root 'backend')
python -m venv .venv
& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt
Pop-Location
Push-Location (Join-Path $root 'frontend')
npm install
Pop-Location
Write-Host 'Setup complete. See docs/development/LOCAL_SETUP.md for run commands.' -ForegroundColor Green
