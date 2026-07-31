#!/usr/bin/env pwsh
# Install dashboard-hub launchers (dashboard-server, dashboard-hub, dash) into
# %USERPROFILE%\.local\bin and make sure that directory is on the User PATH,
# so the commands work from any new PowerShell, cmd, or Git Bash session.

$ErrorActionPreference = "Stop"

$toolRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$localBin = Join-Path $HOME ".local\bin"
New-Item -ItemType Directory -Force -Path $localBin | Out-Null

function Install-Shim {
    param(
        [string]$Name,
        [string]$Subcommand
    )
    $shimPath = Join-Path $localBin "$Name.cmd"
    @"
@echo off
setlocal
set "PYTHONPATH=$toolRoot;%PYTHONPATH%"
python -m dashboard_hub $Subcommand %*
"@ | Set-Content -Path $shimPath -Encoding ASCII
    Write-Host "Installed $shimPath"
}

Install-Shim -Name "dashboard-server" -Subcommand "server"
Install-Shim -Name "dashboard-hub" -Subcommand ""
Install-Shim -Name "dash" -Subcommand "dash"

$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
$pathEntries = $userPath -split ";"
if ($pathEntries -notcontains $localBin) {
    [Environment]::SetEnvironmentVariable("Path", "$userPath;$localBin", "User")
    Write-Host "Added $localBin to your User PATH. Open a new terminal for it to take effect."
} else {
    Write-Host "$localBin is already on your User PATH."
}
