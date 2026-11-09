# ==============================================================================
# MIZAN LOCAL BACKEND & CLOUDFLARE HTTPS TUNNEL LAUNCHER
# ==============================================================================

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "           MIZAN LOCAL BACKEND & HTTPS TUNNEL             " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

$root = Split-Path -Parent $PSScriptRoot
$backendDir = Join-Path $root "backend"
$cloudflared = Join-Path $root "cloudflared.exe"

Write-Host "`n[1/2] Launching Mizan FastAPI Backend (Port 8000)..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$backendDir'; .venv\Scripts\activate; uvicorn app.main:app --host 127.0.0.1 --port 8000"

Start-Sleep -Seconds 2

Write-Host "[2/2] Starting Cloudflare HTTPS Tunnel..." -ForegroundColor Green
Write-Host "`nINSTRUCTIONS FOR HOSTINGER FRONTEND:" -ForegroundColor Yellow
Write-Host "1. Look for the 'https://...trycloudflare.com' URL generated below." -ForegroundColor White
Write-Host "2. In Hostinger File Manager, edit 'public_html/config.js' (or subdomain folder)." -ForegroundColor White
Write-Host "3. Set API_BASE_URL to that URL with '/api/v1', like:" -ForegroundColor White
Write-Host "   window.__MIZAN_CONFIG__ = { API_BASE_URL: 'https://your-tunnel.trycloudflare.com/api/v1' };" -ForegroundColor Cyan
Write-Host "4. Save config.js. Your Hostinger frontend will instantly connect to your PC!" -ForegroundColor White
Write-Host "----------------------------------------------------------`n" -ForegroundColor DarkGray

& $cloudflared tunnel --url http://127.0.0.1:8000
