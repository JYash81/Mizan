$ErrorActionPreference = 'Continue'
$root = Split-Path -Parent $PSScriptRoot
Write-Host "Mizan environment check" -ForegroundColor Cyan
foreach ($command in @('python','node','npm','git')) {
  $available = Get-Command $command -ErrorAction SilentlyContinue
  if ($available) { Write-Host "[OK] $command : $((& $command --version) 2>$null | Select-Object -First 1)" -ForegroundColor Green } else { Write-Host "[MISSING] $command" -ForegroundColor Red }
}
foreach ($path in @('frontend/package.json','backend/requirements.txt','backend/.venv','storage/development')) {
  $fullPath = Join-Path $root $path
  $state = if (Test-Path $fullPath) { 'present' } else { 'missing' }
  Write-Host "[$state] $path"
}
