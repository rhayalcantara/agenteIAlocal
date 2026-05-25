# Agenda de noticias

Dos acciones en `agente_core/data/agenda.json` disparan la skill [buscar-noticias](../proyectos/buscar-noticias.md) sin intervención.

## Acciones activas

| ID | Nombre | Hora | Tipo | Chat |
|----|--------|------|------|------|
| 2 | Buscar noticias diarias | 08:00 | `diaria` | 5483766132 (Rhay) |
| 3 | Enviar resumen de noticias por la noche | 20:00 | `diaria` | 5483766132 (Rhay) |

Ambas con `activa: true`. Mismo prompt en las dos (la única diferencia operativa es la hora):

> Ejecuta la skill 'buscar-noticias' para obtener los titulares más recientes y sus imágenes. Genera un resumen con: 3 titulares principales, enlaces, y una breve descripción de cada uno. Adjunta las imágenes. Envía el resumen por Telegram a las 8:00 [AM/PM].

## Cómo se ejecutan

El scheduler interno del agente (`agente_core/agenda_scheduler.py`) revisa la agenda y, cuando llega la hora, inyecta el `prompt` como si fuera un mensaje de usuario. El agente entonces:

1. Llama a la tool de ejecutar skill → corre `skills/buscar-noticias/run.py`.
2. Lee `reporte_diariolibre.md` que la skill acaba de generar.
3. Arma un resumen propio con 3 titulares principales + descripción breve.
4. Manda por Telegram (texto + imágenes adjuntas) al `chat_id` configurado.

## Editar la agenda

Vía conversación con el agente:
- "Cambia la hora del resumen nocturno a 21:00"
- "Desactiva la acción 2"
- "Lista las acciones de agenda"

Lo hace usando la tool de agenda (CRUD sobre `agenda.json`). No editar el JSON a mano si el agente está corriendo — el scheduler tiene `agenda.json` en RAM y un edit externo se pierde en el siguiente save.

## Qué pasa si la skill falla

- Si el scraper imprime `"Error al scrapear Diario Libre..."`, el agente lo ve como output del tool call y normalmente intenta una segunda vez o reporta el fallo en el resumen por Telegram.
- Si el reporte queda vacío (sin noticias parseadas), el agente debería avisar — no enviar resumen vacío.
- El error se registra en `ultimo_error` de la entrada de agenda + en el historial de `ejecuciones[]`.

## Por qué dos veces al día

Decisión de Rhay (24-abr-2026): noticias a primera hora (8 AM, después del despertar) y al cierre (8 PM, antes de la cama). El feed de `ultima-hora` rota suficiente entre ambas como para no repetir contenido idéntico.

Si en algún momento Rhay quiere reducir a una sola: desactivar la acción 3 (la nocturna). Si quiere más cobertura, la lógica del agente al elegir "3 principales" hace de filtro — no hay riesgo de spam por correr más seguido, pero tampoco aporta valor proporcional.

## Persistencia del historial

`agenda.json` guarda en cada acción un array `ejecuciones[]` con los últimos resultados (timestamp + éxito + resumen truncado). Es la única huella histórica de qué se mandó — `reporte_diariolibre.md` se sobreescribe en cada corrida.

## Relacionado

- [buscar-noticias (skill)](../proyectos/buscar-noticias.md)
- [Scraping de noticias](../conceptos/scraping-noticias.md)
- [Configuración de Telegram](telegram.md)
