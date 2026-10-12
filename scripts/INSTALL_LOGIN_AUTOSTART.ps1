param([switch]$Remove)
# Explicit opt-in only. Uses per-user Windows Startup, no admin or network requirement.
$ErrorActionPreference='Stop'
$Root=(Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$Startup=[Environment]::GetFolderPath('Startup')
$Shortcut=Join-Path $Startup 'TwentyWatts Offline Oracle.lnk'
if ($Remove) {
 if (Test-Path $Shortcut) {Remove-Item -LiteralPath $Shortcut -Force}
 Write-Host '[PASS] Startup shortcut removed; running Oracle not stopped.'
 return
}
if (-not (Test-Path 'C:\Python314\pythonw.exe')) {throw 'Python314 not found; configure installation first'}
$w=New-Object -ComObject WScript.Shell
$s=$w.CreateShortcut($Shortcut)
$s.TargetPath='powershell.exe'
$s.Arguments='-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "'+(Join-Path $Root 'scripts\START_BACKGROUND_WINDOWS.ps1')+'"'
$s.WorkingDirectory=$Root
$s.Description='TwentyWatts localhost offline experiment on user logon; no external API'
$s.Save()
Write-Host "[PASS] Installed per-user auto-start shortcut: $Shortcut" -ForegroundColor Green
