@echo off
TITLE Mizan Local Backend & Tunnel Launcher
powershell -ExecutionPolicy Bypass -File "%~dp0scripts\start_backend_tunnel.ps1"
pause
