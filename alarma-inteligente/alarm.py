import datetime
import sys
import time
import subprocess
import os

def main():
    args = sys.argv[1:]
    
    tiempo = 10
    tipo = "despertar"
    accion = "iluminar"
    
    i = 0
    while i < len(args):
        if args[i] == "--tiempo" and i+1 < len(args):
            tiempo = int(args[i+1])
            i += 2
        elif args[i] == "--tipo" and i+1 < len(args):
            tipo = args[i+1]
            i += 2
        elif args[i] == "--accion" and i+1 < len(args):
            accion = args[i+1]
            i += 2
        else:
            i += 1
    
    hora_inicio = datetime.datetime.now()
    hora_fin = hora_inicio + datetime.timedelta(minutes=tiempo)
    
    print(f"[{hora_inicio.strftime('%H:%M')}] Alarma configurada: {tiempo} min - {tipo}")
    print(f"[{hora_inicio.strftime('%H:%M')}] Suena a las: {hora_fin.strftime('%H:%M')}")
    print(f"[{hora_inicio.strftime('%H:%M')}] Acción: {accion}")
    print("Esperando...")
    
    # Esperar los minutos indicados
    time.sleep(tiempo * 60)
    
    # Hora de la alarma
    print("\n" + "="*50)
    print("  ⏰ ¡ALERTA! ¡Es hora de {}!".format(tipo.upper()))
    print("="*50)
    
    if "iluminar" in accion:
        print("\n💡 ACCIÓN: Activando iluminación...")
        # Aquí se integraría con Home Assistant u otra API de domótica
        print("   (La integración real con Home Assistant se haría aquí)")
        
    if "notificacion" in accion:
        print("🔔 Notificación enviada")
    if "sonido" in accion:
        print("🔊 Sonido reproduciéndose")
    
    # Mostrar mensaje en pantalla (Windows)
    script_ps1 = f'''
Add-Type -AssemblyName System.Windows.Forms
[System.Windows.Forms.MessageBox]::Show('¡Es hora de {tipo}!','Alarma',0,64)
    '''
    with open("_alarma_msg.ps1", "w") as f:
        f.write(script_ps1)
    subprocess.Popen(["powershell", "-ExecutionPolicy", "Bypass", "-File", "_alarma_msg.ps1"], 
                     creationflags=subprocess.CREATE_NEW_CONSOLE)
    print("\n(Noificación mostrada en pantalla)")
    
    # Limpiar archivos temporales
    if os.path.exists("_alarma_msg.ps1"):
        os.remove("_alarma_msg.ps1")

if __name__ == "__main__":
    main()