param([ValidateSet('api','web')][string]$Target = 'api')
$root = Split-Path -Parent $PSScriptRoot
if ($Target -eq 'api') { Push-Location (Join-Path $root 'backend'); & .\.venv\Scripts\python.exe -m uvicorn app.main:app --reload; Pop-Location }
else { Push-Location (Join-Path $root 'frontend'); npm run dev; Pop-Location }
