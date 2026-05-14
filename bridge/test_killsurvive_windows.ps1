# Test kill-survive del servicio claude-bridge.
# Requiere elevacion.

if (-not ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Start-Process powershell.exe -Verb RunAs -ArgumentList ('-NoProfile -ExecutionPolicy Bypass -File "{0}"' -f $PSCommandPath)
    exit 0
}

$logPath = "C:\proyectos\agenteIAlocal\bridge\test_killsurvive_result.txt"

function Get-BridgePID {
    $nssm = Get-CimInstance Win32_Process -Filter "Name='nssm.exe'" | Select-Object -First 1
    if (-not $nssm) { return $null }
    return (Get-CimInstance Win32_Process | Where-Object { $_.ParentProcessId -eq $nssm.ProcessId -and $_.Name -eq 'python.exe' } | Select-Object -First 1).ProcessId
}

$p1 = Get-BridgePID
"PID inicial: $p1" | Tee-Object -FilePath $logPath
try {
    Stop-Process -Id $p1 -Force -ErrorAction Stop
    "Kill SIGTERM al PID $p1 OK" | Tee-Object -FilePath $logPath -Append
} catch {
    "Kill FALLO: $($_.Exception.Message)" | Tee-Object -FilePath $logPath -Append
}

Start-Sleep -Seconds 12

$p2 = Get-BridgePID
"PID post-kill (esperado distinto): $p2" | Tee-Object -FilePath $logPath -Append

if ($p2 -and $p2 -ne $p1) {
    "RESUCITO: PID cambio $p1 -> $p2" | Tee-Object -FilePath $logPath -Append
} else {
    "NO RESUCITO" | Tee-Object -FilePath $logPath -Append
}

try {
    $h = Invoke-RestMethod -Uri "http://localhost:8765/health" -TimeoutSec 5
    "Health: $($h | ConvertTo-Json -Compress)" | Tee-Object -FilePath $logPath -Append
} catch {
    "Health FALLO: $($_.Exception.Message)" | Tee-Object -FilePath $logPath -Append
}

"--- fin del test ---" | Tee-Object -FilePath $logPath -Append
Start-Sleep -Seconds 3
