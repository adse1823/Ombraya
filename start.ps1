# BallPit quick-start (PowerShell)
# Run from the BallPit/ directory

Write-Host "Starting BallPit CyberRange..." -ForegroundColor Cyan

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host ".env created - add your ANTHROPIC_API_KEY then re-run." -ForegroundColor Yellow
    exit 1
}

$root     = $PSScriptRoot
$uvicorn  = Join-Path $root "venv\Scripts\uvicorn.exe"

Write-Host "Starting backend on :8000 (venv)..." -ForegroundColor Green
Start-Process -FilePath $uvicorn `
    -ArgumentList "backend.main:app", "--reload", "--port", "8000" `
    -WorkingDirectory $root `
    -PassThru | Out-Null

Write-Host "Starting frontend on :5173..." -ForegroundColor Green
Set-Location (Join-Path $root "frontend")
npm install
npm run dev
