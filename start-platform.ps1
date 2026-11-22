param([int]$Port = 8000, [string]$PythonPath = '', [string]$NodePath = '', [switch]$OpenBrowser)
$ErrorActionPreference = 'Stop'
$repoRoot = $PSScriptRoot
$operatorFile = Join-Path $env:LOCALAPPDATA 'CapstoneTraining/operator.json'
if (!$PythonPath) {
    $PythonPath = Join-Path $repoRoot '.venv/Scripts/python.exe'
    if (!(Test-Path -LiteralPath $PythonPath) -and (Test-Path -LiteralPath $operatorFile)) {
        $PythonPath = (Get-Content -LiteralPath $operatorFile -Raw | ConvertFrom-Json).python
    }
}
if (!$PythonPath -or !(Test-Path -LiteralPath $PythonPath)) { throw 'Run setup-platform.ps1 once with Python 3.12 and the approved private lab location.' }
$platformArgs = @((Join-Path $repoRoot 'scripts/platform_control.py'), 'start', '--port', "$Port")
if ($NodePath) { $platformArgs += @('--node', $NodePath) }
if ($OpenBrowser) { $platformArgs += '--open' }
& $PythonPath @platformArgs
if ($LASTEXITCODE -ne 0) { throw 'Platform startup failed. Read the error above; no exercise was started.' }
