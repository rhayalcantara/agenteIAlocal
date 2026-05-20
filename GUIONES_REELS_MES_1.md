# Guiones de Reels — Mes 1

**4 reels listos para grabar.** Cada uno con:
- **Duración objetivo**: 15-30 segundos
- **Timing**: segundo por segundo, pantalla por pantalla
- **Voiceover**: línea exacta para generar en ElevenLabs / TTS (voz español dominicano o neutral)
- **Captions on-screen**: lo que aparece en grande (lectura sin sonido)
- **Sonidos**: tipo de audio sugerido
- **Producción**: cómo grabar el screencast

**Especificaciones técnicas comunes:**
- Formato vertical 9:16 (1080×1920)
- 30 fps mínimo
- Fuente captions: Inter Bold blanca, sombra negra suave
- Logo Ranger esquina superior izquierda, pequeño
- Audio voiceover: -3 dB normalizado, +5% velocidad

---

## REEL #1 — "Tour de 15 segundos por Ranger"

**Cuándo:** Semana 1 (15-21 may) — apoyo del Carrusel #1
**Objetivo:** Curiosidad, presentación visual del sistema
**Hook:** vista del dashboard moviéndose rápido
**Duración:** 15 segundos

### Storyboard

| Tiempo | Pantalla | Voiceover IA (español) | Caption on-screen |
|--------|----------|------------------------|-------------------|
| 0:00–0:02 | Cursor abre el navegador y entra a Ranger | "Esto..." | (vacío, dejar respirar) |
| 0:02–0:05 | Dashboard de Ranger con KPIs animados | "...es Ranger Nómina." | **ESTO ES RANGER** |
| 0:05–0:08 | Click en Empleados, vista lista con fotos | "Tu plantilla en RD." | **EMPLEADOS RD ✓** |
| 0:08–0:11 | Click en Nóminas, vista del cálculo | "Tu nómina calculada." | **CÁLCULO EXACTO** |
| 0:11–0:13 | Click en Cerrar, animación de cierre | "Tu cierre auditado." | **CIERRE AUDITADO** |
| 0:13–0:15 | Logo grande + CTA "DM INFO" | "Pruébalo." | **DM "INFO"** + @ranger.nomina |

### Sonido
- Música: track instrumental energético tipo "corporate upbeat" (royalty free en Pixabay)
- SFX: 3 clicks suaves (uno por sección)
- Cierre: ping satisfactorio en cierre

### Producción
1. Abrir Ranger en frontend Angular (4200) con datos demo (Distribuidora Demo SRL)
2. OBS Studio: grabar la pantalla a 1920×1080
3. Mover ratón fluido y planeado (escribir guion de clicks antes)
4. Editar en CapCut: recortar a vertical 9:16, agregar captions, voiceover, música

### Caption del reel (Instagram)
```
ESTO es Ranger Nómina.

15 segundos. Todo lo que necesitas:
✓ Empleados RD
✓ Cálculo exacto
✓ Cierre auditado

DM "INFO" para conocerlo.

#NominaRD #ContadoresRD #SoftwareDominicano #PyMEsRD #DGII #RRHH
```

---

## REEL #2 — "Calcula ISR en 10 segundos"

**Cuándo:** Semana 2 (22-28 may) — apoyo del Carrusel #2 "5 errores al calcular ISR"
**Objetivo:** Demo concreta del módulo ISR / o de la calculadora online
**Hook:** "¿Cuánto pagas de ISR? Te lo digo en 10 segundos."
**Duración:** 20 segundos

### Storyboard

| Tiempo | Pantalla | Voiceover IA | Caption on-screen |
|--------|----------|--------------|-------------------|
| 0:00–0:02 | Persona escribe "Salario: 60,000" en calculadora | "Salario mensual: sesenta mil." | **SALARIO: RD$60,000** |
| 0:02–0:04 | Pantalla escribiendo (mientras pasa el voiceover) | "Click." | (cursor llamativo) |
| 0:04–0:07 | Resultado aparece: AFP, ARS, ISR | "AFP, ARS, ISR. Calculado." | **AFP $1,722 · ARS $1,824** |
| 0:07–0:11 | Zoom al neto resaltado | "Tu neto: cincuenta y cuatro mil, ochocientos." | **NETO: RD$54,800** ✓ |
| 0:11–0:14 | Tabla de tramos ISR aplicada | "Sin Excel. Sin fórmulas. Sin enredos." | **TRAMOS 2026 OFICIALES** |
| 0:14–0:18 | URL de la calculadora visible | "Pruébala gratis." | **LINK EN BIO** |
| 0:18–0:20 | Logo Ranger | "Por Ranger Nómina." | **@RANGER.NOMINA** |

