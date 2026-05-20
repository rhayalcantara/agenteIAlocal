#!/usr/bin/env python3
"""
Doblador de video local: transcripcion y doblaje de video a espanol.
Usa yt-dlp para extraer audio, Whisper para transcripcion,
Google Translate y gTTS para doblaje.
"""

import asyncio
import os
import subprocess
import sys
import tempfile
from pathlib import Path

# Add project dir to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)

try:
    import whisper
except ImportError:
    print("Instalando whisper...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "whisper", "-q"])
    import whisper

try:
    from deep_translator import GoogleTranslator
except ImportError:
    print("Instalando deep-translator...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "deep-translator", "-q"])
    from deep_translator import GoogleTranslator

try:
    from gtts import gTTS