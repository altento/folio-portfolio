$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot

python -c "import PyInstaller" 2>$null
if ($LASTEXITCODE -ne 0) {
  throw "Не найден PyInstaller. Установите сборочные зависимости: python -m pip install -r requirements-build.txt"
}

python -m PyInstaller --noconfirm --clean --onefile --windowed `
  --name folio `
  --add-data 'assets;assets' `
  --add-data 'web/assets;web/assets' `
  main.py

if ($LASTEXITCODE -ne 0) {
  throw "PyInstaller завершился с кодом $LASTEXITCODE"
}

$builtExe = Join-Path $PSScriptRoot "dist\folio.exe"
$rootExe = Join-Path $PSScriptRoot "folio.exe"
try {
  Copy-Item -LiteralPath $builtExe -Destination $rootExe -Force -ErrorAction Stop
  Write-Host "Готово: $rootExe"
} catch {
  $currentExe = Join-Path $PSScriptRoot "folio-current.exe"
  Copy-Item -LiteralPath $builtExe -Destination $currentExe -Force -ErrorAction Stop
  Write-Warning "Старый folio.exe ещё запущен; его не заменял. Новая сборка сохранена: $currentExe"
  Write-Host "Запускайте приложение через Запустить приложение.bat"
}