### Sonido
- Música: track tipo "tech ambient" minimalista
- SFX: tic-tac de cuenta regresiva en 0:00-0:11
- Sonido satisfactorio al aparecer el neto

### Producción
1. Abrir CALCULADORA_ISR.html en navegador, modo presentación
2. Grabar pantalla con OBS (zoom 150% para que se vea grande en vertical)
3. Editar en CapCut: agregar zooms suaves a campos clave, captions grandes

### Caption del reel
```
Calcula tu ISR 2026 en 10 segundos. Sin Excel.

Sin fórmulas. Sin enredos.

Link en bio → calculadora gratis.

Si quieres esto para TODA tu nómina (no solo un cálculo), DM "DEMO".

#ISRRD #NominaRD #ContadoresRD #DGII #CalculadoraISR #SoftwareDominicano #PyMEsRD
```

---

## REEL #3 — "El error de regalía"

**Cuándo:** Semana 3 (29 may - 4 jun) — apoyo del Carrusel #3
**Objetivo:** Educación + lead magnet plantilla Excel
**Hook:** "Pagaste regalía... y le debes a tu empleado."
**Duración:** 25 segundos

### Storyboard

| Tiempo | Pantalla | Voiceover IA | Caption on-screen |
|--------|----------|--------------|-------------------|
| 0:00–0:03 | Texto grande sobre fondo rojo | "Pagaste regalía..." | **"PAGUÉ REGALÍA"** |
| 0:03–0:06 | Cambia a texto: "...y le debes a tu empleado." | "...y le debes a tu empleado." | **"...PERO LE DEBES"** |
| 0:06–0:10 | Pantalla split: "Mes de sueldo" tachado vs "1/12 del año" | "Regalía NO es un mes de sueldo." | **NO ES UN MES** |
| 0:10–0:14 | Fórmula real con números | "Es uno entre doce de lo ganado en el año." | **REGALÍA = TOTAL ANUAL / 12** |
| 0:14–0:18 | Captura de Ranger calculando regalía automático | "Ranger lo calcula automático." | **RANGER LO HACE SOLO** |
| 0:18–0:22 | Pantalla con CTA | "DM la palabra REGALIA." | **DM "REGALIA" 📩** |
| 0:22–0:25 | Logo + handle | "Te enviamos la plantilla gratis." | **PLANTILLA GRATIS** |

### Sonido
- Apertura: sonido de error/notificación dramático (0:00-0:03)
- Resto: track tipo "explainer" calmo
- Cierre: ping satisfactorio

### Producción
1. Crear los frames de texto en Canva o directamente en CapCut (no requiere screencast del sistema)
2. Para el frame 0:14-0:18 sí abrir Ranger y capturar el cálculo
3. Editar todo en CapCut

### Caption del reel
```
"Pagué regalía"... y le debes a tu empleado.

Regalía NO es un mes de sueldo.

Es 1/12 del TOTAL ganado en el año (con comisiones, horas extras y bonos regulares).

Plantilla Excel con la fórmula correcta GRATIS → DM "REGALIA" 📩

#RegaliaRD #SalarioTrece #NominaRD #ContadoresRD #PyMEsRD #DGII #RRHH
```

---

## REEL #4 — "Vacaciones: días hábiles vs calendario"

**Cuándo:** Semana 4 (5-11 jun) — apoyo del Carrusel #4
**Objetivo:** Educación + autoridad técnica
**Hook:** "Le diste 14 días. Le debes 4 más."
**Duración:** 20 segundos

### Storyboard

