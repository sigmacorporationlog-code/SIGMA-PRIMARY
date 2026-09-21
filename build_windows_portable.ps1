﻿[CmdletBinding()]
param([switch]$Clean)
$ErrorActionPreference = "Stop"
& (Join-Path $PSScriptRoot "build_windows.ps1") -Clean:$Clean -SkipInstaller
exit $LASTEXITCODE
