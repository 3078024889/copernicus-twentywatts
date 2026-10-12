param(
  [ValidateSet('inspect','run','test')][string]$Action='inspect',
  [ValidateRange(1,25)][int]$Cycles=1,
  [ValidateRange(1,12)][int]$Participants=12,
  [string]$PythonExe='',
  [switch]$Repeat,
  [ValidateRange(15,86400)][int]$IntervalSeconds=600
)
$ErrorActionPreference='Stop'
$Root=(Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Set-Location $Root
if (-not $PythonExe) {
  $known='D:\.pnpm-store\v10\projects\9e93c800ae9918aa01436d35d6d66abf\_local\r64-db-runtime\python-test\python.exe'
  if (Test-Path $known) { $PythonExe=$known }
  else {
    $candidate=Get-Command python -ErrorAction SilentlyContinue
    if ($candidate -and $candidate.Source -notlike '*\WindowsApps\*') {$PythonExe=$candidate.Source}
  }
}
if (-not $PythonExe -or -not (Test-Path $PythonExe)) {throw 'Python interpreter not found. Supply -PythonExe C:\path\python.exe'}
& $PythonExe --version
if ($LASTEXITCODE -ne 0) {throw 'Python interpreter failed'}
# Supports embedded/isolated Python where -m package import does not resolve current directory.
$code = @'
import sys,runpy
sys.path.insert(0,sys.argv[1])
action=sys.argv[2]
if action=='test':
 import unittest
 r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.discover('tests'))
 raise SystemExit(0 if r.wasSuccessful() else 1)
sys.argv=['tw10.operations',action,'--v8-db','data/v8.sqlite','--db','data/v9.sqlite','--cycles',sys.argv[3],'--participants',sys.argv[4],'--output','reports/operations.json']
runpy.run_module('tw10.operations',run_name='__main__')
'@
if ($Repeat -and $Action -ne 'run') {throw '-Repeat can only be used with -Action run'}
if ($Repeat) { Write-Host 'Foreground bounded research loop: Ctrl+C to stop. No autonomous production promotion.' }
do {
  & $PythonExe -c $code $Root $Action $Cycles $Participants
  if ($LASTEXITCODE -ne 0) {throw "TwentyWatts $Action FAILED (exit $LASTEXITCODE)"}
  if ($Repeat) {Start-Sleep -Seconds $IntervalSeconds}
} while ($Repeat)
