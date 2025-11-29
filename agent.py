import os
import json
import subprocess
from tools import Tool

iatools = Tool()

class Agent:
    
    def __init__(self):
        self.setup_tools()
        system_message_content = "Eres un asistente útil que habla español y eres muy conciso con tus respuestas."
        
        # Intentar leer agent.md
        agent_md_path = "C:\\Proyectos\\agenteIAlocal\\agent.md" # Asumimos que está en el mismo directorio
        if os.path.exists(agent_md_path):
            try:
                with open(agent_md_path, "r", encoding="utf-8") as f:
                    agent_md_content = f.read()
                system_message_content = agent_md_content
                print(f"✅ Configuración cargada desde {agent_md_path}")
            except Exception as e:
                print(f"Advertencia: No se pudo leer {agent_md_path}: {e}. Usando mensaje predeterminado.")
        else:
            print(f"Advertencia: El archivo {agent_md_path} no fue encontrado. Usando mensaje predeterminado.")

        self.messages = [
            {"role": "system", "content": system_message_content}
        ]
            
    def setup_tools(self):
        self.tools = [
            {
                "type": "function",
                "name": "list_files_in_dir",
                "description": "Lista los archivos que existen en un directorio dado (por defecto es el directorio actual)",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "directory": {
                            "type": "string",
                            "description": "Directorio para listar (opcional). Por defecto es el directorio actual"
                        }
                    },
                    "required": []
                }
            },
            {
                "type": "function",
                "name": "read_file",
                "description": "Lee el contenido de un archivo en una ruta especificada",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "La ruta del archivo a leer"
                        },
                          "encodings": {
                            "type": "string",
                            "description": "El tipo de encoding para leer el archivo"
                        }
                    },
                    "required": ["path"]
                }
            },
            {
                "type": "function",
                "name": "edit_file",
                "description": "Edita el contenido de un archivo reemplazando prev_text por new_text. Crea el archivo si no existe.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "La ruta del archivo a editar"
                        },
                        "prev_text": {
                            "type": "string",
                            "description": "El texto que se va a buscar para reemplazar (puede ser vacío para archivos nuevos)"
                        },
                        "new_text": {
                            "type": "string",
                            "description": "El texto que reemplazará a prev_text (o el texto para un archivo nuevo)"
                        }
                    },
                    "required": ["path", "new_text"]
                }
            },
            {
                "type": "function",
                "name": "execute_command",
                "description": "Ejecuta un comando en la terminal (cmd en Windows)",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "command": {
                            "type": "string",
                            "description": "Comando a ejecutar como cadena de texto"
                        }
                    },
                    "required": ["command"]
                }
            }
        ]
      
    def process_response(self, response):
        #True = si llama a una funcion. False = No hubo llamado.

        message = response.output
        # Almacenar mensaje del asistente en el historial
        self.messages += response.output

        # Verificar si hay llamadas a herramientascontent
        for output in response.output:
            if output.type == "function_call":
                fn_name = output.name
                args = json.loads(output.arguments)

                print(f"  - El modelo considera llamar a la herramienta {fn_name}")
                print(f"  - Argumentos: {args}")

                if fn_name == "list_files_in_dir":
                    result = iatools.list_files_in_dir(**args)
                elif fn_name == "read_file":
                    result = iatools.read_file(**args)
                elif fn_name == "edit_file":
                    result = iatools.edit_file(**args)
                elif fn_name == "execute_command":
                    result = iatools.execute_command(**args)
                else:
                    result = f"Herramienta desconocida: {fn_name}"

                print(f"el resultado de la herramienta es: {result}")

                # Agregar resultado de la herramienta al historial
                #Agregar a la memoria la respuesta del llamado
                self.messages.append({
                    "type": "function_call_output",
                    "call_id": output.call_id,
                    "output": json.dumps({
                        #Así lo dejé en el video. Creo que queda mejor
                        #dejarlo como 'result', al aplicar ahora a las
                        #3 herramientas
                        "files": result
                    })
                })
                return True
        # Si no hay tool calls, mostrar la respuesta del asistente
            elif output.type == "message":
                #print(f"Asistente: {output.content}")
                reply = "\n".join(part.text for part in output.content)
                print(f"Asistente: {reply}")

        return False
