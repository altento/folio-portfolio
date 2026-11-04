@echo off
cd /d "%~dp0"
if exist "%~dp0folio.exe" (
  start "" "%~dp0folio.exe"
  exit /b 0
)
if exist "%~dp0dist\folio.exe" (
  start "" "%~dp0dist\folio.exe"
  exit /b 0
)
where py >nul 2>nul
if %errorlevel%==0 (
  py main.py
) else (
  python main.py
)
if errorlevel 1 (
  echo.
  echo Не удалось запустить приложение. Убедитесь, что установлен Python 3.
  pause
)
