import PyPDF2

def read_pdf(file_path):
    try:
        with open(file_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            text = ""
            for page in reader.pages:
                text += page.extract_text() + "\n"
            return text
    except Exception as e:
        return f"Error: {e}"

if __name__ == "__main mandato":
    import sys
    if len(sys.argv) > 1:
        print(read_pdf(sys.argv[1]))
    else:
        print("Please provide a PDF file path.")
