# iniciar_worker_hub.ps1 - Levanta worker_hub en background.
#
# Uso:
#   .\iniciar_worker_hub.ps1            : arranca si no esta corriendo
#   .\iniciar_worker_hub.ps1 -Force     : mata el que haya y reinicia
#   .\iniciar_worker_hub.ps1 -Status    : reporta estado
#   .\iniciar_worker_hub.ps1 -Stop      : detiene
#
# Escucha en 0.0.0.0:8500 (visible al tailnet). Auth via WORKER_HUB_API_KEY del .env.
# Logs: worker_hub/data/uvicorn.log

param(
    [switch]$Force,
    [switch]$Status,
    [switch]$Stop
)

$ErrorActionPreference = "Stop"
$Root   = $PSScriptRoot
$Python = Join-Path $Root "venv\Scripts\python.exe"
$Log    = Join-Path $Root "worker_hub\data\uvicorn.log"
$Port   = 8500

function Get-HubProcess {
    Get-CimInstance Win32_Process -Filter "Name='python.exe'" -ErrorAction SilentlyContinue |
        Where-Object { $_.CommandLine -and $_.CommandLine -like "*worker_hub.main:app*" }
}

if ($Status) {
    $p = Get-HubProcess
    if ($p) {
        Write-Host "worker_hub corriendo: PID $($p.ProcessId)"
        Write-Host "  cmdline: $($p.CommandLine)"
    } else {
        Write-Host "worker_hub NO corriendo"
    }
    try {
        $r = Invoke-WebRequest -Uri "http://127.0.0.1:$Port/health" -UseBasicParsing -TimeoutSec 3
        Write-Host "health: $($r.StatusCode) $($r.Content)"
    } catch {
        Write-Host "health: no responde"
    }
    exit 0
}

if ($Stop -or $Force) {
    $p = Get-HubProcess
    if ($p) {
        Write-Host "deteniendo PID $($p.ProcessId)..."
        Stop-Process -Id $p.ProcessId -Force
        Start-Sleep -Milliseconds 500
    } elseif ($Stop) {
        Write-Host "worker_hub no estaba corriendo"
    }
    if ($Stop) { exit 0 }
}

if (-not $Force) {
    $p = Get-HubProcess
    if ($p) {
        Write-Host "worker_hub ya corre (PID $($p.ProcessId)). Usar -Force para reiniciar."
        exit 0
    }
}

if (-not (Test-Path $Python)) {
    Write-Error "venv no encontrado en $Python"
    exit 1
}
$env_path = Join-Path $Root ".env"
if (-not (Select-String -Path $env_path -Pattern "^WORKER_HUB_API_KEY=.+" -Quiet)) {
    Write-Warning "WORKER_HUB_API_KEY vacio en .env -- hub aceptara peticiones SIN auth."
}

$logDir = Split-Path $Log -Parent
if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Force -Path $logDir | Out-Null }

$args = @(
    "-m", "uvicorn",
    "worker_hub.main:app",
    "--host", "0.0.0.0",
    "--port", "$Port"
)

Write-Host "arrancando worker_hub en :$Port (logs: $Log)..."
$proc = Start-Process -FilePath $Python -ArgumentList $args `
    -WorkingDirectory $Root `
    -RedirectStandardOutput $Log -RedirectStandardError "$Log.err" `
    -WindowStyle Hidden -PassThru

Start-Sleep -Seconds 3   # Da chance al probe inicial de workers

try {
    $r = Invoke-WebRequest -Uri "http://127.0.0.1:$Port/health" -UseBasicParsing -TimeoutSec 10
    if ($r.StatusCode -eq 200) {
        Write-Host "OK worker_hub PID $($proc.Id) - $($r.Content)"
        $ts_ip = & "C:\Program Files\Tailscale\tailscale.exe" ip -4 2>$null | Select-Object -First 1
        if ($ts_ip) {
            Write-Host "URL tailnet: http://${ts_ip}:$Port/v1/chat/completions"
        }
    } else {
        Write-Warning "arranco pero /health respondio $($r.StatusCode)"
    }
} catch {
    Write-Error "worker_hub no respondio en :$Port -- revisar $Log"
    exit 2
}
