$ErrorActionPreference='Stop'
$Root=(Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$Stop=Join-Path $Root 'data\STOP_OFFLINE_ORACLE'
New-Item -ItemType File -Path $Stop -Force | Out-Null
Write-Host "Requested offline training stop: $Stop (server remains read-only until closed)." -ForegroundColor Yellow
