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
- El nombre del TV se busca parcial: "sala" encuentra "TV Sala", "bernar" encuentra "TV Cuarto Bernar"
- La TV Sala es un Fire TV Stick conectado a un TecnoMaster — apagar solo apaga el Stick, no el TV fisico (no tiene CEC)
- Si un TV no responde, puede haberse desconectado del WiFi o cambiado de IP
- ADB esta instalado en: C:\Users\rhay_\platform-tools\adb.exe

## Ejemplos de uso natural

El usuario dice → lo que haces:
- "Pon Netflix en la tele de la sala" → `google_tv(operacion="app", nombre="TV Sala", aplicacion="netflix")`
- "Apaga todas las teles" → `google_tv(operacion="apagar_todos")`
- "Sube el volumen de la habitacion" → `google_tv(operacion="volumen", nombre="TV Habitacion Principal", accion="subir")`
- "Que esta puesto en la tele de Bernar?" → `google_tv(operacion="estado", nombre="TV Cuarto Bernar")`
- "Cambia a HDMI 2 en la tele de Bernar" → `google_tv(operacion="control", nombre="TV Cuarto Bernar", comando="KEYCODE_TV_INPUT_HDMI_2")`
- "Busca peliculas de Marvel en YouTube" → `google_tv(operacion="app", ...)` + `google_tv(operacion="escribir", ...)`
