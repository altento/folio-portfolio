$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot

& (Join-Path $PSScriptRoot 'build-webview-v163.ps1')
if ($LASTEXITCODE -ne 0) { throw "Windows WebView2 v163 build failed with exit code $LASTEXITCODE" }
