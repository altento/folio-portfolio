@echo off
cd /d "%~dp0"

if exist "%~dp0dist\folio-webview-v163\folio-desktop\folio-desktop.exe" (
  start "" "%~dp0dist\folio-webview-v163\folio-desktop\folio-desktop.exe"
  exit /b 0
)

if exist "%~dp0dist\folio-webview-v162\folio-desktop\folio-desktop.exe" (
  start "" "%~dp0dist\folio-webview-v162\folio-desktop\folio-desktop.exe"
  exit /b 0
)

if exist "%~dp0dist\folio-webview-v160\folio-desktop\folio-desktop.exe" (
  start "" "%~dp0dist\folio-webview-v160\folio-desktop\folio-desktop.exe"
  exit /b 0
)

if exist "%~dp0dist\folio-webview-v159\folio-desktop\folio-desktop.exe" (
  start "" "%~dp0dist\folio-webview-v159\folio-desktop\folio-desktop.exe"
  exit /b 0
)
if exist "%~dp0dist\folio-webview-v158\folio-desktop\folio-desktop.exe" (
  start "" "%~dp0dist\folio-webview-v158\folio-desktop\folio-desktop.exe"
  exit /b 0
)
if exist "%~dp0dist\folio-webview-v157\folio-desktop\folio-desktop.exe" (
  start "" "%~dp0dist\folio-webview-v157\folio-desktop\folio-desktop.exe"
  exit /b 0
)
if exist "%~dp0dist\folio-webview-v156\folio-desktop\folio-desktop.exe" (
  start "" "%~dp0dist\folio-webview-v156\folio-desktop\folio-desktop.exe"
  exit /b 0
)
if exist "%~dp0dist\folio-webview-v155\folio-desktop\folio-desktop.exe" (
  start "" "%~dp0dist\folio-webview-v155\folio-desktop\folio-desktop.exe"
  exit /b 0
)
if exist "%~dp0dist\folio-webview-v151\folio-desktop\folio-desktop.exe" (
  start "" "%~dp0dist\folio-webview-v151\folio-desktop\folio-desktop.exe"
  exit /b 0
)
if exist "%~dp0dist\folio-webview-v150\folio-desktop\folio-desktop.exe" (
  start "" "%~dp0dist\folio-webview-v150\folio-desktop\folio-desktop.exe"
  exit /b 0
)
if exist "%~dp0dist\folio-webview-v149\folio-desktop\folio-desktop.exe" (
  start "" "%~dp0dist\folio-webview-v149\folio-desktop\folio-desktop.exe"
  exit /b 0
)
if exist "%~dp0dist\folio-webview-v148\folio-desktop\folio-desktop.exe" (
  start "" "%~dp0dist\folio-webview-v148\folio-desktop\folio-desktop.exe"
  exit /b 0
)
if exist "%~dp0dist\folio-webview-v146\folio-desktop\folio-desktop.exe" (
  start "" "%~dp0dist\folio-webview-v146\folio-desktop\folio-desktop.exe"
  exit /b 0
)
if exist "%~dp0dist\folio-webview-v145\folio-desktop\folio-desktop.exe" (
  start "" "%~dp0dist\folio-webview-v145\folio-desktop\folio-desktop.exe"
  exit /b 0
)
if exist "%~dp0dist\folio-webview-v144\folio-desktop\folio-desktop.exe" (
  start "" "%~dp0dist\folio-webview-v144\folio-desktop\folio-desktop.exe"
  exit /b 0
)
if exist "%~dp0dist\folio-webview-v143\folio-desktop\folio-desktop.exe" (
  start "" "%~dp0dist\folio-webview-v143\folio-desktop\folio-desktop.exe"
  exit /b 0
)
if exist "%~dp0dist\folio-webview-v142\folio-desktop\folio-desktop.exe" (
  start "" "%~dp0dist\folio-webview-v142\folio-desktop\folio-desktop.exe"
  exit /b 0
)
if exist "%~dp0dist\folio-webview-v141\folio-desktop\folio-desktop.exe" (
  start "" "%~dp0dist\folio-webview-v141\folio-desktop\folio-desktop.exe"
  exit /b 0
)
if exist "%~dp0dist\folio-webview-v135\folio-desktop\folio-desktop.exe" (
  start "" "%~dp0dist\folio-webview-v135\folio-desktop\folio-desktop.exe"
  exit /b 0
)
if exist "%~dp0dist\folio-webview-v134\folio-desktop\folio-desktop.exe" (
  start "" "%~dp0dist\folio-webview-v134\folio-desktop\folio-desktop.exe"
  exit /b 0
)
if exist "%~dp0dist\folio-webview-v133\folio-desktop\folio-desktop.exe" (
  start "" "%~dp0dist\folio-webview-v133\folio-desktop\folio-desktop.exe"
  exit /b 0
)
if exist "%~dp0dist\folio-webview\folio-desktop\folio-desktop.exe" (
  start "" "%~dp0dist\folio-webview\folio-desktop\folio-desktop.exe"
  exit /b 0
)
if exist "%~dp0folio-current.exe" (
  start "" "%~dp0folio-current.exe"
  exit /b 0
)
if exist "%~dp0dist\folio.exe" (
  start "" "%~dp0dist\folio.exe"
  exit /b 0
)
if exist "%~dp0folio.exe" (
  start "" "%~dp0folio.exe"
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
