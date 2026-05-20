import os, subprocess
from deep_translator import GoogleTranslator
import whisper
from gtts import gTTS
from moviepy.editor import VideoFileClip, AudioFileClip

def process_video(url):
    v_file = "original.mp4"
    a_en = "audio_en.mp3"
    a_es = "audio_es.mp3"
    v_final = "doblado_es.mp4"
    
    print("▶ Paso 1: Descargando...")
    subprocess.run(['yt-dlp', '-f', 'best[ext=mp4]', '-o', v_file, url], check=True)

    print("▶ Paso 2: Audio EN...")
    subprocess.run(['ffmpeg', '-i', v_file, '-vn', '-acodec', 'libmp3lame', a_en, '-y'], check=True)

    print("▶ Paso 3: Transcribiendo...")
    model = whisper.load_model("base")
    res = model.transcribe(a_en)
    
    print("▶ Paso 4: Traduciendo...")
    txt_es = GoogleTranslator(source='en', target='es').translate(res['text'])

    print("▶ Paso 5: Voz ES...")
    gTTS(txt_es, lang='es').save(a_es)

    print("▶ Paso 6: Montando...")
    v_clip = VideoFileClip(v_file)
    a_clip = AudioFileClip(a_es).set_duration(min(v_clip.duration, AudioFileClip(a_es).duration))
    v_clip.set_audio(a_clip).write_videofile(v_final, codec='libx264', audio_codec='aac')
    print(f"✅ Finalizado: {v_final}")

if __name__ == "__main__":
    process_video("https://www.youtube.com/watch?v=f9LlXkvQg4E")
