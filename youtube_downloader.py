import yt_dlp
import os

def download_youtube_video(url):
    """
    Descarga un video de YouTube en la mejor calidad disponible.
    """
    # Configuración de la carpeta de descargas (Carpeta 'downloads' en el mismo directorio)
    download_path = os    os.path.join(os.getcwd(), 'downloads')
    if not os.path.exists(download_path):
        os.makedirs(download_path)

    # Configuración de yt-dlp
    ydl_opts = {
        'format': 'bestvideo+bestaudio/best',  # Busca la mejor calidad de video y audio
        'outtmpl': f'{download_path}/%(title)s.%(ext)s',  # Nombre del archivo basado en el título
        'noplaylist': True,  # Descargar solo el video, no la lista de reproducción completa
        'quiet': False,      # Mostrar progreso en consola
    }

    print(f"--- Iniciando descarga de: {url} ---")
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Extraer información para mostrar el título antes de descargar
            info = ydl.extract_info(url, download=False)
            print(f"Título detectado: {info.get('title', 'Desconocido')}")
            
            # Realizar la descarga
            ydl.download([url])
            
        print("\n✅ ¡Descarga completada con éxito!")
        print(f"📂 El video se encuentra en: {download_path}")

    except Exception as e:
        print(f"\n❌ Error al intentar descargar el video: {e}")

if __name__ == "__main__":
    # URL proporcionada por el usuario
    video_url = "https://www.youtube.com/watch?v=2X0TyEklQ5s"
    
    download_youtube_video(video_url)
