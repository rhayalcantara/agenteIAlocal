"""
Pipeline: YouTube → MP4 → MP3 → Transcripción (Whisper) → Traducción → TTS (gTTS) → MP4 español
Uso: python pipeline.py <URL_YOUTUBE>
"""
import sys
import os
import subprocess

def run(cmd, desc=""):
    print(f"\n▶ {desc or cmd}")
    result = subprocess.run(cmd, shell=True, text=True,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    print(result.stdout[-2000:] if result.stdout else "")
    return result.returncode == 0, result.stdout

def main():
    if len(sys.argv) < 2:
        print("Uso: python pipeline.py <URL_YOUTUBE>")
        sys.exit(1)

    url = sys.argv[1]
    base = "yt_video"

    # 1. Descargar video
    ok, _ = run(
        f'yt-dlp -f "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best" '
        f'-o "{base}.mp4" "{url}"',
        "Descargando video..."
    )
    if not ok:
        print("ERROR: No se pudo descargar el video."); sys.exit(1)

    # 2. Extraer audio
    run(f'ffmpeg -y -i "{base}.mp4" -vn -acodec libmp3lame -ar 44100 -ac 2 "{base}.mp3"',
        "Extrayendo audio...")

    # 3. Transcribir con Whisper
    run(f'whisper "{base}.mp3" --model base --language English --output_format txt '
        f'--output_dir .', "Transcribiendo con Whisper...")

    txt_file = f"{base}.txt"
    if not os.path.exists(txt_file):
        print("ERROR: No se generó el archivo de transcripción."); sys.exit(1)

    with open(txt_file, "r", encoding="utf-8") as f:
        texto_en = f.read()
    print(f"\n📝 Transcripción ({len(texto_en)} chars):\n{texto_en[:500]}...")

    # 4. Traducir (el agente LLM hace la traducción — aquí dejamos el texto para que lo procese)
    traduccion_file = f"{base}_es.txt"
    print(f"\n⚠️  Traducción pendiente — el agente debe traducir {txt_file} y guardar en {traduccion_file}")
    print("Transcripción en inglés lista para traducir.")

if __name__ == "__main__":
    main()
