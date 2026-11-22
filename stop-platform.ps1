param([string]$PythonPath = '')
$ErrorActionPreference = 'Stop'
if (!$PythonPath) {
    $PythonPath = Join-Path $PSScriptRoot '.venv/Scripts/python.exe'
    $operatorFile = Join-Path $env:LOCALAPPDATA 'CapstoneTraining/operator.json'
    if (!(Test-Path -LiteralPath $PythonPath) -and (Test-Path -LiteralPath $operatorFile)) {
        $PythonPath = (Get-Content -LiteralPath $operatorFile -Raw | ConvertFrom-Json).python
    }
}
if (!$PythonPath -or !(Test-Path -LiteralPath $PythonPath)) { throw 'The configured platform Python environment was not found.' }
& $PythonPath (Join-Path $PSScriptRoot 'scripts/platform_control.py') stop
if ($LASTEXITCODE -ne 0) { throw 'Platform stop did not finish. Read the error; no unrelated process was terminated.' }
