#!/usr/bin/env python3
"""
generate_audio.py — Convierte cuentos a MP3 usando ElevenLabs TTS.
Soporta múltiples voces: narradora + personajes distintos.

Coste: ~10.000 créditos gratis/mes (plan Free) = ~2-3 cuentos completos

Prerequisitos:
    pip install elevenlabs pydub
    set ELEVENLABS_API_KEY=sk_...

Formato del guión (.txt):
    El texto normal lo narra la narradora.
    Para asignar voz a un personaje, usa etiquetas:
        [PERSONAJE:nombre] Texto que dice el personaje.
    Ejemplo:
        La luna brillaba sobre el bosque.
        [PERSONAJE:caye] ¡Mira, Alvarito! ¡Una estrella fugaz!
        [PERSONAJE:alvarito] ¿Pedimos un deseo?

Uso:
    python generate_audio.py --input stories/es/caye_y_la_linterna_magica.txt
    python generate_audio.py --all
    python generate_audio.py --list-voices   # Ver voces disponibles
"""

import argparse
import os
import re
import time
from pathlib import Path

# ---------------------------------------------------------------------------
# CONFIGURACIÓN DE VOCES
# ---------------------------------------------------------------------------
NARRATOR_VOICE = {
    "es": "tXgbXPnsMpKXkuTgvE3h",  # Narrador ES — voz actualizada
    "en": "cgSgspJ2msm6clMCkdW9",  # Jessica — inglés
    "fr": "cgSgspJ2msm6clMCkdW9",  # Jessica — francés
    "de": "cgSgspJ2msm6clMCkdW9",  # Jessica — alemán
    "zh": "cgSgspJ2msm6clMCkdW9",  # Jessica — chino
}

# Voces por personaje
CHARACTER_VOICES = {
    "caye":      "M6VSsB443dZGsCW4RLDr",  # Caye — voz clonada real
    "alvarito":  "V7JiGnncIvaytoLoomdl",  # Alvarito — voz clonada real
    "hada":      "YDDaC9XKjODs7hY78qEW",  # Hada — español
    "dragon":    "z3kTTwYbQrmL7ckdGcJi",  # Dragón/Animales — español
    "bruja":     "M9RTtrzRACmbUzsEMq8p",  # Bruja — español
    "sabio":     "YKrm0N1EAM9Bw27j8kuD",  # Sabio — español
    "animal":    "z3kTTwYbQrmL7ckdGcJi",  # Animales — misma que dragón
    "personaje": "HMCmDsbKeaSZp5LMOYKR",  # Otros animales/personajes
    "nino":      "1tDEBGOo8EqEPApM49eJ",  # Otros niños — español
    "frances":   "Az8xj7Z0gQ5npNFesTsW",  # Personaje con acento francés
    # Añade más personajes aquí con su voice ID
}

# Modelo ElevenLabs — eleven_multilingual_v2 soporta español nativo
MODEL = "eleven_multilingual_v2"

# Configuración de voz (ajusta a tu gusto)
VOICE_SETTINGS = {
    "narrator": {"stability": 0.85, "similarity_boost": 0.75, "style": 0.0, "speed": 0.92},
    "character": {"stability": 0.60, "similarity_boost": 0.80, "style": 0.5, "speed": 1.0},
}

# ElevenLabs permite hasta ~5.000 chars por llamada
MAX_CHARS = 4500


# ---------------------------------------------------------------------------
# PARSEO DEL GUIÓN
# ---------------------------------------------------------------------------

