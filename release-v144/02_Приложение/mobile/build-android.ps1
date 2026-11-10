$ErrorActionPreference = 'Stop'
$sdkCandidates = @(
    $env:ANDROID_HOME,
    $env:ANDROID_SDK_ROOT,
    (Join-Path $env:LOCALAPPDATA 'Android\Sdk'),
    (Join-Path $env:USERPROFILE '.cache\folio-android-sdk')
) | Where-Object { $_ } | Select-Object -Unique
$sdk = $sdkCandidates | Where-Object {
    (Test-Path (Join-Path $_ 'platforms\android-36\android.jar')) -and
    (Test-Path (Join-Path $_ 'build-tools\36.0.0\aapt.exe')) -and
    (Test-Path (Join-Path $_ 'platform-tools\adb.exe'))
} | Select-Object -First 1
$jdkCandidates = @(
    $env:JAVA_HOME,
    (Join-Path $env:LOCALAPPDATA 'Programs\Folio-Temurin21'),
    (Join-Path $env:USERPROFILE '.cache\folio-android-build-tools\temurin-unpack\jdk-21.0.13+9')
) | Where-Object { $_ } | Select-Object -Unique
$jdk = $null
foreach ($candidate in $jdkCandidates) {
    $java = Join-Path $candidate 'bin\java.exe'
    if (Test-Path $java) {
        $previousErrorPreference = $ErrorActionPreference
        $ErrorActionPreference = 'Continue'
        try {
            $javaVersion = (& $java -version 2>&1 | Out-String)
        } finally {
            $ErrorActionPreference = $previousErrorPreference
        }
        if ($javaVersion -match 'version "21\.') {
            $jdk = $candidate
            break
        }
    }
}
$socketDir = 'C:\tmpj\sockets'
if (-not $sdk) { throw 'Android SDK Platform 36, Build-Tools 36.0.0, or Platform-Tools is missing. Set ANDROID_HOME or install the required SDK packages.' }
if (-not $jdk) { throw 'Java 21 is required. Set JAVA_HOME to a JDK 21 installation.' }
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

python (Join-Path $PSScriptRoot 'refresh-android-delivery.py')
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

