# Ideas de Backend Tools — Patron: Tool (logica) + Agente (frontend)

Concepto: cada herramienta es un backend independiente con datos en JSON + fotos.
El agente actua como frontend conversacional. Si el usuario necesita reportes
visuales, el agente genera HTML/CSS/JS o PDF y lo envia por Telegram.

## Estado

| # | Tool | Estado | Descripcion |
|---|------|--------|-------------|
| 1 | lista_compras | HECHO | CRUD de items de supermercado con fotos, estadisticas de frecuencia |
| 2 | distribucion_casa | HECHO | Mapa de areas de la casa (sala, cocina, etc.) con foto y nombre |
| 3 | ubicaciones | HECHO | Objetos + ubicacion (area de la casa) + foto + descripcion del lugar exacto |
| 4 | recetas | HECHO | Ingredientes + pasos + foto. Cruce con lista_compras para sugerencias |
| 5 | gastos | HECHO | Monto + categoria + fecha. Resumenes, presupuestos, comparacion mensual |
| 6 | contactos_servicios | HECHO | Plomero, electricista, etc. + tel + notas + visitas + calificacion |
| 7 | mantenimiento | HECHO | Objeto + frecuencia + area. Pendientes, historial, alertas |
| 8 | documentos | HECHO | Tipo + ubicacion fisica + foto + alertas de vencimiento |
| 9 | presencia | HECHO | Deteccion personas por WiFi (RuView + ESP32). Vitales, caidas, actividad |

## Patron comun

Cada tool sigue la misma arquitectura:

```
agente_core/
  {nombre}_tool.py          — logica con ejecutar(operacion, **kwargs)
  data/
    {nombre}.json           — datos persistentes
    imagenes_{nombre}/      — fotos asociadas (opcional)
```

Registro en agent.py:
- Definicion del schema en setup_tools()
- Dispatch en _ejecutar_tool() con import lazy

## Flujo de dependencias

```
distribucion_casa (areas)
       |
       v
  ubicaciones (objetos en areas)
       |
       v
  mantenimiento (objetos con calendario)

lista_compras
       |
       v
    recetas (cruza ingredientes con lista)
       |
       v
    gastos (precio de lo comprado)
```

## Notas

- Las fotos se guardan localmente, no salen a internet
- Los LLM locales (LM Studio) procesan las imagenes sin enviar datos fuera
- El agente puede generar reportes HTML/PDF bajo demanda y enviarlos por Telegram
- Cada tool es independiente pero pueden cruzar datos entre si
