param(
    [switch]$ForceRestart
)

$ErrorActionPreference = "Stop"

function Write-Step {
    param([string]$Message)
    Write-Host ""
    Write-Host "[STEP] $Message" -ForegroundColor Cyan
}

function Write-Info {
    param([string]$Message)
    Write-Host "[INFO] $Message" -ForegroundColor Green
}

function Write-WarnLine {
    param([string]$Message)
    Write-Host "[WARN] $Message" -ForegroundColor Yellow
}

function Ensure-Command {
    param(
        [string]$CommandName,
        [string]$Hint
    )

    if (-not (Get-Command $CommandName -ErrorAction SilentlyContinue)) {
        throw "Missing command $CommandName. $Hint"
    }
}

function Get-PortListener {
    param([int]$Port)
    return Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
}

function Stop-PortListener {
    param([int]$Port)

    $listener = Get-PortListener -Port $Port
    if (-not $listener) {
        return
    }

    Write-WarnLine "Port $Port is already used by process $($listener.OwningProcess). Stopping it now."
    Stop-Process -Id $listener.OwningProcess -Force
    Start-Sleep -Seconds 1
}

function Wait-HttpReady {
    param(
        [string]$Url,
        [int]$TimeoutSeconds = 30
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        try {
            $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 5
            if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 500) {
                return $true
            }
        }
        catch {
        }

        Start-Sleep -Seconds 1
    }

    return $false
}

function Ensure-BackendEnvironment {
    param(
        [string]$BackendDir,
        [string]$BackendPython
    )

    if (-not (Test-Path $BackendPython)) {
        Write-Step "backend\\.venv not found. Creating backend virtual environment."
        Push-Location $BackendDir
        try {
            python -m venv .venv
        }
        finally {
            Pop-Location
        }
    }

    Write-Step "Checking backend dependencies."
    & $BackendPython -c "import fastapi, uvicorn, galois, pydantic" *> $null
    if ($LASTEXITCODE -ne 0) {
        Write-Step "Backend dependencies are missing. Installing requirements.txt."
        Push-Location $BackendDir
        try {
            & $BackendPython -m pip install -r requirements.txt
        }
        finally {
            Pop-Location
        }
    }
    else {
        Write-Info "Backend dependencies are ready."
    }
}

function Ensure-FrontendEnvironment {
    param([string]$FrontendDir)

    $nodeModulesDir = Join-Path $FrontendDir "node_modules"
    if (-not (Test-Path $nodeModulesDir)) {
        Write-Step "frontend\\node_modules not found. Installing frontend dependencies."
        Push-Location $FrontendDir
        try {
            npm install
        }
        finally {
            Pop-Location
        }
    }
    else {
        Write-Info "Frontend dependencies are ready."
    }
}

function Start-BackendWindow {
    param([string]$BackendDir)

    $backendCommand = @(
        '$host.UI.RawUI.WindowTitle = ''Traceable Secret Sharing - Backend'''
        "Set-Location '$BackendDir'"
        "& '.\.venv\Scripts\python.exe' -m uvicorn main:app --reload --host 127.0.0.1 --port 8000"
    ) -join "; "

    Start-Process -FilePath "powershell.exe" -ArgumentList @("-NoExit", "-Command", $backendCommand) -WorkingDirectory $BackendDir | Out-Null
}

function Start-FrontendWindow {
    param([string]$FrontendDir)

    $frontendCommand = @(
        '$host.UI.RawUI.WindowTitle = ''Traceable Secret Sharing - Frontend'''
        "Set-Location '$FrontendDir'"
        "& npm.cmd run dev"
    ) -join "; "

    Start-Process -FilePath "powershell.exe" -ArgumentList @("-NoExit", "-Command", $frontendCommand) -WorkingDirectory $FrontendDir | Out-Null
}

$rootDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$backendDir = Join-Path $rootDir "backend"
$frontendDir = Join-Path $rootDir "frontend"
$backendPython = Join-Path $backendDir ".venv\Scripts\python.exe"

Write-Step "Checking required commands."
Ensure-Command -CommandName "python" -Hint "Install Python 3.11 and make sure python is available in PATH."
Ensure-Command -CommandName "node" -Hint "Install Node.js."
Ensure-Command -CommandName "npm" -Hint "Install npm."
Ensure-Command -CommandName "powershell.exe" -Hint "This script needs PowerShell to open backend and frontend windows."
Write-Info "Required commands are available."

Ensure-BackendEnvironment -BackendDir $backendDir -BackendPython $backendPython
Ensure-FrontendEnvironment -FrontendDir $frontendDir

if ($ForceRestart) {
    Write-Step "Force restart is enabled. Cleaning ports 8000 and 5173."
    Stop-PortListener -Port 8000
    Stop-PortListener -Port 5173
}

Write-Step "Checking backend port 8000."
$backendListener = Get-PortListener -Port 8000
if ($backendListener) {
    Write-WarnLine "Port 8000 is already in use by process $($backendListener.OwningProcess). Skipping backend launch."
}
else {
    Write-Step "Starting backend service."
    Start-BackendWindow -BackendDir $backendDir
}

if (Wait-HttpReady -Url "http://127.0.0.1:8000/" -TimeoutSeconds 30) {
    Write-Info "Backend is ready: http://127.0.0.1:8000/"
}
else {
    Write-WarnLine "Backend launch command was sent, but readiness was not confirmed in 30 seconds. Check the backend window."
}

Write-Step "Checking frontend port 5173."
$frontendListener = Get-PortListener -Port 5173
if ($frontendListener) {
    Write-WarnLine "Port 5173 is already in use by process $($frontendListener.OwningProcess). Skipping frontend launch."
}
else {
    Write-Step "Starting frontend service."
    Start-FrontendWindow -FrontendDir $frontendDir
}

if (Wait-HttpReady -Url "http://127.0.0.1:5173/" -TimeoutSeconds 30) {
    Write-Info "Frontend is ready: http://127.0.0.1:5173/"
}
else {
    Write-WarnLine "Frontend launch command was sent, but readiness was not confirmed in 30 seconds. Check the frontend window."
}

Write-Host ""
Write-Host "========================================" -ForegroundColor DarkCyan
Write-Host "Startup flow finished." -ForegroundColor Cyan
Write-Host "Frontend: http://127.0.0.1:5173/" -ForegroundColor White
Write-Host "Backend:  http://127.0.0.1:8000/" -ForegroundColor White
Write-Host "Docs:     http://127.0.0.1:8000/docs" -ForegroundColor White
Write-Host "To force restart existing processes, run:" -ForegroundColor DarkYellow
Write-Host "powershell -ExecutionPolicy Bypass -File .\start-project-safe.ps1 -ForceRestart" -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor DarkCyan
