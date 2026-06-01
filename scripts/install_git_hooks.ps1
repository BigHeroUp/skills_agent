$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $ProjectRoot

git config core.hooksPath .githooks
Write-Host "OK Git hooks configurati su .githooks"