def parse_script(text: str) -> list:
    """
    Parsea el guión y devuelve lista de segmentos:
    [{"speaker": "narrator"|"personaje", "text": "..."}]
    """
    # Limpiar markdown
    text = re.sub(r'^#+\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'\*+', '', text)

    segments = []
    lines = text.strip().split('\n')

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Detectar etiqueta de personaje: [PERSONAJE:nombre]
        match = re.match(r'\[PERSONAJE:(\w+)\]\s*(.*)', line, re.IGNORECASE)
        if match:
            character = match.group(1).lower()
            dialogue = match.group(2).strip()
            if dialogue:
                segments.append({"speaker": character, "text": dialogue})
        else:
            # Texto de narración — agrupar párrafos consecutivos
            if segments and segments[-1]["speaker"] == "narrator":
                segments[-1]["text"] += " " + line
            else:
                segments.append({"speaker": "narrator", "text": line})

    return segments


def split_long_segment(text: str) -> list:
    """Divide texto largo en fragmentos respetando frases."""
    if len(text) <= MAX_CHARS:
        return [text]

    sentences = re.split(r'(?<=[.!?])\s+', text)
    chunks, current = [], ""

    for sentence in sentences:
        if len(current) + len(sentence) + 1 <= MAX_CHARS:
            current += (" " if current else "") + sentence
        else:
            if current:
                chunks.append(current)
            current = sentence

    if current:
        chunks.append(current)

    return chunks


# ---------------------------------------------------------------------------
# GENERACIÓN DE AUDIO
# ---------------------------------------------------------------------------

def get_voice_id(speaker: str, lang: str = "es") -> str:
    """Devuelve el voice_id según el speaker."""
    if speaker == "narrator":
        return NARRATOR_VOICE.get(lang, NARRATOR_VOICE["es"])
    return CHARACTER_VOICES.get(speaker, NARRATOR_VOICE.get(lang, NARRATOR_VOICE["es"]))


def synthesize_segment(client, text: str, voice_id: str, is_character: bool = False) -> bytes:
    """Sintetiza un segmento de texto y devuelve bytes MP3."""
    settings_key = "character" if is_character else "narrator"
    s = VOICE_SETTINGS[settings_key]

    from elevenlabs import VoiceSettings

    audio = client.text_to_speech.convert(
        voice_id=voice_id,
        text=text,
        model_id=MODEL,
        voice_settings=VoiceSettings(
            stability=s["stability"],
            similarity_boost=s["similarity_boost"],
            style=s["style"],
            use_speaker_boost=True,
        ),
        output_format="mp3_44100_128",
    )

    # El cliente devuelve un generador — concatenar bytes
    return b"".join(audio)


def generate_audio(txt_path: Path, output_dir: str = "audio", lang: str = None) -> Path:
    from elevenlabs import ElevenLabs

    api_key = os.environ.get("ELEVENLABS_API_KEY")
    if not api_key:
        # Intentar leer desde archivo (igual que el resto del proyecto)
        key_file = Path(__file__).parent / "ElevenLabs Key"
        if key_file.exists():
            api_key = key_file.read_text(encoding="utf-8").strip()
        else:
            raise ValueError("❌ Falta ELEVENLABS_API_KEY — ejecuta set_keys.bat primero")

    client = ElevenLabs(api_key=api_key)

    if not lang:
        # Detectar idioma por carpeta (stories/es/, stories/en/, etc.)
        for part in txt_path.parts:
            if part in NARRATOR_VOICE:
                lang = part
                break
        lang = lang or "es"

    print(f"\n🎙️  Procesando: {txt_path.name} [{lang.upper()}]")
    print("=" * 55)

    with open(txt_path, "r", encoding="utf-8") as f:
        text = f.read()

    segments = parse_script(text)
    print(f"   Segmentos detectados: {len(segments)}")

    speakers = set(s["speaker"] for s in segments)
    print(f"   Personajes: {', '.join(speakers)}")

    audio_parts = []
    total_chars = 0

    for i, segment in enumerate(segments, 1):
        speaker = segment["speaker"]
        text_chunk = segment["text"]
        is_character = speaker != "narrator"

        voice_id = get_voice_id(speaker, lang)
        icon = "🗣️" if is_character else "📖"
        print(f"   {icon} [{i}/{len(segments)}] {speaker}: {text_chunk[:60]}...")

        # Dividir si es muy largo
        sub_chunks = split_long_segment(text_chunk)

        for sub in sub_chunks:
            total_chars += len(sub)
            try:
                audio_bytes = synthesize_segment(client, sub, voice_id, is_character)
                audio_parts.append(audio_bytes)
                # Pausa entre llamadas para no saturar la API
                time.sleep(0.3)
            except Exception as e:
                print(f"   ⚠️  Error en segmento {i}: {e}")
                time.sleep(2)  # Esperar más si hay error

    print(f"\n   Total caracteres procesados: {total_chars:,}")
    print(f"   Créditos ElevenLabs usados: ~{total_chars:,}")

    # Combinar todo el audio
    final_audio = b"".join(audio_parts)

    # Guardar
    lang_dir = Path(output_dir) / lang
    lang_dir.mkdir(parents=True, exist_ok=True)
    mp3_path = lang_dir / f"{txt_path.stem}.mp3"

    with open(mp3_path, "wb") as f:
        f.write(final_audio)

    size_mb = len(final_audio) / 1024 / 1024
    print(f"\n✅ Audio guardado: {mp3_path} ({size_mb:.1f} MB)")
    return mp3_path


def generate_all_audio(stories_dir: str = "stories", output_dir: str = "audio"):
    txt_files = list(Path(stories_dir).rglob("*.txt"))
    if not txt_files:
        print(f"⚠️  No hay archivos .txt en {stories_dir}/")
        return

    print(f"📚 {len(txt_files)} cuentos encontrados")
    for txt_file in txt_files:
        try:
            generate_audio(txt_file, output_dir)
        except Exception as e:
            print(f"❌ Error con {txt_file.name}: {e}")


def list_voices():
    """Lista las voces disponibles en tu cuenta ElevenLabs."""
    from elevenlabs import ElevenLabs

    api_key = os.environ.get("ELEVENLABS_API_KEY")
    client = ElevenLabs(api_key=api_key)

    voices = client.voices.get_all()
    print("\n🎤 Voces disponibles en tu cuenta ElevenLabs:")
    print("=" * 55)
    for v in voices.voices:
        labels = v.labels or {}
        lang = labels.get("language", "?")
        gender = labels.get("gender", "?")
        print(f"  {v.name:<25} ID: {v.voice_id}  [{lang} / {gender}]")


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Genera audio MP3 con ElevenLabs TTS")
    parser.add_argument("--input", help="Archivo .txt del cuento")
    parser.add_argument("--lang", choices=list(NARRATOR_VOICE.keys()), help="Idioma")
    parser.add_argument("--all", action="store_true", help="Convierte todos los cuentos")
    parser.add_argument("--output-dir", default="audio")
    parser.add_argument("--list-voices", action="store_true", help="Lista voces disponibles")
    args = parser.parse_args()

    print("🎙️  Cuentos Infantiles — Generador de audio ElevenLabs")
    print("=" * 55)

    if args.list_voices:
        list_voices()
    elif args.all:
        generate_all_audio(output_dir=args.output_dir)
    elif args.input:
        generate_audio(Path(args.input), args.output_dir, args.lang)
    else:
        parser.print_help()
        print("\n💡 Ejemplos:")
        print("   python generate_audio.py --input stories/es/caye_y_la_linterna_magica.txt")
        print("   python generate_audio.py --list-voices")
        print("   python generate_audio.py --all")
        print("\n📝 Formato del guión:")
        print("   Texto normal → narradora")
        print("   [PERSONAJE:caye] Diálogo → voz de Caye")
        print("   [PERSONAJE:alvarito] Diálogo → voz de Alvarito")


if __name__ == "__main__":
    main()
