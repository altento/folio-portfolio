$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot

$python = Join-Path $env:USERPROFILE '.cache\folio-pywebview-prototype2\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python)) {
  throw "Не найдена среда pywebview: $python"
}
& $python -m PyInstaller --noconfirm --clean --onedir --windowed `
  --name folio-desktop `
  --distpath (Join-Path $PSScriptRoot 'dist\folio-webview-v164') `
  --workpath (Join-Path $PSScriptRoot 'build\folio-webview-v164') `
  --collect-all webview `
  --collect-all pythonnet `
  --collect-all clr_loader `
  --add-data 'web;web' `
  desktop_webview.py

if ($LASTEXITCODE -ne 0) { throw "PyInstaller завершился с кодом $LASTEXITCODE" }
Write-Host 'Build complete.'
