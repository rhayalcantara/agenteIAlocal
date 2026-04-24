# Skill: seguimiento

Tracking universal de notificaciones con cambio de estado en el tiempo.
Usa SQLite para persistencia robusta. Válido para: envíos, transacciones bancarias, reservas, solicitudes y cualquier proceso que avance por estados.

## Cuándo usar esta skill

- El usuario menciona un envío, paquete, pedido o número de tracking
- El usuario pide monitorear una transacción bancaria, pago o transferencia
- Se detecta en un correo un número de seguimiento, orden o referencia de proceso
- El usuario quiere saber el estado actual de algo que se está procesando
- El sub-agente de la agenda está ejecutando un ciclo de monitoreo

## Tipos soportados

| tipo         | Ejemplos                                              |
|--------------|-------------------------------------------------------|
| envio        | Paquete Amazon, DHL, FedEx, UPS, correo postal        |
| transaccion  | Transferencia bancaria, pago en proceso, reembolso    |
| reserva      | Cita médica, hotel, vuelo, restaurante                |
| solicitud    | Trámite de VISA, seguro, crédito, documento oficial   |
| otro         | Cualquier proceso con estados progresivos             |

## Cómo invocar (via ejecutar_script_skill)

```
ejecutar_script_skill("seguimiento", "run.py", "[operacion] [args]")
```

Los args soportan comillas para valores con espacios:
```
ejecutar_script_skill("seguimiento", "run.py", 'agregar --tipo envio --titulo "Pedido Amazon #123" --empresa Amazon')
```

---

## Operaciones

### agregar — Registrar nuevo seguimiento
```
agregar --tipo [tipo] --titulo "[nombre]" --empresa "[empresa]"
        --referencia "[tracking/orden]" --url "[url_tracking]"
        --estado-inicial "[estado]" --estado-final "[palabra_clave_final]"
        --chat-id [chat_id] --notas "[notas]"
```
Solo `--tipo` y `--titulo` son obligatorios.

Retorna el ID del seguimiento y el **prompt sugerido para crear la agenda de monitoreo**.
Después de crear la agenda, vincula con `vincular-agenda`.

**Ejemplo:**
```
agregar --tipo envio --titulo "Pedido Amazon #123-456-789" --empresa Amazon
        --referencia "TBA123456789" --url "https://tracking.amazon.com/..."
        --estado-inicial "En tránsito" --estado-final "Entregado" --chat-id 5483766132
```

---

### listar — Ver seguimientos activos
```
listar
listar --tipo envio
listar --todos
```

---

### ver — Detalle completo con historial
```
ver --id [id]
```
Muestra estado actual, URL, empresa, referencia y los últimos 15 cambios de estado.

---

### actualizar — Registrar nuevo estado (usar en ciclos de monitoreo)
```
actualizar --id [id] --estado "[nuevo estado]" --descripcion "[detalle]" --fuente [auto|email|web|manual]
```

**Retorna si hubo cambio y si se alcanzó el estado final.**
Cuando retorna "ESTADO FINAL ALCANZADO", el agente debe:
1. Notificar al usuario con el mensaje relevante
2. Ejecutar `cerrar --id [id]`
3. Si hay agenda vinculada: `agenda desactivar id=[agenda_id]`

**Ejemplo:**
```
actualizar --id 3 --estado "Entregado" --descripcion "Entrega exitosa en la puerta" --fuente web
```

---

### vincular-agenda — Asociar agenda al seguimiento
```
vincular-agenda --id [seguimiento_id] --agenda-id [agenda_id]
```
Permite que `actualizar` incluya instrucciones para desactivar la agenda automáticamente al finalizar.

---

### cerrar — Cerrar manualmente
```
cerrar --id [id] --razon "[motivo]"
```

---

### resumen — Vista ejecutiva
```
resumen
```
Muestra conteo por tipo y los más recientemente actualizados.

---

## Flujo completo: desde un correo hasta el monitoreo automático

### Paso 1 — El agente lee un correo relevante

El agente lee un correo de Amazon, DHL, un banco, etc. e identifica que contiene una notificación de estado. Extrae:
- Empresa/remitente
- Tipo de notificación (envío, transacción, etc.)
- Número de referencia / tracking
- URL de seguimiento (si existe)
- Estado inicial mencionado

### Paso 2 — Crear el seguimiento
```
ejecutar_script_skill("seguimiento", "run.py",
  'agregar --tipo envio --titulo "Pedido Amazon #XXX" --empresa Amazon
   --referencia "1Z9999..." --url "https://..." --estado-final "Entregado"
   --chat-id [chat_id_del_usuario]')
```

### Paso 3 — Crear la agenda de monitoreo

Usar la herramienta `agenda` con el prompt sugerido por el skill.
Frecuencia recomendada:
- Envíos nacionales: cada 4 horas
- Envíos internacionales: cada 8 horas
- Transacciones bancarias: cada 2 horas
- Solicitudes/trámites: cada 24 horas

### Paso 4 — Vincular la agenda al seguimiento
```
ejecutar_script_skill("seguimiento", "run.py",
  "vincular-agenda --id [seg_id] --agenda-id [agenda_id]")
```

### Paso 5 — El sub-agente monitorea (cada ciclo de agenda)

El sub-agente en cada ciclo:
1. `ver --id [id]` para conocer estado actual y URL
2. Visita la URL con `browser_navegar` o busca correos nuevos con `gmail buscar`
3. Extrae el estado nuevo
4. `actualizar --id [id] --estado "[nuevo]" --descripcion "[detalle]" --fuente web`
5. Si retorna "ESTADO FINAL": notifica, cierra, desactiva agenda

---

## Detección automática en lectura de correos

Cuando el sub-agente lee correos periódicamente (agenda diaria de correos), debe evaluar si algún correo es una notificación de estado rastreable. Señales clave:

**Correos de envío:**
- Asunto contiene: "enviado", "en camino", "tu pedido", "shipment", "tracking"
- Remitente: amazon.com, dhl.com, fedex.com, ups.com, correos.com

**Correos de transacción:**
- Asunto contiene: "transferencia", "pago procesado", "débito", "transacción", "comprobante"
- Remitente: un banco, PayPal, fintech

**Correos de solicitud/trámite:**
- Asunto contiene: "solicitud recibida", "en revisión", "aprobación pendiente", "estatus"

Si se detecta uno, preguntar al usuario si desea activar el seguimiento,
o si el sub-agente tiene instrucción de activarlo automáticamente, proceder con el flujo completo.

---

## Notas importantes

- La BD se crea automáticamente en `skills/seguimiento/seguimiento.db`
- El campo `estado_final` es una palabra clave flexible (no exact match): "entregado" detecta "Entrega exitosa en tu domicilio"
- Si no hay URL, el monitoreo puede hacerse buscando correos con `gmail buscar` usando empresa + referencia como query
- Los seguimientos cerrados se conservan en la BD (útil para estadísticas futuras)
- Concurrencia segura: la BD usa WAL mode para acceso desde agente principal y sub-agente simultáneamente
