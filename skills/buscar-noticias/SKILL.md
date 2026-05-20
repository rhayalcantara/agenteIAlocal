Extrae los titulares mas recientes de Diario Libre y genera un reporte en Markdown.

## Uso
- "Busca noticias"
- "Que hay de nuevo en las noticias"
- "Noticias de hoy"

## Ejecucion
Ejecuta el script con `ejecutar_script_skill`:
- skill: "buscar-noticias"
- script: "run.py"
- args: "" (sin argumentos)

## Resultado
- Genera `reporte_diariolibre.md` en la raiz del proyecto
- Imprime la lista de titulares en la salida
- Muestra las 10 noticias mas recientes de https://www.diariolibre.com/ultima-hora

## Importante
- NO uses Gmail, SMTP ni correo. Esta skill hace scraping web directo.
- NO inventes comandos. Solo ejecuta run.py sin argumentos.
