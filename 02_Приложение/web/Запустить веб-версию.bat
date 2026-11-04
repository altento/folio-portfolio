@echo off
cd /d "%~dp0"
start "folio local" /min py -3 -m http.server 8765 --bind 0.0.0.0 --directory "%~dp0"
timeout /t 2 >nul
start "" http://127.0.0.1:8765/
