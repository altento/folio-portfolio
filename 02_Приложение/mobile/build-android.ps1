$ErrorActionPreference = 'Stop'
$sdk = Join-Path $env:USERPROFILE '.cache\folio-android-sdk'
$jdk = Join-Path $env:USERPROFILE '.cache\folio-android-build-tools\temurin-unpack\jdk-21.0.13+9'
$socketDir = 'C:\tmpj\sockets'
if (-not (Test-Path (Join-Path $sdk 'platform-tools\adb.exe'))) { throw "Android SDK not found at $sdk" }
if (-not (Test-Path (Join-Path $jdk 'bin\java.exe'))) { throw "Temurin JDK 21 not found at $jdk" }
$environmentNames = @('ANDROID_HOME', 'ANDROID_SDK_ROOT', 'JAVA_HOME', 'JAVA_TOOL_OPTIONS', 'TEMP', 'TMP', 'Path')
$previousEnvironment = @{}
foreach ($name in $environmentNames) {
    $previousEnvironment[$name] = [Environment]::GetEnvironmentVariable($name, 'Process')
}
$previousLocation = Get-Location
$buildExitCode = 1
try {
    New-Item -ItemType Directory -Force -Path $socketDir | Out-Null
    # Gradle/JDK use Windows AF_UNIX sockets for selector wakeups. Keep their
    # temporary socket paths short and valid for this child build process.
    $env:TEMP = $socketDir
    $env:TMP = $socketDir
    $env:ANDROID_HOME = $sdk
    $env:ANDROID_SDK_ROOT = $sdk
    $env:JAVA_HOME = $jdk
    $env:Path = "$jdk\bin;$sdk\platform-tools;$sdk\cmdline-tools\latest\bin;$env:Path"
    $env:JAVA_TOOL_OPTIONS = "-Djdk.net.unixdomain.tmpdir=$socketDir"
    Set-Location $PSScriptRoot
    npm run android:debug
    $buildExitCode = $LASTEXITCODE
} finally {
    Set-Location $previousLocation
    foreach ($name in $environmentNames) {
        $oldValue = $previousEnvironment[$name]
        if ($null -eq $oldValue) {
            Remove-Item "Env:$name" -ErrorAction SilentlyContinue
        } else {
            [Environment]::SetEnvironmentVariable($name, $oldValue, 'Process')
        }
    }
}
if ($buildExitCode -ne 0) { exit $buildExitCode }

