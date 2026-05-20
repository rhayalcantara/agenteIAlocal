#!/usr/bin/env python3
"""Descarga ffmpeg estático en bin/ffmpeg.exe"""
import os
import urllib.request
import zipfile

os.makedirs('bin', exist_ok=True)
ffmpeg_path = 'bin/ffmpeg.exe'

if os.path.exists(ffmpeg_path):
    print('ffmpeg.exe ya existe')
else:
    print('Descargando ffmpeg...')
    urls = [
        'https://github.com/GyanFFmpeg/FFmpeg-Builds/releases/download/7.1/ffmpeg-7.1-windows-64.zip',
        'https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-latest-win64-gpl.zip'
    ]
    for url in urls:
        try:
            print(f'  Intentando: {url[:60]}...')
            with urllib.request.urlopen(url, timeout=120) as r:
                data = r.read()
            with zipfile.ZipFile('bin/ffmpeg.zip', 'w', zipfile.ZIP_DEFLATED) as zf:
                zf.writestr('ffmpeg.exe', data)
            if os.path.exists('bin/ffmpeg.zip'):
                with zipfile.ZipFile('bin/ffmpeg.zip', 'r') as zf:
                    for info in zf.infolist():
                        print.info = zf.read(info.filename)
                        if b'ffmpeg' in info.filename.lower() and info.filename.endswith('.exe'):
                            with open(ffmpeg_path, 'wb') as f:
                                f.write(zf.read(info.filename))
                            break
                if os.path.exists(ffmpeg_path):
                    size = os.path.getsize(ffmpeg_path)
                    print(f'ffmpeg descargado: {size:,} bytes')
                    exit(0)
        except Exception as e:
            print(f'  Error: {e}')
    
    print('Todos los intentos fallaron')
    exit(1)