#!/usr/bin/env python3
"""
generate_audio.py — Convierte cuentos a MP3 usando Google Cloud TTS.
Version sin pydub — compatible con Python 3.14+

Prerequisitos:
    pip install google-cloud-texttospeech
    set GOOGLE_APPLICATION_CREDENTIALS=C:\cuentos\google-credentials.json

Uso:
    python generate_audio.py --input stories\es\caye_y_la_linterna_magica.txt
    python generate_audio.py --all
"""

import argparse
import io
import json
import os
import re
import struct
import wave
from datetime import datetime
from pathlib import Path

VOICE_CONFIG = {
    "es": {"language_code": "es-ES", "voice_name": "es-ES-Neural2-C", "speaking_rate": 0.90, "pitch": -1.0},
    "en": {"language_code": "en-GB", "voice_name": "en-GB-Neural2-C", "speaking_rate": 0.88, "pitch": -1.0},
    "fr": {"language_code": "fr-FR", "voice_name": "fr-FR-Neural2-C", "speaking_rate": 0.88, "pitch": -1.0},
    "de": {"language_code": "de-DE", "voice_name": "de-DE-Neural2-C", "speaking_rate": 0.87, "pitch": -1.0},
    "zh": {"language_code": "cmn-CN", "voice_name": "cmn-CN-Neural2-D", "speaking_rate": 0.85, "pitch": -1.0},
}

MAX_CHARS = 4800


def detect_lang(file_path: Path) -> str:
    for part in file_path.parts:
        if part in VOICE_CONFIG:
            return part
    return "es"


def split_text(text: str) -> list:
    text = re.sub(r'^#+\s+', '', text, flags=re.MULTILINE)
    paragraphs = text.split('\n\n')
    chunks, current = [], ""
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        if len(current) + len(para) + 2 <= MAX_CHARS:
            current += ("\n\n" if current else "") + para
        else:
            if current:
                chunks.append(current)
            current = para
    if current:
        chunks.append(current)
    return chunks


def combine_mp3_chunks(chunks_data: list) -> bytes:
    """Combina múltiples chunks de MP3 concatenándolos directamente."""
    return b"".join(chunks_data)


def generate_audio(txt_path: Path, output_dir: str = "audio", lang: str = None) -> Path:
    from google.cloud import texttospeech

    if not lang:
        lang = detect_lang(txt_path)

    voice_cfg = VOICE_CONFIG.get(lang, VOICE_CONFIG["es"])

    print(f"  🎙️  Sintetizando [{lang.upper()}]: {txt_path.name}")
    print(f"      Voz: {voice_cfg['voice_name']}")

    with open(txt_path, "r", encoding="utf-8") as f:
        text = f.read()

    chunks = split_text(text)
    print(f"      Fragmentos: {len(chunks)} | Chars totales: {len(text):,}")

    client = texttospeech.TextToSpeechClient()
    audio_chunks = []

    for i, chunk in enumerate(chunks, 1):
        print(f"      Procesando fragmento {i}/{len(chunks)}...")

        synthesis_input = texttospeech.SynthesisInput(text=chunk)
        voice = texttospeech.VoiceSelectionParams(
            language_code=voice_cfg["language_code"],
            name=voice_cfg["voice_name"],
        )
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3,
            speaking_rate=voice_cfg["speaking_rate"],
            pitch=voice_cfg["pitch"],
        )

        response = client.synthesize_speech(
            input=synthesis_input,
            voice=voice,
            audio_config=audio_config,
        )
        audio_chunks.append(response.audio_content)

    # Combinar chunks
    final_audio = combine_mp3_chunks(audio_chunks)

    # Guardar MP3
    lang_dir = Path(output_dir) / lang
    lang_dir.mkdir(parents=True, exist_ok=True)

    stem = txt_path.stem
    mp3_path = lang_dir / f"{stem}.mp3"

    with open(mp3_path, "wb") as f:
        f.write(final_audio)

    size_mb = len(final_audio) / 1024 / 1024
    print(f"  ✅ Audio guardado: {mp3_path} ({size_mb:.1f} MB)")
    return mp3_path


def generate_all_audio(stories_dir: str = "stories", output_dir: str = "audio"):
    txt_files = list(Path(stories_dir).rglob("*.txt"))
    if not txt_files:
        print(f"  ⚠️  No hay archivos .txt en {stories_dir}/")
        return

    print(f"  📚 {len(txt_files)} cuentos encontrados")
    for txt_file in txt_files:
        try:
            generate_audio(txt_file, output_dir)
        except Exception as e:
            print(f"  ❌ Error con {txt_file}: {e}")


def main():
    parser = argparse.ArgumentParser(description="Genera audio MP3 con Google TTS")
    parser.add_argument("--input", help="Archivo .txt del cuento")
    parser.add_argument("--lang", choices=list(VOICE_CONFIG.keys()))
    parser.add_argument("--all", action="store_true", help="Convierte todos los cuentos")
    parser.add_argument("--output-dir", default="audio")
    args = parser.parse_args()

    print("🎙️  Las aventuras de Caye y Alvarito — Generador de audio")
    print("=" * 55)

    if args.all:
        generate_all_audio(output_dir=args.output_dir)
    elif args.input:
        generate_audio(Path(args.input), args.output_dir, args.lang)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
