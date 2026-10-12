param(
  [Parameter(Mandatory=$true)][string]$Repo,
  [string]$PythonExe = 'C:\Python314\python.exe'
)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$Source = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
if (-not (Test-Path -LiteralPath (Join-Path $Source 'tw10\architecture_audit.py'))) {throw 'TW18 source missing'}
if (-not (Test-Path -LiteralPath $PythonExe)) {throw "Python missing: $PythonExe"}
if (-not (Test-Path -LiteralPath (Join-Path $Repo '.git'))) {throw 'Target is not an existing Git checkout'}
Set-Location -LiteralPath $Repo
$Expected='https://github.com/3078024889/copernicus-twentywatts.git'
$Actual=(git remote get-url origin)
if ($LASTEXITCODE -ne 0 -or $Actual -ne $Expected) {throw "Unexpected remote: $Actual"}
if ((git branch --show-current) -ne 'main') {throw 'Checkout main before syncing'}
$Dirty=@(git status --porcelain)
if ($LASTEXITCODE -ne 0 -or $Dirty.Count -gt 0) {throw 'Working tree not clean; do not overwrite local changes'}
& git pull --ff-only origin main
if ($LASTEXITCODE -ne 0) {throw 'git pull failed'}
# Copy only reviewed source and tests. Never move any checkpoint, evidence or DB.
foreach($Folder in @('tw8','tw9','tw10','tests','scripts','performance')) {
  $From=Join-Path $Source $Folder
  if (-not (Test-Path $From)) {throw "Missing source folder $Folder"}
  $To=Join-Path $Repo $Folder
  New-Item -ItemType Directory -Force -Path $To | Out-Null
  Get-ChildItem -LiteralPath $From -File -Recurse | Where-Object {
    $_.Extension -in @('.py','.ps1','.md','.txt') -and $_.FullName -notmatch '__pycache__'
  } | ForEach-Object {
    $Rel=$_.FullName.Substring($From.Length).TrimStart([char[]]@('\','/'))
    $Dest=Join-Path $To $Rel
    New-Item -ItemType Directory -Force -Path (Split-Path $Dest) | Out-Null
    Copy-Item -LiteralPath $_.FullName -Destination $Dest -Force
  }
}
Copy-Item -LiteralPath (Join-Path $Source 'README.md') -Destination (Join-Path $Repo 'README.md') -Force
$Ignore=Join-Path $Repo '.gitignore'
$Rules=@('*.sqlite','*.sqlite-*','*.sqlite3','*.db','*.db-*','*.jsonl','*.gguf','*.zip','*.bak','.env','.env.*','__pycache__/','data/','checkpoints/','artifacts/','reports/operations.json','reports/competition.json')
Add-Content -LiteralPath $Ignore -Value ($Rules -join "`n")
& git add -- .gitignore README.md tw8 tw9 tw10 tests scripts performance
if ($LASTEXITCODE -ne 0) {throw 'git add failed'}
$Files=@(git diff --cached --name-only)
foreach($File in $Files) {
  if ($File -match '(^data/|^world/|\.sqlite|\.db$|\.jsonl$|\.gguf$|\.env|\.zip$|\.bak$|__pycache__)') {throw "Unsafe staged path: $File"}
}
$OriginalEnv=$env:PYTHONPATH
try {
  $env:PYTHONPATH=$Repo
  # Full repo tests previously depended on an existing local V8 database.
  # If missing, use the source package's non-production test fixture only.
  $TargetDB=Join-Path $Repo 'data\v8.sqlite'
  if (-not (Test-Path $TargetDB)) {
    $PackDB=Join-Path $Source 'data\v8.sqlite'
    if (-not (Test-Path $PackDB)) {throw 'Verified V8 source DB missing from package'}
    New-Item -ItemType Directory -Force -Path (Split-Path $TargetDB) | Out-Null
    Copy-Item -LiteralPath $PackDB -Destination $TargetDB -ErrorAction Stop
  }
  & $PythonExe -m unittest discover -s tests -q
  if ($LASTEXITCODE -ne 0) {throw 'Tests failed; push blocked'}
  & $PythonExe -m tw10.cli inspect --source-db $TargetDB
  if ($LASTEXITCODE -ne 0) {throw 'Data integrity failed; push blocked'}
} finally { $env:PYTHONPATH=$OriginalEnv }
& git diff --cached --stat
if ($LASTEXITCODE -ne 0) {throw 'git diff failed'}
if ((@(git diff --cached --name-only)).Count -eq 0) {Write-Host 'Already synchronized; nothing to push';exit 0}
& git commit -m 'feat: paired architecture challenges and unified offline research validation'
if ($LASTEXITCODE -ne 0) {throw 'git commit failed'}
& git push origin main
if ($LASTEXITCODE -ne 0) {throw 'git push failed; commit remains local'}
Write-Host 'MAIN PUSH VERIFIED' -ForegroundColor Green
& git log -1 --oneline
