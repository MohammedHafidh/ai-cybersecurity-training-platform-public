param([Parameter(Mandatory=$true)][string]$LabRoot, [string]$PythonPath = 'python', [string]$NodePath = '')
$ErrorActionPreference = 'Stop'
Push-Location $PSScriptRoot
$previousHub = $env:HF_HOME
$previousPythonPath = $env:PYTHONPATH
try {
    & $PythonPath -c 'import sys; assert sys.version_info[:2] == (3,12), "Python 3.12 is required"'
    if ($LASTEXITCODE -ne 0) { throw 'Choose a Python 3.12 executable using -PythonPath.' }
    $venvPython = Join-Path $PSScriptRoot '.venv/Scripts/python.exe'
    if (!(Test-Path -LiteralPath $venvPython)) {
        & $PythonPath -m venv .venv
        if ($LASTEXITCODE -ne 0) { throw 'Could not create the platform virtual environment.' }
    }
    & $venvPython -c 'import sys; assert sys.version_info[:2] == (3,12), "Existing environment must use Python 3.12"'
    if ($LASTEXITCODE -ne 0) { throw 'The existing .venv is incompatible; select a clean checkout/environment.' }
    & $venvPython -m pip install --index-url https://download.pytorch.org/whl/cpu torch==2.15.0+cpu
    if ($LASTEXITCODE -ne 0) { throw 'CPU PyTorch installation failed.' }
    & $venvPython -m pip install -r backend/requirements.txt -r requirements/day27.txt -r requirements/day46.txt
    if ($LASTEXITCODE -ne 0) { throw 'Platform dependency installation failed.' }
    $configArgs = @('scripts/platform_control.py','configure','--lab-root',$LabRoot)
    if ($NodePath) { $configArgs += @('--node',$NodePath) }
    & $venvPython @configArgs
    if ($LASTEXITCODE -ne 0) { throw 'Approved lab setup failed. Existing private evidence was not changed.' }
    $env:HF_HOME = Join-Path $env:LOCALAPPDATA 'CapstoneTraining/models'
    $env:PYTHONPATH = 'backend'
    & $venvPython -c 'from app.detection.retrieval import load_encoder; load_encoder(local_files_only=False)'
    if ($LASTEXITCODE -ne 0) { throw 'Embedding model download failed; guides remain available but local retrieval needs repair.' }
    Write-Host 'Setup complete. Ensure Ollama has gemma3:1b, then use start-platform.ps1. Setup did not execute an attack.'
} finally { $env:HF_HOME = $previousHub; $env:PYTHONPATH = $previousPythonPath; Pop-Location }
