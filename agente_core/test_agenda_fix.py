"""Test end-to-end de la inferencia de 'operacion' contra agenda_tool real.

Reproduce el bloque elif fn_name == 'agenda' de agent.py y lo corre
contra agenda_tool.ejecutar con args mal formados (como los manda el LLM).
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agenda_tool import ejecutar as agenda_ejecutar

ARGS_VALIDOS_POR_OP = {
    "agregar": {"nombre", "tipo", "prompt", "chat_id", "descripcion", "hora",
                "dias_semana", "intervalo_minutos", "hora_inicio", "hora_fin"},
    "listar": {"filtro"},
    "ver": {"id"},
    "activar": {"id"},
    "desactivar": {"id"},
    "eliminar": {"id"},
    "historial": {"id", "ultimas"},
}


def llamar_agenda(args_llm: dict) -> tuple[str, dict, str]:
    """Reproduce el bloque elif del agent.py. Retorna (op_inferida, args_filtrados, resultado)."""
    args = dict(args_llm)
    operacion = args.pop("operacion", None)
    if not operacion:
        if args.get("nombre") and args.get("tipo") and args.get("prompt"):
            operacion = "agregar"
        elif args.get("ultimas") is not None:
            operacion = "historial"
        elif args.get("listar") or args.get("filtro") is not None:
            operacion = "listar"
        elif args.get("id") is not None and not args.get("nombre"):
            operacion = "ver"
        else:
            operacion = "listar"
    args.pop("listar", None)
    permitidos = ARGS_VALIDOS_POR_OP.get(operacion, set())
    args = {k: v for k, v in args.items() if k in permitidos}
    try:
        resultado = agenda_ejecutar(operacion, **args)
    except Exception as e:
        resultado = f"EXCEPCION: {type(e).__name__}: {e}"
    return operacion, args, resultado


CASOS = [
    # (descripcion, args como los manda el LLM, op esperada, debe_no_crashear)
    ("LLM manda solo {listar:true}", {"listar": True}, "listar", True),
    ("LLM manda solo {filtro:activas}", {"filtro": "activas"}, "listar", True),
    ("LLM pide ver id solo", {"id": 1}, "ver", True),
    ("LLM pide historial", {"id": 1, "ultimas": 3}, "historial", True),
    ("LLM correcto: listar explicito", {"operacion": "listar"}, "listar", True),
    ("LLM correcto: listar con filtro", {"operacion": "listar", "filtro": "activas"}, "listar", True),
    ("LLM pide listar con args sobrantes", {"operacion": "listar", "id": 999, "nombre": "x"}, "listar", True),
    ("LLM no manda nada", {}, "listar", True),
]

print("="*80)
print("TEST inferencia agenda + agenda_tool real")
print("="*80)
ok = 0
fallos = []
for desc, args_in, op_esperada, debe_no_crashear in CASOS:
    op, args_fil, res = llamar_agenda(args_in)
    crashea = res.startswith("EXCEPCION:")
    pasa = (op == op_esperada) and (not crashea if debe_no_crashear else True)
    estado = "OK" if pasa else "FAIL"
    if pasa:
        ok += 1
    else:
        fallos.append((desc, op, op_esperada, res[:200]))
    print(f"[{estado}] {desc}")
    print(f"   args_in={args_in} -> op={op}, args_filtrados={args_fil}")
    res_corto = res[:140].replace("\n", " | ")
    print(f"   resultado: {res_corto}")
    print()

print("="*80)
print(f"RESULTADO: {ok}/{len(CASOS)} pasaron")
if fallos:
    print("\nFALLOS:")
    for f in fallos:
        print(f"  - {f}")
print("="*80)
