[CmdletBinding()]
param(
    [string]$Distro = ""
)

$ErrorActionPreference = "Stop"
$repoPath = (Resolve-Path (Join-Path $PSScriptRoot "..")).ProviderPath
. (Join-Path $PSScriptRoot "wsl-common.ps1")

Invoke-WslRepoBash -RepoPath $repoPath -Distro $Distro -Script "./build/smoke-overlay.sh"
