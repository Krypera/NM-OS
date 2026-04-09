[CmdletBinding()]
param(
    [string]$Distro = "",
    [string]$ImagePath = ""
)

$ErrorActionPreference = "Stop"
$repoPath = (Resolve-Path (Join-Path $PSScriptRoot "..")).ProviderPath
. (Join-Path $PSScriptRoot "wsl-common.ps1")

if ($ImagePath) {
    $resolvedDistro = Resolve-WslDistro -Distro $Distro
    $wslImagePath = Convert-ToWslPath -WindowsPath (Resolve-Path $ImagePath).ProviderPath -Distro $resolvedDistro
    Invoke-WslRepoBash -RepoPath $repoPath -Distro $resolvedDistro -Script './build/smoke-qemu.sh "$1"' -Arguments @($wslImagePath)
} else {
    Invoke-WslRepoBash -RepoPath $repoPath -Distro $Distro -Script "./build/smoke-qemu.sh"
}
