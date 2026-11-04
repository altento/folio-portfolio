$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot

python -m PyInstaller --noconfirm --clean --onefile --windowed `
  --name folio `
  --add-data 'assets;assets' `
  --add-data 'web/assets;web/assets' `
  main.py

if ($LASTEXITCODE -ne 0) {
  throw "PyInstaller завершился с кодом $LASTEXITCODE"
}

Copy-Item -LiteralPath (Join-Path $PSScriptRoot "dist\folio.exe") -Destination (Join-Path $PSScriptRoot "folio.exe") -Force
Write-Host "Готово: $PSScriptRoot\folio.exe"

