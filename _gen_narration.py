"""Genera narración Spanish con edge-tts (un solo MP3 continuo de ~40s)."""
import asyncio, sys
from pathlib import Path
import edge_tts

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# Voz neutra latam con buena entonación
VOICE = "es-MX-JorgeNeural"  # masculino, claro, profesional
# Alternativas: es-DO-EmilioNeural (dominicano), es-US-AlonsoNeural

# Script con pausas SSML (pero edge-tts soporta solo subset). Usamos texto plano con puntuación.
SCRIPT = (
    "OperacionesRanger. "
    "Sistema de gestión de turnos para guardianes de seguridad. "
    "Acceso seguro con tokens JWT y contraseñas hasheadas. "
    "Tres roles: administrador, supervisor, consulta. "
    "Dashboard en vivo: turnos del mes, guardianes activos, horas trabajadas. "
    "Cálculo automático de turnos. "
    "El sistema separa horas normales, extras, diurnas y nocturnas. Cero cálculo manual. "
    "Feriados nacionales y por decreto, sincronizados. Recargo aplicado solo. "
    "Integración con nómina: un clic genera el reporte listo para procesar. "
    "El sistema está completo. ¿Lo activamos?"
)


async def main():
    out = Path("narration.mp3")
    com = edge_tts.Communicate(SCRIPT, VOICE, rate="+15%")
    await com.save(str(out))
    print(f"Generated: {out} -> {out.stat().st_size//1024}KB")


if __name__ == "__main__":
    asyncio.run(main())
