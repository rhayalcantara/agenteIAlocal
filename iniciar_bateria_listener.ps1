# iniciar_bateria_listener.ps1 - Lanza bateria_event_listener.py en background.
#
# Reemplaza el schtask `RangerMonitorBateria` (cada 5 min) por listener
# event-driven via WMI Win32_Battery. Idempotente.
#
# Uso:
#   .\iniciar_bateria_listener.ps1            : arranca si no esta
#   .\iniciar_bateria_listener.ps1 -Status    : reporta estado
#   .\iniciar_bateria_listener.ps1 -Stop      : detiene
#   .\iniciar_bateria_listener.ps1 -Force     : reinicia

param(
    [switch]$Force,
    [switch]$Status,
    [switch]$Stop
)

$ErrorActionPreference = "Stop"
$Root   = $PSScriptRoot
$Python = Join-Path $Root "venv\Scripts\python.exe"
$LogDir = Join-Path $Root "logs"
$Log    = Join-Path $LogDir "bateria_listener.stdout.log"
$LogErr = Join-Path $LogDir "bateria_listener.stderr.log"

function Get-ListenerProcess {
    Get-CimInstance Win32_Process -Filter "Name='python.exe'" -ErrorAction SilentlyContinue |
        Where-Object { $_.CommandLine -and $_.CommandLine -like "*bateria_event_listener.py*" }
}

if ($Status) {
    $p = Get-ListenerProcess
    if ($p) {
        $p | Select-Object ProcessId,@{n='Started';e={[datetime]$_.CreationDate}} | Format-List
        Write-Host "=== ultima linea del log ==="
        Get-Content $Log -Tail 3 -ErrorAction SilentlyContinue
    } else {
        Write-Host "listener NO corriendo"
    }
    exit 0
}

if ($Stop -or $Force) {
    $p = Get-ListenerProcess
    foreach ($x in $p) {
        Write-Host "deteniendo listener PID $($x.ProcessId)..."
        try { Stop-Process -Id $x.ProcessId -Force } catch {}
    }
    Start-Sleep -Seconds 1
    if ($Stop) { exit 0 }
}

if (-not $Force) {
    $p = Get-ListenerProcess
    if ($p) {
        Write-Host "listener ya corre (PID $($p.ProcessId)). Usar -Force para reiniciar."
        exit 0
    }
}

if (-not (Test-Path $Python)) {
    Write-Error "venv no encontrado en $Python"
    exit 1
}
if (-not (Test-Path $LogDir)) { New-Item -ItemType Directory -Force -Path $LogDir | Out-Null }

$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUNBUFFERED = "1"

Write-Host "arrancando bateria_event_listener (logs: $Log)..."
$proc = Start-Process -FilePath $Python `
    -ArgumentList "-u","bateria_event_listener.py" `
    -WorkingDirectory $Root `
    -RedirectStandardOutput $Log -RedirectStandardError $LogErr `
    -WindowStyle Hidden -PassThru

Start-Sleep -Seconds 4

$p = Get-ListenerProcess
if ($p) {
    Write-Host "OK listener PID $($p.ProcessId)"
    Write-Host "=== primera lectura ==="
    Get-Content $Log -Tail 3 -ErrorAction SilentlyContinue
} else {
    Write-Error "listener no quedo vivo. Revisar $LogErr"
    Get-Content $LogErr -Tail 15 -ErrorAction SilentlyContinue
    exit 2
}
