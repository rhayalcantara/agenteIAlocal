import os
import subprocess

class Tool:
    def __init__(self):
        pass

    def execute_command(self, command):
        """Ejecuta un comando en la terminal y devuelve la salida."""
        try:
            # Combinamos stdout y stderr para no perder detalles de errores
            result = subprocess.run(
                command, 
                shell=True, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.STDOUT, 
                text=True, 
                timeout=60  # Timeout de seguridad de 60 segundos
            )
            output = result.stdout
            print("=== Salida del comando ===")
            print(output)
            return output
            #return result.stdout
        except subprocess.TimeoutExpired:
            return "Error: El comando excedió el tiempo límite de ejecución."
        except Exception as e:
            return f"Error al ejecutar comando: {str(e)}"

    def read_file(self, path,encodings='utf-8'):
        """Lee el contenido de un archivo."""
        print ("   ReadFile:"+path)
        try:
            with open(path, 'r', encoding=encodings) as file:
                content = file.read()
            print ("✓  ReadFile:"+path)
            return content
        except Exception as e:
            return str(e)

    def edit_file(self, path, prev_text, new_text):
        """Edita un archivo reemplazando prev_text por new_text. Crea el archivo si no existe."""
        try:
            # Si el archivo no existe, lo crea
            if not os.path.exists(path):
                print ("   Add File:"+path)
                # Crear directorios solo si la ruta contiene subdirectorios
                dir_path = os.path.dirname(path)
                if dir_path:
                    os.makedirs(dir_path, exist_ok=True)
                with open(path, 'w', encoding='utf-8') as file:
                    file.write(new_text)
                #agregar una verificacion de que el archivo se creo
                if os.path.exists(path):
                    print (" ✓  Added File:"+path)
                    return "Archivo creado."
                else:
                    print ("Added File:"+path+ " fallo")
                    return "Added File:"+path+ " fallo"
            # Si existe, reemplaza el texto
            print ("   edit File:"+path)
            with open(path, 'r', encoding='utf-8') as file:
                content = file.read()                
            if prev_text not in content:
                return "Texto a reemplazar no encontrado."
            
            updated_content = content.replace(prev_text, new_text)
            
            with open(path, 'w', encoding='utf-8') as file:
                file.write(updated_content)
            print (" ✓  edited File:"+path)
            return "Archivo actualizado."
        except Exception as e:
            return str(e)

    def list_files_in_dir(self, directory="."):
        """Lista los archivos en un directorio dado."""
        try:
            files = [f for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))]
            return files
        except Exception as e:
            return str(e)