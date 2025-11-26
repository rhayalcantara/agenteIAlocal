# Tu primer Agente de IA
Este repositorio es el código para el video "Tu primer agente de IA" en el canal Ringa Tech

## Configuración
Para ejecutar el proyecto es necesario:
- Descargar el repositorio
- Opcional: Crea un ambiente virtual
- Instala las dependencias ejecutando
	- ```  pip install -r requirements.txt ```
- Crea un archivo llamado ```.env``` (puedes usar `.env.example` como plantilla)

### Opción 1: Usar OpenAI API
En el archivo `.env` agrega:
```
API_BASE_URL=https://api.openai.com/v1
MODEL_NAME=gpt-4
OPENAI_API_KEY=sk-tu-clave-aqui
```

### Opción 2: Usar LM Studio (Modelo Local)
1. Descarga e instala [LM Studio](https://lmstudio.ai/)
2. Descarga y carga un modelo compatible (por ejemplo: Mistral, Llama, etc.)
3. En LM Studio, ve a la pestaña "Local Server" y haz clic en "Start Server"
4. Anota la URL del servidor (por defecto: `http://localhost:1234`)
5. En el archivo `.env` agrega:
```
API_BASE_URL=http://localhost:1234/v1
MODEL_NAME=nombre-del-modelo-en-lm-studio
OPENAI_API_KEY=not-needed
```

**Para usar LM Studio desde otra computadora en la red:**
1. En la computadora con LM Studio, obtén la IP local (Windows: `ipconfig`, Linux/Mac: `ifconfig`)
2. Inicia el servidor en LM Studio
3. En el archivo `.env` de la computadora cliente usa:
```
API_BASE_URL=http://[IP-DEL-SERVIDOR]:1234/v1
MODEL_NAME=nombre-del-modelo
OPENAI_API_KEY=not-needed
```
Ejemplo: `API_BASE_URL=http://192.168.1.100:1234/v1`

## Ejecución
- Activar el ambiente virtual
- Ejecutar ```python main.py```
- El programa mostrará la configuración activa (endpoint y modelo)
- Para salir, escribe: `salir`, `exit`, `bye`, o `sayonara`

## Solución de Problemas

### LM Studio no responde
- Verifica que el servidor esté corriendo en LM Studio (pestaña "Local Server")
- Confirma que el puerto sea el correcto (por defecto 1234)
- Si usas IP de red, verifica que no haya firewall bloqueando el puerto

### Error de conexión
- Verifica que la URL en `.env` sea correcta y termine en `/v1`
- Para localhost: `http://localhost:1234/v1`
- Para red: `http://[IP]:1234/v1`

### El modelo no soporta herramientas (function calling)
- No todos los modelos locales soportan llamadas a funciones
- Modelos recomendados que soportan function calling:
  - Mistral 7B Instruct
  - Llama 3.1 (8B o superior)
  - Qwen 2.5

### Variables de entorno no se cargan
- Asegúrate de que el archivo se llame exactamente `.env` (sin extensión adicional)
- Verifica que esté en la raíz del proyecto
- En Windows, asegúrate de ver extensiones de archivo para evitar `.env.txt`

## Agradecimientos

El proyecto está basado libremente en la publicación de Thorsten Ball en [Ampcode.com](https://ampcode.com/how-to-build-an-agent)