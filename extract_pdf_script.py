import pdfplumber
import os

def extract_pdf_content(pdf_path):
    \"\"\"
    Extrae todo el texto de un archivo PDF usando pdfplumber.
    \"\"\"
    if not os.path.exists(pdf_path):
        return f"Error: El archivo '{pdf_path}' no existe."

    text_content = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for i, page in enumerate(pdf.pages):
                page_text = page.extract_text()
                if page_text:
                    text_content.append(f\"--- Página {i+1} ---\\n{page_text}\")
        
        return \"\\n\".join(text_content)
    except Exception as e:
        return f"Error al procesar el PDF: {str(e)}"

if __name__ == \"__main__\":
    # Reemplaza con la ruta de tu archivo PDF
    archivo_pdf = 'gmail_manager/downloads/3000775354_3_2026.PDF' 
    
    print(f\"\\n--- Iniciando extracción de: {archivo_pdf} ---\\n\")
    resultado = extract_pdf_content(archivo_pdf)
    print(resultado)
