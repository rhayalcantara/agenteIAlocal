<#
.SYNOPSIS
  Registra (o re-registra) una Scheduled Task de Windows que ejecuta
  scripts\archive_whatsapp_log.js todos los dias a las 23:55 hora local.

.DESCRIPTION
  - Nombre de la tarea: ClaudeWhatsAppArchive
  - Idempotente: si ya existe, la elimina y la vuelve a crear.
  - Puede requerir permisos de administrador. Si falla, abrir PowerShell
    elevado (Run as Administrator) y volver a ejecutar.

.NOTES
  Ejecutar manualmente:
    powershell -ExecutionPolicy Bypass -File scripts\register_whatsapp_archive_task.ps1
#>

[CmdletBinding()]
param(
    [string]$TaskName = 'ClaudeWhatsAppArchive',
    [string]$TimeOfDay = '23:55'
)

$ErrorActionPreference = 'Stop'

# Resolver rutas absolutas
$ScriptDir   = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectDir  = (Resolve-Path (Join-Path $ScriptDir '..')).Path
$ArchiveJs   = Join-Path $ProjectDir 'scripts\archive_whatsapp_log.js'

if (-not (Test-Path $ArchiveJs)) {
    Write-Error "No se encontro $ArchiveJs"
    exit 1
}

# Detectar node.exe en PATH
$NodeCmd = Get-Command node.exe -ErrorAction SilentlyContinue
if (-not $NodeCmd) {
    Write-Error "node.exe no esta en PATH. Instala Node.js o ajusta PATH antes de re-ejecutar."
    exit 1
}
$NodePath = $NodeCmd.Source

Write-Host "Proyecto:  $ProjectDir"
Write-Host "Script:    $ArchiveJs"
Write-Host "Node:      $NodePath"
Write-Host "Tarea:     $TaskName"
Write-Host "Hora:      $TimeOfDay (diaria)"
Write-Host ""

# Borrar si existe (idempotencia)
$existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($existing) {
    Write-Host "Tarea existente encontrada, eliminando..."
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
}

# Crear accion
$ArgString = '"' + $ArchiveJs + '"'
$Action = New-ScheduledTaskAction -Execute $NodePath -Argument $ArgString -WorkingDirectory $ProjectDir

# Trigger diario
$Trigger = New-ScheduledTaskTrigger -Daily -At $TimeOfDay

# Settings
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Minutes 10)

# Principal: usuario actual, permisos limitados
$Principal = New-ScheduledTaskPrincipal -UserId ($env:USERDOMAIN + '\' + $env:USERNAME) -LogonType Interactive -RunLevel Limited

$Task = New-ScheduledTask -Action $Action -Trigger $Trigger -Settings $Settings -Principal $Principal -Description 'Snapshot diario gzip de whatsapp_monitor.log y whatsapp_enviados.log a whatsapp_archive/YYYY-MM-DD/'

try {
    Register-ScheduledTask -TaskName $TaskName -InputObject $Task | Out-Null
    Write-Host ""
    Write-Host "OK - Tarea '$TaskName' registrada para correr diariamente a las $TimeOfDay."
    Write-Host "Verificar con:           Get-ScheduledTask -TaskName $TaskName"
    Write-Host "Forzar corrida manual:   Start-ScheduledTask -TaskName $TaskName"
}
catch {
    $errMsg  = $_.Exception.Message
    $selfPath = $MyInvocation.MyCommand.Path
    Write-Warning "No se pudo registrar la tarea: $errMsg"
    Write-Warning "Reintenta abriendo PowerShell como Administrador y ejecutando:"
    Write-Warning ("  powershell -ExecutionPolicy Bypass -File '" + $selfPath + "'")
    exit 1
}
