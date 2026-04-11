[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "../..")).ProviderPath
$buildPs1 = Join-Path $repoRoot "build/build.ps1"
$installDepsPs1 = Join-Path $repoRoot "build/install-deps.ps1"
$smokeOverlayPs1 = Join-Path $repoRoot "build/smoke-overlay.ps1"
$wslCommonPs1 = Join-Path $repoRoot "build/wsl-common.ps1"

foreach ($path in @($buildPs1, $installDepsPs1, $smokeOverlayPs1, $wslCommonPs1)) {
    if (-not (Test-Path $path -PathType Leaf)) {
        throw "missing required script: $path"
    }
}

$wslCommonSource = Get-Content -Raw $wslCommonPs1
foreach ($signature in @(
    "function Assert-WslInstalled",
    "function Get-WslDistroNames",
    "function Resolve-WslDistro",
    "function Convert-ToWslPath",
    "function Invoke-WslRepoBash"
)) {
    if ($wslCommonSource -notmatch [regex]::Escape($signature)) {
        throw "wsl-common.ps1 is missing expected function: $signature"
    }
}

$buildSource = Get-Content -Raw $buildPs1
if ($buildSource -notmatch "EnableBrave") {
    throw "build.ps1 does not expose the EnableBrave switch."
}
if ($buildSource -notmatch "Invoke-WslRepoBash") {
    throw "build.ps1 does not call Invoke-WslRepoBash."
}

$installDepsSource = Get-Content -Raw $installDepsPs1
if ($installDepsSource -notmatch "Invoke-WslRepoBash") {
    throw "install-deps.ps1 does not call Invoke-WslRepoBash."
}

$smokeOverlaySource = Get-Content -Raw $smokeOverlayPs1
if ($smokeOverlaySource -notmatch "Invoke-WslRepoBash") {
    throw "smoke-overlay.ps1 does not call Invoke-WslRepoBash."
}

$script:WslCalls = @()

function global:wsl.exe {
    param(
        [Parameter(ValueFromRemainingArguments = $true)]
        [string[]]$WslArgs
    )

    $script:WslCalls += ,($WslArgs -join " ")
    $global:LASTEXITCODE = 0

    if ($WslArgs -contains "-l" -and $WslArgs -contains "-q") {
        return @("Ubuntu", "Debian")
    }
    if ($WslArgs -contains "-l" -and $WslArgs -contains "-v") {
        return @(
            "  NAME      STATE   VERSION",
            "* Ubuntu    Running 2",
            "  Debian    Stopped 2"
        )
    }
    if ($WslArgs -contains "wslpath") {
        return "/mnt/c/Users/runner/work/NM-OS/NM-OS"
    }
    return @()
}

. $wslCommonPs1

$resolvedDefault = Resolve-WslDistro -Distro ""
if ($resolvedDefault -ne "Ubuntu") {
    throw "Resolve-WslDistro did not select the starred default distro."
}

$resolvedExplicit = Resolve-WslDistro -Distro "Debian"
if ($resolvedExplicit -ne "Debian") {
    throw "Resolve-WslDistro did not honor explicit distro selection."
}

$converted = Convert-ToWslPath -WindowsPath "C:\Users\runner\work\NM-OS\NM-OS" -Distro "Ubuntu"
if (-not $converted.StartsWith("/mnt/")) {
    throw "Convert-ToWslPath returned an unexpected path: $converted"
}

$script:WslCalls = @()
Invoke-WslRepoBash `
    -RepoPath "C:\Users\runner\work\NM-OS\NM-OS" `
    -Distro "Ubuntu" `
    -Script "./build/build.sh" `
    -Arguments @("--example")

$invokeCall = $script:WslCalls | Where-Object { $_.Contains("--cd") -and $_.Contains("bash -lc") } | Select-Object -First 1
if (-not $invokeCall) {
    throw "Invoke-WslRepoBash did not invoke wsl.exe with --cd."
}
if ($invokeCall -notmatch "bash -lc \./build/build\.sh bash --example$") {
    throw "Invoke-WslRepoBash argument forwarding does not match expected wrapper contract."
}

Write-Host "Windows PowerShell wrapper and WSL bridge checks passed."
