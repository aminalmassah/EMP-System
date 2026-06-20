@echo off
taskkill /f /im python.exe >nul 2>&1
taskkill /f /im python3.exe >nul 2>&1
echo Server stopped.
timeout /t 2 >nul
