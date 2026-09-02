# Bazaario PowerShell control script for Windows
param([string]$Command = "help")

$ErrorActionPreference = "Stop"
$ApiPort = if ($env:BAZAARIO_API_PORT) { $env:BAZAARIO_API_PORT } else { "8000" }
$WebPort = if ($env:BAZAARIO_WEB_PORT) { $env:BAZAARIO_WEB_PORT } else { "5173" }
$Py = ".venv\Scripts\python.exe"

function Ensure-Venv {
    if (-not (Test-Path $Py)) {
        Write-Host "Virtualenv missing or incomplete. Running setup first..."
        & $PSCommandPath setup
    }
}

switch ($Command) {
    "setup" {
        python -m venv .venv
        & $Py -m pip install --upgrade pip
        & $Py -m pip install -r requirements.txt
        Set-Location frontend
        if (-not (Test-Path node_modules)) { npm install }
        Set-Location ..
        Write-Host "Setup complete. Next: .\bazaario.ps1 seed; .\bazaario.ps1 dev"
    }
    "seed" {
        Ensure-Venv
        & $Py seed.py
    }
    "api" {
        Ensure-Venv
        & $Py -m flask --app backend.bazaario run --host 127.0.0.1 --port $ApiPort
    }
    "web" {
        Set-Location frontend
        npm run dev -- --host 127.0.0.1 --port $WebPort
    }
    "dev" {
        Ensure-Venv
        Write-Host "Starting Flask API on port $ApiPort..."
        Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PWD'; .venv\Scripts\python.exe -m flask --app backend.bazaario run --host 127.0.0.1 --port $ApiPort"
        Set-Location frontend
        npm run dev -- --host 127.0.0.1 --port $WebPort
    }
    "test" {
        Ensure-Venv
        & $Py -m pytest tests/ -q
    }
    "build" {
        Set-Location frontend
        npm run build
    }
    "status" {
        foreach ($target in @(@{Name="api"; Port=$ApiPort}, @{Name="web"; Port=$WebPort})) {
            try {
                $res = Invoke-WebRequest -Uri "http://127.0.0.1:$($target.Port)/" -UseBasicParsing -TimeoutSec 2 -ErrorAction SilentlyContinue
                $code = $res.StatusCode
            } catch {
                if ($_.Exception.Response) {
                    $code = [int]$_.Exception.Response.StatusCode
                } else {
                    $code = 0
                }
            }
            if ($code -eq 0) {
                Write-Host "$($target.Name) (port $($target.Port)): down"
            } else {
                Write-Host "$($target.Name) (port $($target.Port)): up (HTTP $code)"
            }
        }
    }
    default {
        Write-Host "Usage: .\bazaario.ps1 <command>"
        Write-Host "  setup   first-time install: python venv + pip + npm"
        Write-Host "  seed    reset and seed the database"
        Write-Host "  api     run the Flask API on 127.0.0.1:5050"
        Write-Host "  web     run the Vite frontend on 127.0.0.1:5173"
        Write-Host "  dev     run api + web together"
        Write-Host "  test    run the pytest suite"
        Write-Host "  build   production build of frontend"
        Write-Host "  status  show whether ports are responding"
    }
}
