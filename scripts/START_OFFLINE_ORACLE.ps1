param(
 [ValidateRange(1024,65535)][int]$Port=28722,
 [ValidateRange(1,86400)][int]$Interval=20,
 [ValidateRange(1,25)][int]$Cycles=1,
 [ValidateRange(1,12)][int]$Participants=12,
 [string]$PythonExe='C:\Python314\python.exe',
 [switch]$ReadOnly
)
$ErrorActionPreference='Stop'
$Root=(Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$SourceDB=Join-Path $Root 'data\v8.sqlite'
$StateDB=Join-Path $Root 'data\v14_offline.sqlite'
$StopFile=Join-Path $Root 'data\STOP_OFFLINE_ORACLE'
$Report=Join-Path $Root 'reports\offline_oracle_status.json'
if (-not (Test-Path -LiteralPath $PythonExe)) {throw "Python not found: $PythonExe"}
if (-not (Test-Path -LiteralPath $SourceDB)) {throw "Verified 7777 experimental source missing: $SourceDB"}
if (Test-Path -LiteralPath $StopFile) {throw "Offline stop file exists: $StopFile; manually remove only when ready to resume"}
$Runner=@'
import sys,runpy
root,source,state,port,interval,cycles,participants,stop,report,readonly=sys.argv[1:]
sys.path.insert(0,root)
sys.argv=['tw10.offline_oracle','--source-db',source,'--state-db',state,'--port',port,'--interval',interval,'--cycles',cycles,'--participants',participants,'--stop-file',stop,'--report',report]
if readonly=='True':sys.argv+=['--read-only']
runpy.run_module('tw10.offline_oracle',run_name='__main__')
'@
Write-Host "Offline Oracle http://127.0.0.1:$Port/ (CTRL+C stops; V3 untouched)" -ForegroundColor Cyan
& $PythonExe -c $Runner $Root $SourceDB $StateDB "$Port" "$Interval" "$Cycles" "$Participants" $StopFile $Report "$([bool]$ReadOnly)"
if ($LASTEXITCODE -ne 0) {throw "Offline Oracle exited with $LASTEXITCODE"}
