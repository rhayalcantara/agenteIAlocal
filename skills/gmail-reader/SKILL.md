# Gmail Reader Skill

Esta skill permite buscar y leer correos electrónicos de Gmail utilizando la API de Google. 

## Funcionalidades
- **Listar correos no leídos**: Por defecto, busca los últimos mensajes que no han sido leídos (`is:unread`).
- **Filtrar por etiqueta**: Permite especificar una etiqueta (ej. "Work", "Invoices") para limitar la búsqueda usando el argumento `--label`.

## Uso

### 1. Listar los últimos correos no leídos
Para obtener una lista de los mensajes más recientes que no has abierto:
```bash
python3 gmail_manager/main.py
```

### 2. Listar correos no leídos de una etiqueta específica
Si quieres buscar solo los correos sin leer dentro de una categoría (por ejemplo, "Trabajo"):
```bash
python3 gmail_manager/main.py --label "Work"
```

## Requisitos
- Tener el archivo `credentials.json` en la raíz del proyecto.
- Tener configurado el entorno con las librerías necesarias (`google-api-python-client`, `google-auth-oauthlib`, etc.).

## Ejemplo de Salida
```text
ID: 18f2a... | Subject: Reunión Mañana | From: jefe@empresa.com
ID: 17c9b... | Subject: Factura Pendiente | From: contabilidad@servicio.com
```