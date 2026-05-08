#!/usr/bin/env python3
"""
generate_audio.py — Convierte los cuentos de texto a audio MP3
usando Google Cloud Text-to-Speech (Neural2 — tier gratuito 1M chars/mes).

Voz: femenina, cálida, Neural2. Perfecta para cuentos infantiles.

Prerequisitos:
    pip install google-cloud-texttospeech pydub
    export GOOGLE_APPLICATION_CREDENTIALS="path/to/service-account.json"

Uso:
    python generate_audio.py --input stories/es/luca_y_la_linterna_magica.txt
    python generate_audio.py --all   # convierte todos los .txt en stories/
"""

import argparse
import json
import os
import re
from pathlib import Path
from datetime import datetime

# ──────────────────────────────────────────────
# CONFIGURACIÓN DE VOCES POR IDIOMA
# Todas son Neural2 (alta calidad, incluidas en el tier gratuito)
# ──────────────────────────────────────────────

VOICE_CONFIG = {
    "es": {
        "language_code": "es-ES",
        "voice_name": "es-ES-Neural2-C",   # Mujer, cálida, española
        "speaking_rate": 0.90,              # Un poco más lento — ideal para dormir
        "pitch": -1.0,                      # Tono ligeramente bajo, relajante
    },
    "en": {
        "language_code": "en-GB",
        "voice_name": "en-GB-Neural2-C",   # Mujer, británica, suave
        "speaking_rate": 0.88,
        "pitch": -1.0,
    },
    "fr": {
        "language_code": "fr-FR",
        "voice_name": "fr-FR-Neural2-C",   # Mujer, francesa, musical
        "speaking_rate": 0.88,
        "pitch": -1.0,
    },
    "de": {
        "language_code": "de-DE",
        "voice_name": "de-DE-Neural2-C",   # Mujer, alemana, clara
        "speaking_rate": 0.87,
        "pitch": -1.0,
    },
    "zh": {
        "language_code": "cmn-CN",
        "voice_name": "cmn-CN-Neural2-D",  # Mujer, mandarín, suave
        "speaking_rate": 0.85,
        "pitch": -1.0,
    },
}

# Google TTS tiene límite de 5.000 caracteres por llamada — dividimos el texto
MAX_CHARS_PER_REQUEST = 4800

# ──────────────────────────────────────────────
# FUNCIONES
# ──────────────────────────────────────────────

def detect_language_from_path(file_path: Path) -> str:
    """Detecta el idioma a partir de la estructura de carpetas: stories/es/cuento.txt"""
    parts = file_path.parts
    for i, part in enumerate(parts):
        if part == "stories" and i + 1 < len(parts):
            lang = parts[i + 1]
            if lang in VOICE_CONFIG:
                return lang
    # Fallback: buscar en el nombre del directorio padre
    parent = file_path.parent.name
    if parent in VOICE_CONFIG:
        return parent
    return "es"  # default


def split_text_for_tts(text: str, max_chars: int = MAX_CHARS_PER_REQUEST) -> list:
    """
    Divide el texto en fragmentos respetando párrafos y puntos.
    Google TTS tiene límite de 5.000 chars por llamada.
    """
    # Limpiar markdown headers
    text = re.sub(r'^#+\s+', '', text, flags=re.MULTILINE)
    
    paragraphs = text.split('\n\n')
    chunks = []
    current_chunk = ""
    
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        
        if len(current_chunk) + len(para) + 2 <= max_chars:
            current_chunk += ("\n\n" if current_chunk else "") + para
        else:
            if current_chunk:
                chunks.append(current_chunk)
            # Si un párrafo solo es más largo que el límite, dividir por frases
            if len(para) > max_chars:
                sentences = re.split(r'(?<=[.!?])\s+', para)
                temp = ""
                for s in sentences:
                    if len(temp) + len(s) + 1 <= max_chars:
                        temp += (" " if temp else "") + s
                    else:
                        if temp:
                            chunks.append(temp)
                        temp = s
                if temp:
                    current_chunk = temp
                else:
                    current_chunk = ""
            else:
                current_chunk = para
    
    if current_chunk:
        chunks.append(current_chunk)
    
    return chunks


def text_to_audio_chunk(client, text: str, voice_cfg: dict) -> bytes:
    """Convierte un fragmento de texto a audio usando Google TTS."""
    from google.cloud import texttospeech
    
    synthesis_input = texttospeech.SynthesisInput(text=text)
    
    voice = texttospeech.VoiceSelectionParams(
        language_code=voice_cfg["language_code"],
        name=voice_cfg["voice_name"],
    )
    
    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3,
        speaking_rate=voice_cfg["speaking_rate"],
        pitch=voice_cfg["pitch"],
        effects_profile_id=["headphone-class-device"],  # Optimizado para auriculares/altavoces
    )
    
    response = client.synthesize_speech(
        input=synthesis_input,
        voice=voice,
        audio_config=audio_config,
    )
    
    return response.audio_content


