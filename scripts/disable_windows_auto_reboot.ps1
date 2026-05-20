# Bloquea auto-reboot por Windows Update mientras hay sesión iniciada.
# Mantiene actualizaciones automáticas, pero NO reinicia la PC sin tu permiso.
#
# Uso: clic derecho → "Ejecutar con PowerShell como administrador"
#       o desde PowerShell admin:
#           Set-ExecutionPolicy -Scope Process Bypass; .\disable_windows_auto_reboot.ps1
#
# Para revertir: ejecuta el script con -Revert.
#
# Cambios aplicados:
#   1. HKLM\...\WindowsUpdate\AU\NoAutoRebootWithLoggedOnUsers = 1
#      → Mientras haya un usuario logueado, no reinicia.
#   2. Active Hours 00:00-23:00 (rango máximo, 23h)
#      → Windows considera todas las horas "activas".
#   3. Deshabilita la tarea programada "Reboot" en Scheduler.

param([switch]$Revert)

if (-not ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Host "Este script requiere privilegios de administrador." -ForegroundColor Red
    Write-Host "Re-ejecuta PowerShell como administrador y vuelve a correr el script." -ForegroundColor Yellow
    exit 1
}

$auKey = "HKLM:\SOFTWARE\Policies\Microsoft\Windows\WindowsUpdate\AU"
$uxKey = "HKLM:\SOFTWARE\Microsoft\WindowsUpdate\UX\Settings"

if ($Revert) {
    Write-Host "Revirtiendo cambios..." -ForegroundColor Cyan
    if (Test-Path $auKey) {
        Remove-ItemProperty -Path $auKey -Name "NoAutoRebootWithLoggedOnUsers" -ErrorAction SilentlyContinue
    }
    if (Test-Path $uxKey) {
        Set-ItemProperty -Path $uxKey -Name "IsActiveHoursEnabled" -Value 0 -Type DWord -ErrorAction SilentlyContinue
    }
    try {
        Get-ScheduledTask -TaskPath "\Microsoft\Windows\UpdateOrchestrator\" -TaskName "Reboot" -ErrorAction Stop | Enable-ScheduledTask | Out-Null
        Write-Host "  Tarea Reboot rehabilitada." -ForegroundColor Green
    } catch {}
    Write-Host "Listo. Comportamiento original restaurado." -ForegroundColor Green
    exit 0
}

Write-Host "Aplicando políticas para evitar reinicio automático..." -ForegroundColor Cyan

if (-not (Test-Path $auKey)) {
    New-Item -Path $auKey -Force | Out-Null
}
New-ItemProperty -Path $auKey -Name "NoAutoRebootWithLoggedOnUsers" -Value 1 -PropertyType DWord -Force | Out-Null
Write-Host "  [OK] NoAutoRebootWithLoggedOnUsers = 1" -ForegroundColor Green

if (-not (Test-Path $uxKey)) {
    New-Item -Path $uxKey -Force | Out-Null
}
New-ItemProperty -Path $uxKey -Name "ActiveHoursStart" -Value 0 -PropertyType DWord -Force | Out-Null
New-ItemProperty -Path $uxKey -Name "ActiveHoursEnd"   -Value 23 -PropertyType DWord -Force | Out-Null
New-ItemProperty -Path $uxKey -Name "IsActiveHoursEnabled" -Value 1 -PropertyType DWord -Force | Out-Null
Write-Host "  [OK] Active Hours 00:00-23:00 habilitado" -ForegroundColor Green

try {
    $task = Get-ScheduledTask -TaskPath "\Microsoft\Windows\UpdateOrchestrator\" -TaskName "Reboot" -ErrorAction Stop
    if ($task.State -ne 'Disabled') {
        $task | Disable-ScheduledTask | Out-Null
        Write-Host "  [OK] Tarea UpdateOrchestrator\Reboot deshabilitada" -ForegroundColor Green
    } else {
        Write-Host "  [skip] Tarea UpdateOrchestrator\Reboot ya estaba deshabilitada" -ForegroundColor DarkGray
    }
} catch {
    Write-Host "  [warn] No se pudo deshabilitar UpdateOrchestrator\Reboot (puede no existir en tu build)" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Listo. Windows Update SEGUIRA descargando e instalando, pero no reiniciara solo." -ForegroundColor Green
Write-Host "Cuando quieras reiniciar manualmente: Win+X -> Apagar o cerrar sesion -> Actualizar y reiniciar." -ForegroundColor Cyan
Write-Host ""
Write-Host "Para revertir: .\disable_windows_auto_reboot.ps1 -Revert" -ForegroundColor DarkGray
