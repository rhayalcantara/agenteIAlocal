# iniciar_gateway.ps1 - Levanta anthropic_gateway en background.
#
# Uso:
#   .\iniciar_gateway.ps1            : arranca si no esta corriendo
#   .\iniciar_gateway.ps1 -Force     : mata el que haya y vuelve a arrancar
#   .\iniciar_gateway.ps1 -Status    : solo reporta estado
#   .\iniciar_gateway.ps1 -Stop      : detiene
#
# Escucha en 0.0.0.0:8400 (visible al tailnet). Auth via ANTHROPIC_GATEWAY_API_KEY del .env.
# Logs: anthropic_gateway/data/uvicorn.log

param(
    [switch]$Force,
    [switch]$Status,
    [switch]$Stop
)

$ErrorActionPreference = "Stop"
$Root   = $PSScriptRoot
$Python = Join-Path $Root "venv\Scripts\python.exe"
$Log    = Join-Path $Root "anthropic_gateway\data\uvicorn.log"
$Port   = 8400

function Get-GatewayProcess {
    Get-CimInstance Win32_Process -Filter "Name='python.exe'" -ErrorAction SilentlyContinue |
        Where-Object { $_.CommandLine -and $_.CommandLine -like "*anthropic_gateway.main:app*" }
}

if ($Status) {
    $p = Get-GatewayProcess
    if ($p) {
        Write-Host "gateway corriendo: PID $($p.ProcessId)"
        Write-Host "  cmdline: $($p.CommandLine)"
    } else {
        Write-Host "gateway NO corriendo"
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
    $p = Get-GatewayProcess
    if ($p) {
        Write-Host "deteniendo PID $($p.ProcessId)..."
        Stop-Process -Id $p.ProcessId -Force
        Start-Sleep -Milliseconds 500
    } elseif ($Stop) {
        Write-Host "gateway no estaba corriendo"
    }
    if ($Stop) { exit 0 }
}

if (-not $Force) {
    $p = Get-GatewayProcess
    if ($p) {
        Write-Host "gateway ya esta corriendo (PID $($p.ProcessId)). Usar -Force para reiniciar."
        exit 0
    }
}

if (-not (Test-Path $Python)) {
    Write-Error "venv no encontrado en $Python"
    exit 1
}
$env_path = Join-Path $Root ".env"
if (-not (Select-String -Path $env_path -Pattern "^ANTHROPIC_GATEWAY_API_KEY=.+" -Quiet)) {
    Write-Warning "ANTHROPIC_GATEWAY_API_KEY vacio en .env -- gateway aceptara peticiones SIN auth."
}

$logDir = Split-Path $Log -Parent
if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Force -Path $logDir | Out-Null }

$args = @(
    "-m", "uvicorn",
    "anthropic_gateway.main:app",
    "--host", "0.0.0.0",
    "--port", "$Port"
)

Write-Host "arrancando gateway en :$Port (logs: $Log)..."
$proc = Start-Process -FilePath $Python -ArgumentList $args `
    -WorkingDirectory $Root `
    -RedirectStandardOutput $Log -RedirectStandardError "$Log.err" `
    -WindowStyle Hidden -PassThru

Start-Sleep -Seconds 2

try {
    $r = Invoke-WebRequest -Uri "http://127.0.0.1:$Port/health" -UseBasicParsing -TimeoutSec 5
    if ($r.StatusCode -eq 200) {
        Write-Host "OK gateway PID $($proc.Id) - /health $($r.Content)"
        $ts_ip = & "C:\Program Files\Tailscale\tailscale.exe" ip -4 2>$null | Select-Object -First 1
        if ($ts_ip) {
            Write-Host "URL tailnet: http://${ts_ip}:$Port/v1/messages"
        }
    } else {
        Write-Warning "arranco pero /health respondio $($r.StatusCode)"
    }
} catch {
    Write-Error "gateway no respondio en :$Port -- revisar $Log"
    exit 2
}
