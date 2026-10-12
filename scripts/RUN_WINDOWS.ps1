param(
  [ValidateSet('test','inspect','train','gate','benchmark','benchmark-repeat','verify')][string]$Action='verify',
  [ValidateRange(1,100)][int]$Batches=1,
  [ValidateRange(1,25)][int]$Cycles=1,
  [ValidateRange(1,12)][int]$Participants=12,
  [string]$PythonExe='',
  [string]$SourceDB='',
  [string]$StateDB='',
  [string]$Report=''
)
$ErrorActionPreference='Stop'
$Root=(Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$FallbackPython='D:\.pnpm-store\v10\projects\9e93c800ae9918aa01436d35d6d66abf\_local\r64-db-runtime\python-test\python.exe'
if (-not $PythonExe -and (Test-Path -LiteralPath $FallbackPython)) { $PythonExe=$FallbackPython }
if (-not $PythonExe -and (Get-Command py -ErrorAction SilentlyContinue)) { $PythonExe=(Get-Command py).Source }
if (-not $PythonExe) { throw 'Python executable required: -PythonExe <full path>' }
if (-not (Test-Path -LiteralPath $PythonExe)) { throw "Python not found: $PythonExe" }
if (-not $SourceDB) { $SourceDB=Join-Path $Root 'data\v8.sqlite' }
if (-not $StateDB) { $StateDB=Join-Path $Root 'data\v11.sqlite' }
if (-not $Report) { $Report=Join-Path $Root 'reports\latest.json' }
$SourceDB=[IO.Path]::GetFullPath($SourceDB)
$StateDB=[IO.Path]::GetFullPath($StateDB)
$Report=[IO.Path]::GetFullPath($Report)
$Runner=@'
import sys,runpy
root,action,src,state,batches,cycles,participants,report=sys.argv[1:]
sys.path.insert(0,root)
sys.argv=['tw10.cli',action,'--root',root,'--source-db',src,'--state-db',state,'--batches',batches,'--cycles',cycles,'--participants',participants,'--report',report]
runpy.run_module('tw10.cli',run_name='__main__')
'@
function Invoke-Research([string]$Step) {
  & $PythonExe -c $Runner $Root $Step $SourceDB $StateDB "$Batches" "$Cycles" "$Participants" $Report
  if ($LASTEXITCODE -ne 0) { throw "TwentyWatts $Step failed ($LASTEXITCODE); halted, no promotion or publish" }
}
if ($Action -eq 'verify') {
  Invoke-Research 'test'
  Invoke-Research 'inspect'
  Invoke-Research 'gate'
  Write-Host '[PASS] Operational verification complete. Certification is separately gated.' -ForegroundColor Green
} else {
  Invoke-Research $Action
}
