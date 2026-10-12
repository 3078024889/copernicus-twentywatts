param(
 [string]$PythonExe='C:\Python314\pythonw.exe',
 [ValidateRange(1024,65535)][int]$Port=28722,
 [ValidateRange(1,86400)][int]$Interval=20,
 [ValidateRange(1,25)][int]$Cycles=1,
 [ValidateRange(1,12)][int]$Participants=12
)
$ErrorActionPreference='Stop'
$Root=(Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$Source=Join-Path $Root 'data\v8.sqlite'
$State=Join-Path $Root 'data\v14_offline.sqlite'
$Stop=Join-Path $Root 'data\STOP_OFFLINE_ORACLE'
$Report=Join-Path $Root 'reports\offline_oracle_status.json'
if (-not (Test-Path $PythonExe)) {throw "Python GUI executable not found: $PythonExe"}
if (-not (Test-Path $Source)) {throw "Missing verified source: $Source"}
if (Test-Path $Stop) {throw "Stop request exists. Review/remove before starting: $Stop"}
$Listening=Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
if ($Listening) {throw "Port $Port already in use. Refusing to interrupt existing owner."}
# Argument list quotes preserve paths with spaces; always restrict listener to 127.0.0.1.
$Arg='-m tw10.offline_oracle --source-db "{0}" --state-db "{1}" --port {2} --interval {3} --cycles {4} --participants {5} --stop-file "{6}" --report "{7}"' -f $Source,$State,$Port,$Interval,$Cycles,$Participants,$Stop,$Report
$p=Start-Process -FilePath $PythonExe -WorkingDirectory $Root -ArgumentList $Arg -PassThru
Start-Sleep -Seconds 2
if ($p.HasExited) {throw "Oracle exited on startup with code $($p.ExitCode). Run START_OFFLINE_ORACLE.ps1 to see errors."}
try {
 $response=Invoke-RestMethod -Uri "http://127.0.0.1:$Port/api/live" -TimeoutSec 10
 if ($response.source.configurations -ne 7777) {throw 'Source registry verification failed'}
 Write-Host "[PASS] Offline Oracle PID=$($p.Id): http://127.0.0.1:$Port/" -ForegroundColor Green
} catch {
 throw "Oracle process exists but health validation failed: $($_.Exception.Message)"
}
