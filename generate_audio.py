#!/usr/bin/env python3
"""
generate_audio.py — Convierte cuentos a MP3 usando OpenAI TTS.
Voz: nova (femenina, cálida, expresiva) — mucho mejor que Google TTS.

Coste: ~$0.015 por cuento completo (~1.500 palabras)

Prerequisitos:
    pip install openai
    set OPENAI_API_KEY=sk-...

Uso:
    python generate_audio.py --input stories\es\caye_y_la_linterna_magica.txt
    python generate_audio.py --all
"""

import argparse
import os
import re
from pathlib import Path

# Voz por idioma — todas femeninas y cálidas
VOICE_CONFIG = {
    "es": "nova",      # Cálida, expresiva — perfecta para español
    "en": "nova",      # Igual de buena en inglés
    "fr": "nova",      # Funciona bien en francés
    "de": "nova",      # Alemán
    "zh": "shimmer",   # Shimmer suena mejor en chino
}

# OpenAI TTS tiene límite de 4.096 caracteres por llamada
MAX_CHARS = 4000


def detect_lang(file_path: Path) -> str:
    for part in file_path.parts:
        if part in VOICE_CONFIG:
            return part
    return "es"


def split_text(text: str) -> list:
    """Divide el texto en fragmentos respetando párrafos."""
    # Limpiar markdown
    text = re.sub(r'^#+\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'\*+', '', text)

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


def generate_audio(txt_path: Path, output_dir: str = "audio", lang: str = None) -> Path:
    from openai import OpenAI

    if not lang:
        lang = detect_lang(txt_path)

    voice = VOICE_CONFIG.get(lang, "nova")

    print(f"  🎙️  Sintetizando [{lang.upper()}]: {txt_path.name}")
    print(f"      Voz: OpenAI {voice}")

    with open(txt_path, "r", encoding="utf-8") as f:
        text = f.read()

    chunks = split_text(text)
    print(f"      Fragmentos: {len(chunks)} | Chars totales: {len(text):,}")

    client = OpenAI()
    audio_chunks = []

    for i, chunk in enumerate(chunks, 1):
        print(f"      Procesando fragmento {i}/{len(chunks)}...")

        response = client.audio.speech.create(
            model="tts-1-hd",     # Alta calidad
            voice=voice,
            input=chunk,
            response_format="mp3",
            speed=0.92,           # Ligeramente más lento — ideal para dormir
        )

        audio_chunks.append(response.content)

    # Combinar todos los chunks en un solo MP3
    final_audio = b"".join(audio_chunks)

    # Guardar
    lang_dir = Path(output_dir) / lang
    lang_dir.mkdir(parents=True, exist_ok=True)

    mp3_path = lang_dir / f"{txt_path.stem}.mp3"
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
            print(f"  ❌ Error con {txt_file.name}: {e}")


def main():
    parser = argparse.ArgumentParser(description="Genera audio MP3 con OpenAI TTS")
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
        print("\n💡 Ejemplo:")
        print('   python generate_audio.py --input stories\\es\\caye_y_la_linterna_magica.txt')


if __name__ == "__main__":
    main()
