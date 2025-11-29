import os
from openai import OpenAI
from dotenv import load_dotenv
from agent import Agent

load_dotenv()

# Configuración flexible del servidor de IA
api_base_url = os.getenv("API_BASE_URL", "https://api.openai.com/v1")
model_name = os.getenv("MODEL_NAME", "gpt-4")
api_key = os.getenv("OPENAI_API_KEY")

print("=" * 50)
print("Mi primer agente de IA")
print("=" * 50)
print(f"📡 Endpoint: {api_base_url}")
print(f"🤖 Modelo: {model_name}")
print("=" * 50)

# Inicializar cliente con configuración personalizada
# Para OpenRouter, necesitamos headers adicionales
if "openrouter.ai" in api_base_url:
    client = OpenAI(
        base_url=api_base_url,
        api_key=api_key,
        default_headers={
            "HTTP-Referer": "https://github.com/tu-usuario/agente-ia",  # Opcional pero recomendado
            "X-Title": "Mi Agente IA"  # Opcional pero recomendado
        }
    )
else:
    client = OpenAI(
        base_url=api_base_url,
        api_key=api_key
    )
agent = Agent()

def cmd_limpiar():
    agent.messages = [
        {"role": "system", "content": "Eres un asistente útil que habla español y eres muy conciso con tus respuestas,lee el archivo agent.py si existe"}
    ]
    print("🧹 Historial limpiado.")
    return True

def cmd_salir():
    print("Hasta luego!")
    return False

def cmd_inicializar():
    agent.messages = [{"role": "user", "content": "verifica si el archivo agent.md existe, si no existe crea lo y pide al usuario que rellene con las indicaciones para este proyecto"}]    
    print("Se crea el archivo agent.md.")
    return True
    
comandos = {
    "/limpiar": cmd_limpiar,
    "/salir": cmd_salir,
    "/exit": cmd_salir,
    "/bye": cmd_salir,
    "/init": cmd_inicializar
}

while True:
    user_input = input("Tú: ").strip()
    
    #Validaciones
    if not user_input:
        continue
    
    if user_input.lower() in comandos:
        if not comandos[user_input.lower()]():
            break
        continue
    
    #Agregar nuestro mensaje al historial
    agent.messages.append({"role": "user", "content": user_input})
    
    while True:
        try:
            response = client.responses.create(
                model=model_name,
                input=agent.messages,
                tools=agent.tools
            )

            called_tool = agent.process_response(response)

            #Si no se llamo herramienta, tenemos la respuesta final
            if not called_tool:
                break

        except Exception as e:
            print(f"\n⚠️  Error al comunicarse con el modelo: {type(e).__name__}")
            print(f"Detalles: {str(e)[:200]}...")
            print("\nPosibles soluciones:")
            print("  1. El contexto es muy largo - intenta reiniciar la conversación")
            print("  2. Reinicia el servidor en LM Studio")
            print("  3. Verifica que el modelo soporte function calling")

            # Remover el último mensaje del usuario para que no quede en historial
            if agent.messages and len(agent.messages) > 0:
                last_msg = agent.messages[-1]
                # Verificar si es un dict con role="user"
                if isinstance(last_msg, dict) and last_msg.get("role") == "user":
                    agent.messages.pop()

            break
        
        