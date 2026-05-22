# Skill: Manejo TV

Control remoto de los televisores de la casa via red local (ADB over WiFi).

## TVs disponibles

| Nombre | Area | Marca | IP | Notas |
|--------|------|-------|-----|-------|
| TV Cuarto Bernar | Cuarto de Bernar | CHiQ Milexus | 192.168.1.45 | Android TV 11 |
| TV Habitacion Principal | Habitacion principal | JVC 4K | 192.168.1.182 | Android TV 11 |
| TV Sala | Sala | Amazon Fire TV Stick | 192.168.1.193 | Fire OS (Android 9). No apaga el TV TecnoMaster, solo el Stick |

## Como usar

Todas las operaciones se hacen con la herramienta `google_tv`:

### Encender / Apagar
```
google_tv(operacion="encender", nombre="TV Sala")
google_tv(operacion="apagar", nombre="TV Habitacion Principal")
google_tv(operacion="apagar_todos")
```

### Volumen
```
google_tv(operacion="volumen", nombre="TV Sala", accion="subir")
google_tv(operacion="volumen", nombre="TV Sala", accion="subir", nivel=5)
google_tv(operacion="volumen", nombre="TV Sala", accion="bajar")
google_tv(operacion="volumen", nombre="TV Sala", accion="mute")
```

### Abrir apps
```
google_tv(operacion="app", nombre="TV Sala", aplicacion="youtube")
google_tv(operacion="app", nombre="TV Sala", aplicacion="netflix")
google_tv(operacion="app", nombre="TV Sala", aplicacion="disney+")
google_tv(operacion="app", nombre="TV Sala", aplicacion="prime")
google_tv(operacion="app", nombre="TV Sala", aplicacion="spotify")
google_tv(operacion="app", nombre="TV Sala", aplicacion="hbo")
```
Apps disponibles: youtube, netflix, disney+, prime, hbo, max, spotify, plex, twitch, chrome, kodi, vlc, configuracion, play store

### Poner noticias / contenido de YouTube (operacion "youtube")
`app` solo abre YouTube en home. Para REPRODUCIR algo concreto usa `youtube`:
```
# Canal de noticias en vivo (presets):
google_tv(operacion="youtube", nombre="principal", canal="dw")
google_tv(operacion="youtube", nombre="principal", canal="cdn")
# Cualquier URL de YouTube (canal/live, watch, etc.):
google_tv(operacion="youtube", nombre="principal", url="https://www.youtube.com/watch?v=XXXX")
# Por ID de video:
google_tv(operacion="youtube", nombre="principal", video="dQw4w9WgXcQ")
# Busqueda (abre resultados):
google_tv(operacion="youtube", nombre="principal", buscar="noticias republica dominicana hoy")
```
Presets de canales de noticias en vivo: **dw** (DW Espanol), **cdn** (CDN 37 RD), **noticias sin**, **color vision**, **listin**. (La operacion despierta la pantalla automaticamente antes de abrir.)

### Navegacion y control
```
google_tv(operacion="control", nombre="TV Sala", comando="arriba")
google_tv(operacion="control", nombre="TV Sala", comando="abajo")
google_tv(operacion="control", nombre="TV Sala", comando="izquierda")
google_tv(operacion="control", nombre="TV Sala", comando="derecha")
google_tv(operacion="control", nombre="TV Sala", comando="ok")
google_tv(operacion="control", nombre="TV Sala", comando="back")
google_tv(operacion="control", nombre="TV Sala", comando="home")
google_tv(operacion="control", nombre="TV Sala", comando="play")
google_tv(operacion="control", nombre="TV Sala", comando="pausa")
google_tv(operacion="control", nombre="TV Sala", comando="mute")
```
Controles: arriba, abajo, izquierda, derecha, ok, enter, back, home, menu, play, pausa, stop, siguiente, anterior, adelantar, retroceder, mute, silencio, buscar, info, guia

