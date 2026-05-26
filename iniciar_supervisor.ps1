# iniciar_supervisor.ps1 - Levanta el supervisor en background.
#
# El supervisor a su vez arranca: telegram_agente.py + job_manager.
# Pensado para correr en logon de Windows via schtasks (RangerSupervisor).
#
# Uso:
#   .\iniciar_supervisor.ps1            : arranca si no esta corriendo
#   .\iniciar_supervisor.ps1 -Force     : mata el que haya y reinicia
#   .\iniciar_supervisor.ps1 -Status    : reporta estado
#   .\iniciar_supervisor.ps1 -Stop      : detiene (mata supervisor + agente)

param(
    [switch]$Force,
    [switch]$Status,
    [switch]$Stop
)

$ErrorActionPreference = "Stop"
$Root   = $PSScriptRoot
$Python = Join-Path $Root "venv\Scripts\python.exe"
$LogDir = Join-Path $Root "logs"
$Log    = Join-Path $LogDir "supervisor.stdout.log"
$LogErr = Join-Path $LogDir "supervisor.stderr.log"

function Get-SupervisorProcess {
    Get-CimInstance Win32_Process -Filter "Name='python.exe'" -ErrorAction SilentlyContinue |
        Where-Object { $_.CommandLine -and $_.CommandLine -like "*supervisor_bot*" }
}

function Get-AgentProcess {
    Get-CimInstance Win32_Process -Filter "Name='python.exe'" -ErrorAction SilentlyContinue |
        Where-Object { $_.CommandLine -and $_.CommandLine -like "*telegram_agente.py*" }
}

if ($Status) {
    $sup = Get-SupervisorProcess
    if ($sup) {
        Write-Host "supervisor corriendo:"
        $sup | Select-Object ProcessId,@{n='Started';e={[datetime]$_.CreationDate}} | Format-List
    } else {
        Write-Host "supervisor NO corriendo"
    }
    $ag = Get-AgentProcess
    if ($ag) {
        Write-Host "agente corriendo:"
        $ag | Select-Object ProcessId,@{n='Started';e={[datetime]$_.CreationDate}} | Format-List
    } else {
        Write-Host "agente NO corriendo"
    }
    exit 0
}

if ($Stop -or $Force) {
    # Mata supervisor primero (sino podria relanzar al agente justo despues)
    $sup = Get-SupervisorProcess
    foreach ($p in $sup) {
        Write-Host "deteniendo supervisor PID $($p.ProcessId)..."
        try { Stop-Process -Id $p.ProcessId -Force } catch {}
    }
    Start-Sleep -Milliseconds 500
    # Despues el agente
    $ag = Get-AgentProcess
    foreach ($p in $ag) {
        Write-Host "deteniendo agente PID $($p.ProcessId)..."
        try { Stop-Process -Id $p.ProcessId -Force } catch {}
    }
    Start-Sleep -Seconds 1
    if ($Stop) { exit 0 }
}

# Idempotencia: si ya corre, no duplicar
if (-not $Force) {
    $sup = Get-SupervisorProcess
    if ($sup) {
        Write-Host "supervisor ya corre (PID $($sup.ProcessId)). Usar -Force para reiniciar."
        exit 0
    }
}

if (-not (Test-Path $Python)) {
    Write-Error "venv no encontrado en $Python"
    exit 1
}

if (-not (Test-Path $LogDir)) { New-Item -ItemType Directory -Force -Path $LogDir | Out-Null }

# Setear env para no perder encoding ni buffering
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUNBUFFERED = "1"

Write-Host "arrancando supervisor (logs: $Log)..."
$proc = Start-Process -FilePath $Python `
    -ArgumentList "-u","supervisor/supervisor_bot.py" `
    -WorkingDirectory $Root `
    -RedirectStandardOutput $Log -RedirectStandardError $LogErr `
    -WindowStyle Hidden -PassThru

Start-Sleep -Seconds 8

# Verificacion: supervisor + agente vivos
$sup = Get-SupervisorProcess
$ag  = Get-AgentProcess
if ($sup -and $ag) {
    Write-Host "OK supervisor PID $($sup.ProcessId) + agente PID $($ag.ProcessId)"
    exit 0
} elseif ($sup) {
    Write-Warning "supervisor arranco (PID $($sup.ProcessId)) pero el agente todavia no esta vivo. Revisar $LogErr"
    exit 0
} else {
    Write-Error "supervisor no quedo vivo. Revisar $LogErr"
    Get-Content $LogErr -Tail 15 -ErrorAction SilentlyContinue
    exit 2
}