def generate_audio(txt_path: Path, output_dir: str = "audio", lang: str = None) -> Path:
    """
    Genera el MP3 completo para un cuento.
    Divide el texto si es necesario y combina los fragmentos.
    """
    try:
        from google.cloud import texttospeech
        from pydub import AudioSegment
        import io
    except ImportError:
        print("  ❌ Instala las dependencias: pip install google-cloud-texttospeech pydub")
        raise
    
    # Detectar idioma
    if not lang:
        lang = detect_language_from_path(txt_path)
    
    voice_cfg = VOICE_CONFIG.get(lang, VOICE_CONFIG["es"])
    
    print(f"  🎙️  Sintetizando voz [{lang.upper()}]: {txt_path.name}")
    print(f"      Voz: {voice_cfg['voice_name']} | Velocidad: {voice_cfg['speaking_rate']}")
    
    # Leer texto
    with open(txt_path, "r", encoding="utf-8") as f:
        text = f.read()
    
    # Dividir en chunks
    chunks = split_text_for_tts(text)
    print(f"      Fragmentos: {len(chunks)} | Chars totales: {len(text):,}")
    
    # Inicializar cliente Google TTS
    client = texttospeech.TextToSpeechClient()
    
    # Generar audio por fragmentos
    audio_segments = []
    for i, chunk in enumerate(chunks, 1):
        print(f"      Procesando fragmento {i}/{len(chunks)} ({len(chunk)} chars)...")
        audio_data = text_to_audio_chunk(client, chunk, voice_cfg)
        segment = AudioSegment.from_mp3(io.BytesIO(audio_data))
        audio_segments.append(segment)
        
        # Pausa suave entre párrafos (0.8 seg de silencio)
        if i < len(chunks):
            pause = AudioSegment.silent(duration=800)
            audio_segments.append(pause)
    
    # Combinar todos los fragmentos
    print(f"      Combinando {len(audio_segments)} segmentos...")
    final_audio = audio_segments[0]
    for seg in audio_segments[1:]:
        final_audio += seg
    
    # Guardar MP3
    lang_audio_dir = Path(output_dir) / lang
    lang_audio_dir.mkdir(parents=True, exist_ok=True)
    
    stem = txt_path.stem
    mp3_path = lang_audio_dir / f"{stem}.mp3"
    
    final_audio.export(
        mp3_path,
        format="mp3",
        bitrate="192k",
        tags={
            "title": stem.replace("_", " ").title(),
            "artist": "Caye",
            "album": "Cuentos para dormir de Caye",
            "genre": "Children",
            "year": str(datetime.now().year),
        }
    )
    
    duration_min = len(final_audio) / 1000 / 60
    print(f"  ✅ Audio generado: {mp3_path} ({duration_min:.1f} min)")
    return mp3_path


def generate_all_audio(stories_dir: str = "stories", output_dir: str = "audio"):
    """Convierte todos los .txt en stories/ a MP3."""
    stories_path = Path(stories_dir)
    txt_files = list(stories_path.rglob("*.txt"))
    
    if not txt_files:
        print(f"  ⚠️  No se encontraron archivos .txt en {stories_dir}/")
        return
    
    print(f"  📚 Encontrados {len(txt_files)} cuentos para convertir")
    results = []
    
    for txt_file in txt_files:
        try:
            mp3_path = generate_audio(txt_file, output_dir)
            results.append({"txt": str(txt_file), "mp3": str(mp3_path), "ok": True})
        except Exception as e:
            print(f"  ❌ Error con {txt_file}: {e}")
            results.append({"txt": str(txt_file), "error": str(e), "ok": False})
    
    ok = sum(1 for r in results if r["ok"])
    print(f"\n  ✨ Completado: {ok}/{len(results)} audios generados en {output_dir}/")
    return results


# ──────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Convierte cuentos de texto a MP3 con Google Cloud TTS"
    )
    parser.add_argument("--input", help="Archivo .txt del cuento a convertir")
    parser.add_argument("--lang", choices=list(VOICE_CONFIG.keys()),
                        help="Idioma (auto-detectado si no se especifica)")
    parser.add_argument("--all", action="store_true",
                        help="Convierte todos los cuentos en stories/")
    parser.add_argument("--output-dir", default="audio",
                        help="Directorio de salida (default: audio/)")
    
    args = parser.parse_args()
    
    print("🎙️  Cuentos para dormir de Caye — Generador de audio")
    print("=" * 55)
    
    if args.all:
        generate_all_audio(output_dir=args.output_dir)
    elif args.input:
        generate_audio(Path(args.input), args.output_dir, args.lang)
    else:
        parser.print_help()
        print("\n💡 Prerequisitos:")
        print("   1. Activa Google Cloud TTS API en console.cloud.google.com")
        print("   2. Descarga el JSON de service account")
        print("   3. export GOOGLE_APPLICATION_CREDENTIALS='path/to/key.json'")
        print("   4. pip install google-cloud-texttospeech pydub")


if __name__ == "__main__":
    main()
