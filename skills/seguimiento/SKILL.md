# Skill: seguimiento

Tracking universal de procesos con cambio de estado en el tiempo.
Válido para: envíos, transacciones bancarias, reservas, solicitudes y cualquier proceso que avance por estados.

---

## INSTRUCCIÓN CRÍTICA PARA EL AGENTE

**CUANDO EL USUARIO PIDA ALGO RELACIONADO CON SEGUIMIENTOS, TÚ DEBES:**
1. Llamar a la herramienta `ejecutar_script_skill` INMEDIATAMENTE
2. NO explicar cómo se usa la herramienta
3. NO mostrar comandos al usuario
4. Ejecutar y reportar el resultado

**Parámetros correctos de la herramienta:**
- skill: `seguimiento`
- script: `run.py`
- args: el subcomando con sus argumentos

---

## Cuándo activar

- Usuario pregunta por un pedido, envío, paquete o tracking
- Usuario pregunta por el estado de una transacción bancaria
- Usuario quiere saber el estado de una reserva, cita o trámite
- Correo detectado con número de tracking o referencia rastreable

---

## Operaciones disponibles (args para ejecutar_script_skill)

### Listar seguimientos activos
args: `listar`
args: `listar --tipo envio`
args: `listar --todos`

### Ver detalle con historial
args: `ver --id 3`

### Registrar nuevo seguimiento
args: `agregar --tipo envio --titulo "Pedido Amazon" --empresa Amazon --referencia "TBA123" --estado-final "Entregado" --chat-id 5483766132`
args: `agregar --tipo envio --titulo "Pedido X" --empresa DHL --referencia "REF123" --email-notificar "correo@ejemplo.com"`

Solo `--tipo` y `--titulo` son obligatorios.

### Actualizar estado
args: `actualizar --id 3 --estado "En tránsito" --fuente web`
args: `actualizar --id 3 --estado "Entregado" --descripcion "Entrega exitosa" --fuente email`

### Vincular agenda de monitoreo
args: `vincular-agenda --id 3 --agenda-id 5`

### Cerrar seguimiento
args: `cerrar --id 3 --razon "Entregado"`

### Resumen ejecutivo
args: `resumen`

---

## Tipos de seguimiento

| tipo | Ejemplos |
|------|----------|
| envio | Amazon, DHL, FedEx, UPS, correo postal |
| transaccion | Transferencia bancaria, pago, reembolso |
| reserva | Cita médica, hotel, vuelo, restaurante |
| solicitud | VISA, seguro, crédito, documento oficial |
| otro | Cualquier proceso con estados progresivos |

---

## Flujo cuando el agente detecta un correo con tracking

1. Llama `listar` para verificar si ya existe ese seguimiento
2. Si NO existe: llama `agregar` con los datos del correo
3. Crea agenda de monitoreo con la herramienta `agenda`
4. Llama `vincular-agenda` con el ID del seguimiento y el ID de la agenda

## Ciclo de monitoreo automático (sub-agente de agenda)

1. Llama `ver --id X` para conocer estado actual y URL
2. Busca correos nuevos con gmail-reader o navega la URL de tracking
3. Si hay nuevo estado: llama `actualizar --id X --estado "..." --fuente web`
4. Si el resultado dice "ESTADO FINAL ALCANZADO": llama `cerrar --id X` y desactiva la agenda
5. Si no hay cambio: el resultado empieza con [SILENCIOSO] — propagar ese prefijo en la respuesta

## Notificación por email

Si el seguimiento tiene `email_notificar` configurado, el resultado de `actualizar`
incluye automáticamente la instrucción de envío. Ejecútala con `gmail-reader enviar`.

---

## Notas

- La BD se crea automáticamente en `skills/seguimiento/seguimiento.db`
- El campo `estado_final` hace matching flexible: "entregado" detecta "Entrega exitosa en tu domicilio"
- Los seguimientos cerrados se conservan (estadísticas futuras)
