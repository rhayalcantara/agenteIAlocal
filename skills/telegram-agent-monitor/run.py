"""
Diagnóstico automático del agente de Telegram.
Reporta: instancias activas, últimos errores, estado general.
"""
import os
import subprocess
import sys

LOG_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "agente_core", "logs", "agente.log")
LOG_PATH = os.path.normpath(LOG_PATH)
AGENT_SCRIPT = "telegram_agente.py"


def verificar_instancias():
    try:
        result = subprocess.run(
            ["pgrep", "-f", AGENT_SCRIPT],
            capture_output=True, text=True
        )
        pids = [p.strip() for p in result.stdout.strip().splitlines() if p.strip()]
        if not pids:
            return "INSTANCIAS: ninguna activa"
        elif len(pids) == 1:
            return f"INSTANCIAS: 1 activa (PID {pids[0]}) — OK"
        else:
            return f"INSTANCIAS: {len(pids)} activas (PIDs: {', '.join(pids)}) — CONFLICTO DETECTADO"
    except Exception as e:
        return f"INSTANCIAS: error verificando — {e}"


def leer_ultimos_errores(n=20):
    if not os.path.exists(LOG_PATH):
        return "LOG: archivo no encontrado"
    try:
        with open(LOG_PATH, "r", encoding="utf-8", errors="ignore") as f:
            lineas = f.readlines()
        ultimas = lineas[-n:]
        errores = [l.strip() for l in ultimas if "ERROR" in l or "WARNING" in l or "Conflict" in l]
        if not errores:
            return "LOG: sin errores recientes"
        return "LOG (errores recientes):\n" + "\n".join(errores[-10:])
    except Exception as e:
        return f"LOG: error leyendo — {e}"


def ultima_actividad():
    if not os.path.exists(LOG_PATH):
        return "ACTIVIDAD: sin datos"
    try:
        with open(LOG_PATH, "r", encoding="utf-8", errors="ignore") as f:
            lineas = f.readlines()
        for linea in reversed(lineas):
            linea = linea.strip()
            if linea and ("INFO" in linea or "ERROR" in linea):
                return f"ULTIMA ACTIVIDAD: {linea}"
        return "ACTIVIDAD: log vacío"
    except Exception as e:
        return f"ACTIVIDAD: error — {e}"


def verificar_dependencias():
    problemas = []
    try:
        import whisper  # noqa
    except ImportError:
        problemas.append("whisper no instalado (pip install openai-whisper)")
    try:
        from gtts import gTTS  # noqa
    except ImportError:
        problemas.append("gTTS no instalado (pip install gTTS)")
    if problemas:
        return "DEPENDENCIAS FALTANTES:\n" + "\n".join(f"  - {p}" for p in problemas)
    return "DEPENDENCIAS: OK (whisper + gTTS disponibles)"


if __name__ == "__main__":
    print("=" * 50)
    print("  TELEGRAM AGENT MONITOR — DIAGNÓSTICO")
    print("=" * 50)
    print(verificar_instancias())
    print(verificar_dependencias())
    print(ultima_actividad())
    print(leer_ultimos_errores())
    print("=" * 50)
