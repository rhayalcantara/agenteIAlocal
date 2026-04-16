import fitz  # PyMuPDF
import os

def analyze_pdf(pdf_path):
    """
    Analiza un PDF para determinar si es texto o imagen.
    Retorna el texto extraído o una indicación de que requiere OCR (imagen).
    """
    if not os.path.exists(pdf_path):
        return "Error: El archivo no existe."

    try:
        doc = fitz.open(pdf_path)
        full_text = ""
        contains_images_only = True
        
        for page in doc:
            page_text = page.get_text().strip()
            if page_text:
                full_text += page_text + "\n"
                contains_images_only = False
        
        doc.close()

        if contains_images_only:
            return "IMAGE_MODE"
        else:
            return f"TEXT_MODE\n\n{full_text}"

    except Exception as e:
        return f"Error al procesar el PDF: {str(e)}"

def call_llm_vision(pdf_path):
    """
    Placeholder para llamar a un LLM con capacidades de visión (ej. GPT-4o o Claude 3.5 Sonnet).
    En una implementación real, aquí convertirías las páginas a imagen y las enviarías.
    """
    print(f"--- [Simulación] Enviando {pdf_path} a LLM Vision ---")
    return "[Texto extraído por el LLM tras procesar la imagen del PDF]"

def main(file_path):
    result = analyze_pdf(file_path)

    if result == "IMAGE_MODE":
        print("Resultado: El PDF es una imagen (o escaneo sin capa de texto).")
        # Aquí llamaríamos al LLM
        llm_output = call_llm_vision(file_path)
        print(f"Respuesta del LLM:\n{llm_output}")
    elif result.startswith("TEXT_MODE"):
        print("Resultado: El PDF contiene texto seleccionable.")
        print(f"Contenido extraído:\n{result.replace('TEXT_MODE', '').strip()}")
    else:
        print(f"Error: {result}")

if __name__ == "__main__":
    # Reemplaza con la ruta de tu archivo PDF para probar
    test_pdf = "documento_prueba.pdf" 
    
    # Crear un PDF de prueba rápido si no existe (solo para demostración)
    if not os.path.exists(test_pdf):
        print("Creando un PDF de prueba con texto...")
        doc_test = fitz.open()
        page = doc_test.new_page()
        page.insert_text((50, 50), "Hola, esto es un PDF con texto real.")
        doc_test.save(test_pdf)
        doc_test.close()

    main(test_pdf)
