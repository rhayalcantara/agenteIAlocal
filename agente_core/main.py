"""Punto de entrada para el agente en modo consola."""
import sys
import os

# Asegurar que agente_core/ esté en el path
_dir = os.path.dirname(os.path.abspath(__file__))
if _dir not in sys.path:
    sys.path.insert(0, _dir)

from provider_config import obtener_configuracion
from agent import Agent
from logger import get_logger

logger = get_logger("main")


def main():
    print("=" * 60)
    print("  Agente IA — Modo Consola")
    print("=" * 60)

    try:
        config = obtener_configuracion()
    except KeyboardInterrupt:
        print("\nCancelado.")
        return

    agente = Agent(
        model=config["model"],
        api_key=config["api_key"],
        base_url=config.get("base_url"),
        provider=config.get("provider", "openai"),
    )

    print(f"\n[Modelo: {config['model']} | Proveedor: {config.get('provider')}]")
    print("Escribe 'salir' para terminar. 'limpiar' para borrar historial.\n")

    while True:
        try:
            user_input = input("Tú: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nHasta luego.")
            break

        if not user_input:
            continue

        if user_input.lower() in ("salir", "exit", "quit"):
            print("Hasta luego.")
            break

        if user_input.lower() == "limpiar":
            agente.limpiar_historial()
            print("[Historial limpiado]\n")
            continue

        try:
            respuesta = agente.chat(user_input)
            print(f"\nAgente: {respuesta}\n")
        except Exception as e:
            logger.error(f"Error en chat: {e}", exc_info=True)
            print(f"[Error]: {e}\n")


if __name__ == "__main__":
    main()
