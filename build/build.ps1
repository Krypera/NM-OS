[CmdletBinding()]
param(
    [string]$Distro = "",
    [switch]$EnableBrave
)

$ErrorActionPreference = "Stop"
$repoPath = (Resolve-Path (Join-Path $PSScriptRoot "..")).ProviderPath
. (Join-Path $PSScriptRoot "wsl-common.ps1")

if ($EnableBrave) {
    Invoke-WslRepoBash -RepoPath $repoPath -Distro $Distro -Script "NMOS_ENABLE_BRAVE=1 ./build/build.sh"
} else {
    Invoke-WslRepoBash -RepoPath $repoPath -Distro $Distro -Script "./build/build.sh"
}
