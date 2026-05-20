import time
import sys
import datetime
import json
import os
from pathlib import Path

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
    print(f"[{hora_inicio.strftime('%H:%M')}] Acorde a las: {hora_fin.strftime('%H:%M')}")
    print(f"[{hora_inicio.strftime('%H:%M')}] Acción: {accion}")
    print("Esperando...")
    
    # Aquí va la lógica real de espera
    # time.sleep(tiempo * 60)
    
    # Por ahora no esperamos en la terminal, solo configuramos
    print(f"\nALERTA: ¡Es hora de {tipo}!")
    print("-" * 40)
    if "iluminar" in accion:
        print("💡 ACCIÓN: Activando iluminación")
        # Aquí activarías la skill de iluminacion:
        # ejecutar_skill("home-assistant", "encender_luz", room="todas")
    if "notificacion" in accion:
        print("🔔 ACCIÓN: Enviando notificación")
    if "sonido" in accion:
        print("🔊 ACCIÓN: Reproduciendo sonido")
    
    print("\nAlarma completada.")

if __name__ == "__main__":
    main()