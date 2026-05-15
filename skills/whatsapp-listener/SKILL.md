# Skill: WhatsApp Listener

Conecta a WhatsApp via whatsapp-web.js y escucha mensajes de chats y grupos.

## Cuando usar esta skill
- El usuario dice "conectate a WhatsApp", "inicia WhatsApp", "escucha WhatsApp"
- Quiere monitorear el grupo "sistemaray" de su cliente Ranger
- Necesita recibir mensajes de WhatsApp

## Ejecucion

### 1. Verificar si ya esta corriendo
```bash
tasklist | grep -i node | grep -v grep
```
Si hay procesos node corriendo whatsapp_test.js, ya esta activo.

### 2. Iniciar el listener
```bash
node C:/proyectos/agenteIAlocal/whatsapp_test.js
```
Ejecutar en background con `run_in_background: true`.

### 3. Primera vez (sin sesion guardada)
- Se genera un QR como imagen en `whatsapp_qr.png` y se abre automaticamente
- El usuario debe escanear con: WhatsApp > Dispositivos vinculados > Vincular dispositivo
- La sesion se guarda en `.wwebjs_auth/` para proximas veces

### 4. Siguientes veces
- Se conecta automaticamente sin QR
- Muestra "WHATSAPP CONECTADO" cuando esta listo

### 5. Monitorear mensajes
Armar un Monitor con:
```bash
tail -f <output_file> | grep -E --line-buffered "\[|->|CONECTADO|Autenticado|Error"
```

## Leer historial de mensajes

### Opcion PRIMARIA: `whatsapp_leer_cache.py` (recomendado siempre que el monitor este vivo)

Lee desde `whatsapp_nuevos.json` que el monitor llena en tiempo real. **NO toca el browser**, asi que NO interfiere con `whatsapp_monitor.js`. Usalo por default.

```bash
python whatsapp_leer_cache.py "SISTEMA RAY" 20       # ultimos 20 del grupo
python whatsapp_leer_cache.py "Rhay" 10              # ultimos 10 del DM con Rhay
python whatsapp_leer_cache.py --list                  # lista chats unicos vistos
python whatsapp_leer_cache.py --since 2026-05-14 "SISTEMA RAY"  # filtrado
python whatsapp_leer_cache.py "SISTEMA RAY" 5 --json  # output JSON
python whatsapp_leer_cache.py 120363424666838458@g.us 10  # por chat_id literal
```

Comportamiento:
- Busqueda por nombre = case-insensitive + substring (ej. "ray" matchea "SISTEMA RAY").
- Si match es ambiguo, imprime la lista y sale con codigo 3. Refina con un substring mas largo o usa el `chat_id`.
- Si no encuentra nada, codigo 4 + mensaje.
- Solo muestra mensajes desde que arranco el monitor (no historial mas viejo).

Tips de quoting cuando invocas desde `execute_bash`:
- En Windows (cmd.exe) las comillas dobles funcionan: `python whatsapp_leer_cache.py "SISTEMA RAY" 5`.
- Evita comillas innecesarias en numeros: `5` no `"5"`.
- Si el nombre tiene comillas o caracteres especiales, considera usar el chat_id literal en su lugar.

### Opcion ALTERNATIVA: `whatsapp_leer.js` (solo si el monitor NO esta corriendo)

```bash
node C:/proyectos/agenteIAlocal/whatsapp_leer.js "NOMBRE DEL CHAT" [cantidad]
```
Ejemplos:
- `node whatsapp_leer.js "SISTEMA RAY" 20` — ultimos 20 mensajes (lee directo del browser)
- `node whatsapp_leer.js "Rhay" 10` — ultimos 10 del DM con Rhay

**Limitacion:** levanta su propio Puppeteer, asi que **falla con "browser is already running"** si `whatsapp_monitor.js` esta vivo. Usar solo cuando necesites historial pre-monitor o como fallback. Si el monitor esta corriendo, **detener primero** con `taskkill //PID <pid_monitor> //F`, leer, y volver a arrancar el monitor.

Si el chat no se encuentra, lista los chats disponibles.

## Grupos de interes
- **SISTEMA RAY** — ID: `120363424666838458@g.us` — Grupo del cliente Ranger donde exponen situaciones del sistema. Los mensajes de este grupo son prioritarios.
- Miembros clave: Nicaury A. Brito (operadora), Agustina Cordero (operadora), Rhay B. Alcantara M. (desarrollador)

## Arquitectura
- **whatsapp_test.js** — Script Node.js con whatsapp-web.js
- **Autenticacion** — LocalAuth guardada en `.wwebjs_auth/`
- **Dependencias Node** — whatsapp-web.js, qrcode (en node_modules/)
- **Puppeteer** — Chromium headless para WhatsApp Web

## Formato de mensajes recibidos
```
[NombreGrupo] NombreContacto: texto del mensaje
  -> Grupo ID: 120363XXXXXX@g.us
[DM] NombreContacto: texto del mensaje
```

## Detener
```bash
tasklist | grep node | awk '{print $2}' | while read pid; do taskkill //PID $pid //F; done
```