| Tiempo | Pantalla | Voiceover IA | Caption on-screen |
|--------|----------|--------------|-------------------|
| 0:00–0:03 | Frame negro con texto rojo grande | "Le diste 14 días de vacaciones." | **LE DISTE 14 DÍAS** |
| 0:03–0:06 | Mismo frame, aparece línea adicional | "Y le debes 4 más." | **LE DEBES 4 MÁS** |
| 0:06–0:11 | Calendario animado mostrando días corridos vs hábiles | "14 días hábiles no es lo mismo que 14 corridos." | **HÁBILES ≠ CORRIDOS** |
| 0:11–0:15 | Visualización: 14 hábiles = ~18 corridos | "Catorce hábiles. Dieciocho días en el calendario." | **14 HÁB = 18 CAL** |
| 0:15–0:18 | Captura Ranger calculando vacaciones | "Ranger lo calcula bien." | **RANGER LO HACE** |
| 0:18–0:20 | Logo + handle | "DM la palabra VACACIONES." | **DM "VACACIONES"** |

### Sonido
- Música: track minimalista, contemplativo
- SFX: sonido "ding" en 0:03 al aparecer "le debes 4 más"

### Producción
1. Animar el calendario en CapCut (template "calendar reveal")
2. Capturar el módulo de vacaciones de Ranger
3. Edición simple, sin efectos pesados

### Caption del reel
```
"Le di 14 días de vacaciones"... pero ¿hábiles o corridos?

El Código Laboral RD habla de HÁBILES (lunes a viernes, sin feriados).

Si los diste corridos, le debes 4 días más.

DM "VACACIONES" para el resumen completo.

#VacacionesRD #CodigoLaboral #NominaRD #ContadoresRD #MinisterioDeTrabajo #PyMEsRD
```

---

## Plan de publicación de reels

| Día | Reel | Hora sugerida | Cruce |
|-----|------|---------------|-------|
| Vie 16 may | Reel #1 (Tour) | 7:00 PM RD | Refuerza Carrusel #1 del jueves |
| Vie 23 may | Reel #2 (ISR) | 7:00 PM RD | Refuerza Carrusel #2 + dirige a calculadora |
| Vie 30 may | Reel #3 (Regalía) | 7:00 PM RD | Refuerza Carrusel #3 + captura emails |
| Vie 6 jun | Reel #4 (Vacaciones) | 7:00 PM RD | Refuerza Carrusel #4 |

**Importante:** publicar reel cada viernes después del carrusel del jueves. El carrusel construye autoridad con texto denso, el reel del día siguiente entretiene y refuerza con visual.

---

## Setup para grabar (una sola vez)

### OBS Studio (gratis)
1. Descargar de obsproject.com
2. Configurar escena "Ranger Screencast":
   - Captura de pantalla: monitor donde tienes el navegador
   - Crop a 1080×1920 vertical (en pantalla principal vertical) o grabar horizontal y recortar después en CapCut
3. Salida: 30 fps, 1080p, formato MP4

### Voiceover IA (ElevenLabs recomendado)
1. Crear cuenta en elevenlabs.io (plan free permite varios minutos al mes)
2. Buscar voz español dominicano o neutral latinoamericano
3. Recomendaciones: "Diego" o "Mateo" (voces clones latinos)
4. Velocidad: +5%, claridad: 70%, stability: 50%

### Editor (CapCut gratis)
1. Importar el clip OBS + el audio voiceover
2. Sincronizar visual con narración
3. Agregar captions grandes (estilo Subtitle Auto)
4. Música de fondo a -18 dB para que no tape la voz
5. Exportar 1080×1920 a 30 fps

---

## Batch grabado (recomendado)

Mejor grabar los 4 screencasts del sistema **en un solo día** (~1 hora):
- Sesión 1: Tour dashboard (Reel #1)
- Sesión 2: Calculadora ISR (Reel #2)
- Sesión 3: Módulo regalía (Reel #3)
- Sesión 4: Módulo vacaciones (Reel #4)

Luego, en otra sesión de ~1 hora, generar los 4 voiceovers en ElevenLabs.

Luego, en otra de ~2 horas, editar los 4 reels en CapCut.

Total producción: 4 horas para los 4 reels del mes. Hechos. Programados. Listo.

---

*Generado por Claudy el 14 may 2026.*