### Cambiar entrada HDMI
Para cambiar de entrada HDMI, usa control con el keycode directo:
```
google_tv(operacion="control", nombre="TV Cuarto Bernar", comando="KEYCODE_TV_INPUT_HDMI_1")
google_tv(operacion="control", nombre="TV Cuarto Bernar", comando="KEYCODE_TV_INPUT_HDMI_2")
google_tv(operacion="control", nombre="TV Cuarto Bernar", comando="KEYCODE_TV_INPUT_HDMI_3")
```

### Escribir texto (busquedas)
```
google_tv(operacion="escribir", nombre="TV Sala", texto="pelicula de accion")
```

### Ver estado
```
google_tv(operacion="estado")
google_tv(operacion="estado", nombre="TV Sala")
google_tv(operacion="listar")
```

### Escanear red
```
google_tv(operacion="escanear")
```

## Notas importantes

- Los TVs deben tener **Depuracion USB activada** (Opciones de desarrollador)
- El nombre del TV se busca parcial: "sala" encuentra "TV Sala", "bernar" encuentra "TV Cuarto Bernar", "principal" encuentra "TV Habitacion Principal"
- La TV Sala es un Fire TV Stick conectado a un TecnoMaster — apagar solo apaga el Stick, no el TV fisico (no tiene CEC)
- Si un TV no responde, puede haberse desconectado del WiFi o cambiado de IP
- ADB esta instalado en: C:\Users\rhay_\platform-tools\adb.exe

### Si ADB sale "unauthorized" (no ejecuta comandos)
La autorizacion se pierde a veces. `encender`/`youtube`/etc. devolveran un aviso. Para arreglar:
1. Con la TV ENCENDIDA, en la TV: Ajustes → Opciones de desarrollador → "Revocar autorizaciones de depuracion USB", dejar Depuracion ON.
2. `adb kill-server && adb connect <ip>:5555` y aceptar el aviso en la TV ("Siempre permitir").
Si la TV esta apagada y `encender` no responde por estar unauthorized, se puede **encender por Wake-on-LAN** (magic packet al MAC de la TV, broadcast puertos 9/7) — eso la prende, pero apagar/controlar sigue exigiendo ADB autorizado.

### Verificar que se ve en pantalla (screenshot)
```
adb -s <ip>:5555 shell screencap -p /sdcard/x.png
adb -s <ip>:5555 pull /sdcard/x.png <ruta-local>
```
En git-bash usar `MSYS_NO_PATHCONV=1` para que no mangle `/sdcard/...`, y dar el destino en ruta Windows (`C:/...`). NO usar `adb exec-out screencap > file` en git-bash (corrompe el binario).

### Panel de datos en la TV (relacionado)
`tv_panel_server.py` (raiz) sirve un dashboard (`/` stats de PC, `/pendientes` lee la agenda del agente) que se abre en la TV con la operacion `youtube` url=... o un VIEW intent. Util para dejar la TV como panel de informacion.

## Ejemplos de uso natural

El usuario dice → lo que haces:
- "Pon Netflix en la tele de la sala" → `google_tv(operacion="app", nombre="TV Sala", aplicacion="netflix")`
- "Apaga todas las teles" → `google_tv(operacion="apagar_todos")`
- "Sube el volumen de la habitacion" → `google_tv(operacion="volumen", nombre="TV Habitacion Principal", accion="subir")`
- "Que esta puesto en la tele de Bernar?" → `google_tv(operacion="estado", nombre="TV Cuarto Bernar")`
- "Cambia a HDMI 2 en la tele de Bernar" → `google_tv(operacion="control", nombre="TV Cuarto Bernar", comando="KEYCODE_TV_INPUT_HDMI_2")`
- "Busca peliculas de Marvel en YouTube" → `google_tv(operacion="app", ...)` + `google_tv(operacion="escribir", ...)`
- "Pon noticias en la habitacion principal" → `google_tv(operacion="youtube", nombre="principal", canal="cdn")` (o el canal que prefiera)
- "Pon DW en la tele" → `google_tv(operacion="youtube", nombre="principal", canal="dw")`
- "Enciende la tele del cuarto principal" → `google_tv(operacion="encender", nombre="principal")` (si esta unauthorized o no responde, usar Wake-on-LAN)
- "Pon este video de YouTube en la sala" → `google_tv(operacion="youtube", nombre="TV Sala", url="<url>")`
