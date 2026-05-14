# Instala bridge.server como servicio Windows usando NSSM.
# REQUIERE EJECUCION ELEVADA (Run as Administrator).
#
# Si lo ejecutas sin elevacion, te lo relanza pidiendo UAC.

if (-not ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Host "No estas elevado, relanzando con UAC..."
    Start-Process powershell.exe -Verb RunAs -ArgumentList ('-NoProfile -ExecutionPolicy Bypass -File "{0}"' -f $PSCommandPath)
    exit 0
}

$ErrorActionPreference = "Stop"

# === Paths reales ===
$ServiceName  = "claude-bridge"
$NSSM         = "C:\Users\rhay_\AppData\Local\Microsoft\WinGet\Packages\NSSM.NSSM_Microsoft.Winget.Source_8wekyb3d8bbwe\nssm-2.24-101-g897c7ad\win64\nssm.exe"
$PythonBin    = "C:\proyectos\agenteIAlocal\venv\Scripts\python.exe"
$ProjectDir   = "C:\proyectos\agenteIAlocal"
$LogDir       = "C:\proyectos\agenteIAlocal\bridge\logs"
$StdoutLog    = Join-Path $LogDir "bridge-stdout.log"
$StderrLog    = Join-Path $LogDir "bridge-stderr.log"

# Sanity checks
foreach ($p in @($NSSM, $PythonBin, $ProjectDir)) {
    if (-not (Test-Path $p)) { throw "No existe: $p" }
}
New-Item -ItemType Directory -Path $LogDir -Force | Out-Null

# Si el servicio ya existe, lo quitamos antes para reinstalar limpio
$existing = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
if ($existing) {
    Write-Host "Servicio existente detectado, removiendo..."
    if ($existing.Status -eq "Running") { & $NSSM stop $ServiceName confirm }
    & $NSSM remove $ServiceName confirm
    Start-Sleep -Seconds 2
}

# Instalar
Write-Host "Instalando servicio $ServiceName..."
& $NSSM install $ServiceName $PythonBin "-m" "bridge.server"
& $NSSM set $ServiceName AppDirectory $ProjectDir
& $NSSM set $ServiceName DisplayName "Claude Bridge (FastAPI)"
& $NSSM set $ServiceName Description "Mini-bridge HTTP para comms Claude-local <-> Claude-Ranger via Tailscale."
& $NSSM set $ServiceName Start SERVICE_AUTO_START
& $NSSM set $ServiceName AppStdout $StdoutLog
& $NSSM set $ServiceName AppStderr $StderrLog
& $NSSM set $ServiceName AppRotateFiles 1
& $NSSM set $ServiceName AppRotateOnline 1
& $NSSM set $ServiceName AppRotateBytes 1048576
# Reiniciar automatico si crashea (NSSM default ya hace esto, lo dejamos explicito)
& $NSSM set $ServiceName AppThrottle 5000
& $NSSM set $ServiceName AppExit Default Restart
& $NSSM set $ServiceName AppRestartDelay 3000

# Arrancar
Write-Host "Arrancando servicio..."
& $NSSM start $ServiceName

Start-Sleep -Seconds 3

# Verificar
$svc = Get-Service -Name $ServiceName
Write-Host ""
Write-Host "=== Estado ==="
Write-Host ("Servicio: {0} -> {1}" -f $svc.Name, $svc.Status)

try {
    $h = Invoke-RestMethod -Uri "http://localhost:8765/health" -TimeoutSec 5
    Write-Host ("Health: {0}" -f ($h | ConvertTo-Json -Compress))
} catch {
    Write-Host ("Health FALLO: {0}" -f $_.Exception.Message)
}

Write-Host ""
Write-Host "Comandos de operacion:"
Write-Host ("  Arrancar: & '{0}' start {1}" -f $NSSM, $ServiceName)
Write-Host ("  Parar:    & '{0}' stop {1}" -f $NSSM, $ServiceName)
Write-Host ("  Estado:   Get-Service {0}" -f $ServiceName)
Write-Host ("  Logs:     {0}" -f $LogDir)
Write-Host ("  Remover:  & '{0}' remove {1} confirm" -f $NSSM, $ServiceName)
Write-Host ""
Read-Host "Presiona Enter para cerrar"
