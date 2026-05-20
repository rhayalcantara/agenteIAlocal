# Pendientes de Desarrollo

Actualizado: 2026-04-26

## Bugs activos

### Bug agenda: KeyError 'operacion'
El agente llama `agenda` con `{'listar': True}` pero el handler espera `args.pop("operacion")`. El LLM no esta pasando el campo `operacion` requerido.
- Archivo: `agente_core/agent.py:1067`
- Error: `KeyError: 'operacion'`
- Causa: el LLM genera args sin el campo obligatorio "operacion"
- Fix: validar que "operacion" exista y usar un default, o ajustar la descripcion del tool para que el LLM siempre lo incluya

## Monitor Hub (nuevo proyecto)
- Diseno listo en `design_monitor_hub.md`
- **Fase 1:** Refactorizar monitor actual como plugin + hub central
- **Fase 2:** Plugin WhatsApp (grupo SISTEMA RAY)
- **Fase 3:** Dashboard web con FastAPI
- **Fase 4:** Plugin Gmail + prioridades

## WhatsApp → Agente local
- Agente local guarde mensajes de SISTEMA RAY en .md automaticamente
- Pulir execute_bash (comillas en "SISTEMA RAY", esperar output completo)
- MCP server de WhatsApp (como el de Telegram)

## Agente local
- Skill buscar-noticias corregida, probar que el agente la invoque bien tras reinicio
- Verificar wiki muestre 4 paginas tras el fix
- Notificaciones cruzadas (WhatsApp urgente → Telegram)

## Gateway Anthropic-compatible para Claude Desktop
- PC Worker con modelos LLM (via VPN o red local)
- PC Gateway con endpoint `/v1/messages` (formato Anthropic) que traduce a `/v1/chat/completions` (OpenAI)
- Cloudflare Tunnel para HTTPS gratis (`cloudflared tunnel --url http://localhost:puerto`)
- Resultado: Claude Desktop conectado a modelos locales sin VPS ni dominio
- Costo: $0

## App Android — Interfaz directa con el agente
Dispositivos en la casa y guagua para comunicarse con el agente sin intermediarios (sin Telegram/WhatsApp).
- **Oir:** Microfono → STT (Whisper) → texto
- **Ver:** Camara → Vision (Qwen3.6) → descripcion para el LLM
- **Responder:** LLM genera respuesta → TTS → audio por el dispositivo
- Flujo: voz/imagen → gateway → agente → respuesta hablada
- Dispositivos: tablets/telefonos viejos como terminales fijas en cada area
- Tecnologias posibles: Flutter/Kotlin + WebSocket al agente, o PWA con Web Speech API
- Integracion con presencia: saber en que zona esta el usuario para contexto

## Claude Ranger — Comunicacion con instancia del servidor
- Flujo: Rhay + Claude local desarrollan → push al repo → avisan a Claude del servidor por Telegram → el actualiza, despliega y reporta
- La instancia de Claude en el servidor de Ranger necesita un bot de Telegram para recibir instrucciones nuestras
- El se encarga de: git pull, deploy, migrations, reportar resultado
- No atiende al equipo de Ranger directamente, solo recibe ordenes de nosotros

## Ideas futuras
- Dashboard centralizado con FastAPI para todos los monitores
- Agente local guarda conversaciones, Claude analiza bajo demanda
