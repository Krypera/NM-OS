function Assert-WslInstalled {
    if (-not (Get-Command wsl.exe -ErrorAction SilentlyContinue)) {
        throw "wsl.exe not found. Install WSL2 first."
    }
}

function Get-WslDistroNames {
    $names = & wsl.exe -l -q 2>$null
    return @($names | ForEach-Object { $_.Trim() } | Where-Object { $_ })
}

function Resolve-WslDistro {
    param(
        [string]$Distro
    )

    $distros = Get-WslDistroNames
    if (-not $distros -or $distros.Count -eq 0) {
        throw "No WSL distributions are installed."
    }

    if ($Distro) {
        if ($distros -notcontains $Distro) {
            throw "WSL distribution '$Distro' not found. Installed distros: $($distros -join ', ')"
        }
        return $Distro
    }

    $defaultLine = & wsl.exe -l -v 2>$null | Select-String "^\s*\*"
    if ($defaultLine) {
        foreach ($name in $distros) {
            if ($defaultLine.ToString() -match [regex]::Escape($name)) {
                return $name
            }
        }
    }

    return $distros[0]
}

function Convert-ToWslPath {
    param(
        [string]$WindowsPath,
        [string]$Distro
    )

    $result = (& wsl.exe -d $Distro -- wslpath -a $WindowsPath).Trim()
    if (-not $result) {
        throw "Could not convert Windows path to WSL path: $WindowsPath"
    }
    return $result
}

function Invoke-WslRepoBash {
    param(
        [string]$RepoPath,
        [string]$Distro,
        [string]$Script,
        [string[]]$Arguments = @()
    )

    Assert-WslInstalled
    $resolvedDistro = Resolve-WslDistro -Distro $Distro
    $repoWslPath = Convert-ToWslPath -WindowsPath $RepoPath -Distro $resolvedDistro
    & wsl.exe -d $resolvedDistro --cd $repoWslPath -- bash -lc $Script bash @Arguments
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}
