# Skill: gmail-reader

Lee y busca correos de Gmail via API OAuth2. Usa credenciales de `gmail_manager/`.

## Cuándo usar esta skill

- Leer los últimos correos del inbox
- Buscar correos con filtros (remitente, asunto, fecha, etc.)
- Obtener resumen de no leídos
- Ver el contenido completo de un correo por ID

**IMPORTANTE:** Esta skill se invoca SIEMPRE con `ejecutar_script_skill`, NO con import de Python.

## Cómo invocar

```
ejecutar_script_skill("gmail-reader", "run.py", "[subcomando] [args]")
```

---

## Subcomandos

### leer — Inbox reciente
```
ejecutar_script_skill("gmail-reader", "run.py", "leer")
ejecutar_script_skill("gmail-reader", "run.py", "leer --cantidad 20")
ejecutar_script_skill("gmail-reader", "run.py", "leer --cantidad 5 --cuerpo")
```

### buscar — Filtrar correos (sintaxis de Gmail)
```
ejecutar_script_skill("gmail-reader", "run.py", 'buscar --query "from:amazon.com"')
ejecutar_script_skill("gmail-reader", "run.py", 'buscar --query "subject:enviado after:2026/04/01"')
ejecutar_script_skill("gmail-reader", "run.py", 'buscar --query "from:banco is:unread" --cuerpo')
ejecutar_script_skill("gmail-reader", "run.py", 'buscar --query "tracking OR pedido OR shipment" --cantidad 5')
```

### resumen — Conteo no leídos + remitentes frecuentes
```
ejecutar_script_skill("gmail-reader", "run.py", "resumen")
```

### ver — Correo completo por ID
```
ejecutar_script_skill("gmail-reader", "run.py", "ver --id <message_id>")
```

### enviar — Enviar un correo
```
ejecutar_script_skill("gmail-reader", "run.py", 'enviar --para "destino@email.com" --asunto "Asunto aqui" --cuerpo "Texto del correo"')
```
El correo se envía desde la cuenta Gmail autenticada (rhayalcantara@gmail.com).
El cuerpo se convierte automáticamente a HTML con formato legible.

---

## Requisitos

- `gmail_manager/credentials.json` — credenciales OAuth2 de Google
- `gmail_manager/token.json` — token generado tras autorización

Si `token.json` no existe: ejecutar `python gmail_manager/main.py` primero.

---

## Sintaxis de query Gmail útil

| Query | Significado |
|-------|-------------|
| `from:amazon.com` | De Amazon |
| `subject:pedido` | Asunto contiene "pedido" |
| `is:unread` | No leídos |
| `after:2026/04/01` | Después del 1 abril 2026 |
| `label:inbox` | En inbox |
| `has:attachment` | Con adjunto |
| `from:dhl.com OR from:fedex.com` | De DHL o FedEx |

---

## Salida

Retorna JSON con lista de correos:
```json
[
  {
    "id": "18f3a...",
    "de": "auto-confirm@amazon.com",
    "asunto": "Tu pedido ha sido enviado",
    "fecha": "Thu, 24 Apr 2026 10:30:00 -0500",
    "snippet": "Tu pedido #123-456-789 fue enviado..."
  }
]
```

Con `--cuerpo` incluye campo `"cuerpo"` con el texto completo (hasta 3000 chars).
