# Guía paso a paso — Crear cuentas y publicar el primer Reel

**Hecho para Rhay.** Asumimos que NO has tocado IG, FB o YouTube nunca con esta marca. Te llevo de cero hasta el reel publicado.

**Tiempo estimado:** 1 hora 30 minutos (puedes partir en sesiones).

---

## ÍNDICE

1. [Verificar que tienes el reel generado](#paso-1)
2. [Crear correo de la marca](#paso-2)
3. [Crear cuenta Instagram](#paso-3)
4. [Crear página Facebook](#paso-4)
5. [Vincular IG + FB](#paso-5)
6. [Crear canal YouTube (opcional hoy)](#paso-6)
7. [Subir el reel a Instagram](#paso-7)
8. [Subir el reel a Facebook](#paso-8)
9. [Subir como Short a YouTube (opcional)](#paso-9)
10. [Qué hacer en las primeras 24 horas](#paso-10)

---

## <a name="paso-1"></a>Paso 1 — Verificar que tienes el reel generado (1 min)

El archivo debe estar aquí:
```
C:\proyectos\ranger sistemas\videos-tutoriales\out\reel-carrusel-1.mp4
```

Doble-click para abrirlo. Debe durar **~28 segundos**, ser vertical, mostrar las 8 slides con narración dominicana.

**Si no existe o quieres regenerarlo:**

```bash
cd "C:\proyectos\ranger sistemas\videos-tutoriales"

# Solo si necesitas regenerar el audio:
python marketing/generate-reel-audio.py

# Renderizar el video:
npx remotion render Carrusel1Reel out/reel-carrusel-1.mp4
```

Toma 2-5 minutos según tu PC.

---

## <a name="paso-2"></a>Paso 2 — Crear correo de la marca (5 min)

**Recomendado:** correo nuevo y separado de tu personal.

1. Ir a [accounts.google.com/signup](https://accounts.google.com/signup)
2. Nombre: `Ranger` · Apellido: `Nómina`
3. Username: `ranger.nomina.rd` (o `rangernominard`, `rangernomina2026`, lo que esté disponible)
4. Contraseña: úsala fuerte y guárdala en un manejador de contraseñas

Resultado: `ranger.nomina.rd@gmail.com` o equivalente. Lo usarás para IG, FB y YT.

**Si prefieres no crear correo nuevo:** usa `rhayalcantara@gmail.com`. Pero te recomiendo separar para que en el futuro otra persona pueda manejar las RRSS sin pedirte el tuyo.

---

## <a name="paso-3"></a>Paso 3 — Crear cuenta Instagram (10 min)

### 3.1 Registro

1. Abrir app Instagram (o ir a [instagram.com](https://www.instagram.com))
2. Tocar **"Crear cuenta nueva"** → continuar con email
3. Email: el que creaste en el Paso 2
4. Nombre completo: `Ranger Nómina`
5. **Username:** intenta `ranger.nomina`
   - Si está tomado: `rangernominard`, `ranger.nomina.rd`, `ranger_nomina`
   - Apunta el que termines usando — lo necesitarás en FB y YT
6. Contraseña: misma que el email (o gestor de contraseñas)
7. Fecha de nacimiento: la tuya (Instagram no la muestra pública)
8. Verificar email con el código que llega

### 3.2 Convertir a cuenta profesional

Esto desbloquea estadísticas y permite **publicar reels más fácil**.

1. Tocar tu foto de perfil → **"Configuración"**
2. **"Cuenta"** → bajar hasta **"Cambiar a cuenta profesional"**
3. Tocar **"Continuar"** varias veces
4. **Categoría:** `Software empresarial` o `Empresa de software`
5. ¿Empresa o creador? → **"Empresa"**
6. Datos de contacto: tu correo de marca (paso 2)
7. **Saltar** los pasos de Facebook por ahora (lo haremos en paso 4)

### 3.3 Foto de perfil

1. Editar perfil → **"Cambiar foto"**
2. Subir `ranger-icon.png` (lo descargaste de `LOGO_RANGER.html`)
   - Si no lo tienes: abre `C:\proyectos\agenteIAlocal\LOGO_RANGER.html` y baja la "Foto de perfil"

### 3.4 Bio

En **"Editar perfil"** → **Biografía**, pega exacto:

```
RANGER NÓMINA · 🇩🇴
El sistema de nómina que sí
entiende República Dominicana

✓ ISR · AFP · ARS · Regalía
✓ Cierres auditados

👇 Calculadora ISR gratis
```

(El link de la bio lo agregamos mañana cuando subas la calculadora a Netlify.)

---

## <a name="paso-4"></a>Paso 4 — Crear página Facebook (10 min)

### 4.1 Crear la página

1. Desde tu Facebook personal en [facebook.com](https://www.facebook.com), buscar **"Páginas"** en el menú lateral
2. **"+ Crear nueva página"**
3. **Nombre de la página:** `Ranger Nómina`
4. **Categoría:** escribir `Empresa de software` y seleccionar
5. **Descripción:**

```
Sistema de nómina específico para República Dominicana.
ISR exacto, AFP, ARS, regalía, cierres auditados.
Para PyMEs que quieren nómina sin dolor.
```

6. **"Crear página"**

### 4.2 Foto de perfil y portada

1. **Foto de perfil:** subir `ranger-icon.png` (la misma que IG)
2. **Foto de portada:** subir `ranger-cover-fb.png` (también de `LOGO_RANGER.html`)

### 4.3 Información adicional

En **"Acerca de"** → **"Información de contacto"**:
- **Correo:** tu correo de marca (paso 2)
- **Sitio web:** déjalo vacío por ahora (lo llenas mañana con URL Netlify)
- **Categoría:** Software empresarial

---

## <a name="paso-5"></a>Paso 5 — Vincular Instagram + Facebook (5 min)

Esto permite publicar 1 vez y aparece en ambas redes.

1. Ir a [business.facebook.com](https://business.facebook.com) (Meta Business Suite)
2. Iniciar sesión con tu Facebook personal (el que creó la página Ranger Nómina)
3. Si te pide crear una cuenta de Business: usa nombre `Ranger Nómina`
4. **Configuración** (engranaje) → **"Cuentas de Instagram"**
5. **"Agregar"** → vincular con `@ranger.nomina` (te llevará a iniciar sesión IG)
6. Aceptar permisos

✅ Cuando publiques desde Meta Business Suite o desde el botón "Compartir en Facebook" de IG, aparecerá en ambas.

---

## <a name="paso-6"></a>Paso 6 — Crear canal YouTube (10 min · OPCIONAL HOY)

YouTube se puede dejar para la semana 2 si quieres. Si lo haces ahora:

1. Ir a [youtube.com](https://www.youtube.com) e iniciar sesión con tu correo de marca (paso 2)
2. Tocar tu foto (arriba derecha) → **"Crear un canal"**
3. **"Usar un nombre personalizado"** → `Ranger Nómina RD`
4. **Crear canal**
5. **Personalizar el canal**:
   - Foto de perfil: `ranger-icon.png`
   - Banner: `ranger-cover-fb.png` (sirve igual, dimensiones similares)
   - Descripción del canal:
   ```
   Tutoriales y casos de uso de Ranger Nómina, el sistema de nómina especializado en República Dominicana.

   En este canal aprenderás:
   • Cálculo correcto de ISR según tramos DGII
   • AFP, ARS y descuentos de ley
   • Regalía pascual (salario 13)
   • Vacaciones según Código Laboral RD
   • Cierres auditados y reportes a banco

   Para contadores, RRHH y dueños de PyMEs dominicanas.

   📧 Contacto: ranger.nomina.rd@gmail.com
   📷 Instagram: @ranger.nomina
   ```

---

## <a name="paso-7"></a>Paso 7 — Subir el reel a Instagram (10 min)

### 7.1 Desde el celular (recomendado)

1. Pasar `reel-carrusel-1.mp4` al celular:
   - **Opción A:** Google Drive — subir desde PC, descargar en celular
   - **Opción B:** WhatsApp Web — enviártelo a ti mismo
   - **Opción C:** Telegram — "Mensajes guardados"
2. Abrir Instagram en el celular
3. Tocar **`+`** → **"Reel"**
4. Seleccionar el video (debe verse en tu galería)
5. **NO** uses los filtros/música de Instagram (ya tiene voiceover propio)
6. **Caption** (copiar exacto):

```
ESTO es Ranger Nómina.

15 segundos. Todo lo que necesitas saber:
✓ Cálculos legales RD precisos
✓ Cierres auditados con evidencia
✓ Reportes a banco en CSV
✓ Para 10 a 500 empleados

DM "INFO" para conocer el sistema.

#NominaRD #ContadoresRD #PyMEsRD #SoftwareDominicano #RRHH #DGII #TSS #Empresarios #NominaDigital #SantoDomingo
```

7. **Configuración avanzada:**
   - ✅ Activar "También publicar en Facebook"
   - ✅ Permitir descargas
   - ✅ Permitir remezclas
   - Etiquetas/hashtags: ya van en el caption
8. **"Compartir"**

### 7.2 Desde la web (alternativa)

Instagram Reels NO se puede subir desde el sitio web normalmente. Usa [business.facebook.com](https://business.facebook.com):
1. Meta Business Suite → **"Crear publicación"** → **"Reel"**
2. Seleccionar el archivo MP4
3. Agregar caption (mismo de arriba)
4. Programar o publicar ahora

---

## <a name="paso-8"></a>Paso 8 — Subir el reel a Facebook (5 min)

Si en Instagram marcaste "También en Facebook", **ya está**. Salta al Paso 9.

Si no:
1. Página Ranger Nómina en Facebook
2. **"Crear publicación"** → **"Carrete"**
3. Subir el archivo
4. Mismo caption del Paso 7

---

## <a name="paso-9"></a>Paso 9 — Subir como Short a YouTube (5 min · si creaste canal)

1. Ir a [youtube.com](https://www.youtube.com) logueado en `Ranger Nómina RD`
2. Tocar **`Crear`** (cámara con `+`) → **"Subir video"**
3. Seleccionar `reel-carrusel-1.mp4`
4. **Título:** `Conoce Ranger Nómina · Sistema de nómina para RD`
5. **Descripción:**

```
Ranger Nómina es el sistema de nómina especializado en República Dominicana.

✓ Cálculos ISR 2026 según tramos DGII
✓ AFP (2.87%) y ARS (3.04%) capeados
✓ Regalía pascual proporcional
✓ Vacaciones en días hábiles del Código Laboral
✓ Cierres auditados con evidencia
✓ Reportes a banco en CSV listos
✓ Importación masiva desde Excel

Para PyMEs y empresas medianas dominicanas (10-500 empleados).

📩 Para una demo personalizada de 20 minutos, déjanos un comentario o escríbenos a @ranger.nomina en Instagram.

#NominaRD #ISR #DGII #Contadores #PyMEs #SoftwareDominicano #RepublicaDominicana
```

6. **Visibilidad:** Público
7. **Etiquetas:** `nomina, RD, dominicana, ISR, DGII, contadores, software, payroll`
8. **Como YouTube Short** (debería detectarlo automático por ser vertical y <60s)
9. **Publicar**

---

## <a name="paso-10"></a>Paso 10 — Primeras 24 horas (qué hacer)

### Primeras 2 horas
- Compartir el reel a tu **WhatsApp personal** (1 grupo o estado)
- Compartirlo en **LinkedIn personal** si tienes (opcional)
- Avisar a 3-5 amigos contadores/RRHH para que comenten o den like (no compres engagement, solo gente real)

### Hora 4-6
- Revisar comentarios en IG y FB
- Responder TODOS, incluso un "🙏"
- Si alguien pregunta "¿cómo funciona?" o "¿cuánto cuesta?", responder con info real
- Si alguien escribe DM "INFO" → usar la plantilla del archivo `MANUAL_ARRANQUE.md`

### Hora 12-24
- Subir 2-3 stories casuales:
  - "Subimos el primer reel ¿qué piensan?"
  - Poll: "¿Usas Excel para nómina? Sí / No"
  - "Próximamente: calculadora ISR gratis 👀"
- Revisar estadísticas (Instagram Insights desde el perfil profesional)

### Reglas de la primera semana

1. **No supliques seguidores.** El contenido es lo que atrae, no los pedidos.
2. **Responde rápido los DMs.** Cada uno es lead potencial.
3. **No compres seguidores.** Algoritmo te castiga.
4. **Publica con regularidad.** Mañana viernes 15 toca el carrusel #1. Lunes el reel #1 (este). Jueves 22 carrusel #2. Etc.
5. **Mide engagement, no seguidores.** 100 seguidores activos > 1000 fantasmas.

---

## 🆘 Si algo falla

### El render del video falla
```bash
cd "C:\proyectos\ranger sistemas\videos-tutoriales"
npm install
npx remotion render Carrusel1Reel out/reel-carrusel-1.mp4
```

### Audio no se escucha en el video
1. Verificar que `public/audio/reel-carrusel-1.mp3` existe
2. Re-generar: `python marketing/generate-reel-audio.py`
3. Re-renderizar

### Instagram dice "no se puede subir"
- Verifica que el archivo sea MP4 (no MOV ni AVI)
- Verifica que dure menos de 90 segundos (el nuestro dura ~28s, OK)
- Verifica que sea vertical 9:16

### Facebook no cross-postea desde IG
- Volver a Meta Business Suite → Configuración → Cuentas de Instagram → re-vincular

---

## ✅ Checklist final

- [ ] Reel renderizado en `out/reel-carrusel-1.mp4`
- [ ] Correo de marca creado
- [ ] Cuenta Instagram `@ranger.nomina` lista con bio y foto
- [ ] Página Facebook `Ranger Nómina` lista con portada
- [ ] IG + FB vinculadas en Meta Business Suite
- [ ] (Opcional) Canal YouTube `Ranger Nómina RD` listo
- [ ] Reel subido a Instagram como Reel
- [ ] Reel publicado en Facebook (cross-post automático o manual)
- [ ] (Opcional) Short subido a YouTube
- [ ] Primeras 2 horas: compartido a contactos cercanos
- [ ] Plantillas DM listas a mano (`MANUAL_ARRANQUE.md`)

---

*Generado por Claudy el 14 may 2026 para Rhay.*
