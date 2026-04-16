import yt_dlp
import os

def download_youtube_video(url):
    """
    Descarga un video de YouTube usando la mejor calidad disponible.
    """
    # Configuración profesional para yt-dlp
    ydl_opts = {
        'format': 'bestvideo+bestaudio/best',  # Busca la mejor combinación de video y audio
        'outtmpl': '%(title)s.%(ext)s',        # El nombre del archivo será el título del video
        'noplaylist': True,                    # Si es un link a playlist, descarga solo el video actual
        'postprocessors': [{                   # Procesa para asegurar que el formato sea compatible (ej. mp4)
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
    }

    print(f"[*] Iniciando proceso de descarga para: {url}")
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Extraer información primero para mostrar el título
            info = ydl.extract_info(url, download=False)
            print(f"[+] Video detectado: {info.get('title', 'Desconocido')}")
            
            # Iniciar descarga real
            ydl.download([url])
            print("\n[✓] ¡Descarga completada con éxito!")
            
    except Exception as e:
        print(f"\n[!] Error crítico durante la descarga: {e}")

if __name__ == "__main__":
    # URL que proporcionaste
    video_url = "https://www.youtube.com/watch?v=2X0TyEklQ5s"
    
    # Verificar si hay conexión o si el link es válido
    download_youtube_video(video_url)
