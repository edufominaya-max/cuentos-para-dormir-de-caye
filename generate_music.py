#!/usr/bin/env python3
"""
generate_music.py — Genera canciones y sintonía para los cuentos via Suno API.

Genera:
  1. Sintonía INTRO  — orquestal Disney, 10-15s, con voz ElevenLabs encima
  2. Canciones del cuento — una por [CANCION:titulo] en el guión
  3. Sintonía OUTRO  — igual que intro

Prerequisitos:
    pip install requests elevenlabs
    Variables: APIPASS_KEY, ELEVENLABS_API_KEY

Uso:
    python generate_music.py --jingle          # Solo genera la sintonía
    python generate_music.py --story stories/es/mi_cuento.json
    python generate_music.py --all             # Todas las canciones pendientes
"""

import argparse
import json
import os
import re
import time
from pathlib import Path

# ---------------------------------------------------------------------------
# CONFIGURACIÓN
# ---------------------------------------------------------------------------

SUNO_GENERATE = "https://api.apipass.dev/api/v1/jobs/createTask"
SUNO_FETCH    = "https://api.apipass.dev/api/v1/jobs/recordInfo"

# Sintonía — orquestal mágico tipo Disney, 10-15 segundos
JINGLE_PROMPT = (
    "magical orchestral children's theme, Disney style, whimsical and warm, "
    "strings harp glockenspiel, playful fairy tale mood, bedtime lullaby energy, "
    "10 seconds intro jingle, fade in fade out, instrumental only, no vocals"
)

JINGLE_STYLE = "magical orchestral Disney children's bedtime"

# Voz ElevenLabs para la sintonía (Papi — narrador principal)
JINGLE_VOICE_ID = "vq02QcE85JB44tzQhGG5"
JINGLE_TEXT = "Cuentos infantiles: Las aventuras de Caye y Alvarito"

# Estilo base para canciones del cuento
SONG_BASE_STYLE = (
    "children's song, warm and playful, acoustic guitar and glockenspiel, "
    "simple melody easy to sing, bedtime story style, soft and magical"
)

# Regex para slugificar nombres de archivo — definido fuera de f-strings
_SLUG_RE = re.compile(r'[^\w]')


# ---------------------------------------------------------------------------
# SUNO — generación de audio
# ---------------------------------------------------------------------------

def slugify(text: str, max_len: int = 30) -> str:
    """Convierte texto en slug seguro para nombres de archivo."""
    return _SLUG_RE.sub('_', text.lower())[:max_len]


def generate_suno_track(prompt: str, title: str, style: str,
                        instrumental: bool = True, lyrics: str = "",
                        output_path: Path = None) -> Path:
    """Genera un track con Suno via apipass.dev"""
    import requests

    api_key = os.environ.get("APIPASS_KEY")
    if not api_key:
        raise ValueError("❌ Falta APIPASS_KEY en variables de entorno")

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
        "User-Agent": "Mozilla/5.0"
    }

    payload = {
        "model": "suno/generate",
        "input": {
            "model_version": "V5",
            "customMode": True,
            "style": style,
            "title": title,
            "instrumental": instrumental,
            "prompt": prompt if instrumental else lyrics + "\n\n[VOICE STYLE: warm children's singer, soft and playful]",
            "weirdnessConstraint": 0.2,
            "styleWeight": 0.8,
        }
    }

    print(f"   🎵 Enviando a Suno: '{title}'...")
    response = requests.post(SUNO_GENERATE, headers=headers, json=payload, timeout=30)

    if response.status_code != 200:
        raise Exception(f"Suno error {response.status_code}: {response.text}")

    task_id = response.json().get("data", {}).get("taskId", "")
    print(f"   Task ID: {task_id}")

    # Polling hasta que esté listo (max 5 minutos)
    for i in range(60):
        time.sleep(5)
        fetch = requests.get(f"{SUNO_FETCH}?taskId={task_id}", headers=headers, timeout=30)
        if fetch.status_code != 200:
            continue

        data  = fetch.json()
        state = data.get("data", {}).get("state", "")
        print(f"   Estado [{i+1}/60]: {state}")

        if state == "success":
            result_json = data.get("data", {}).get("resultJson", {})
            audio_url = ""
            for key in ["resultUrls", "data"]:
                val = result_json.get(key, [])
                if val:
                    audio_url = val[0] if isinstance(val[0], str) else val[0].get("audio_url", "")
                    break
            if not audio_url:
                audio_url = result_json.get("audio_url", "")
            if not audio_url:
                raise Exception("No audio URL en respuesta Suno")

            audio_data = requests.get(audio_url, timeout=60).content

            if not output_path:
                output_path = Path("music") / f"{slugify(title)}.mp3"

            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "wb") as f:
                f.write(audio_data)

            print(f"   ✅ Audio guardado: {output_path}")
            return output_path

        elif state == "fail":
            raise Exception("Suno devolvió estado 'fail'")

    raise Exception("Timeout esperando respuesta de Suno")


# ---------------------------------------------------------------------------
# ELEVENLABS — voz para la sintonía
# ---------------------------------------------------------------------------

def generate_jingle_voice(text: str, output_path: Path) -> Path:
    """Genera la voz de la sintonía con ElevenLabs."""
    from elevenlabs import ElevenLabs, VoiceSettings

    api_key = os.environ.get("ELEVENLABS_API_KEY")
    if not api_key:
        key_file = Path(__file__).parent / "ElevenLabs Key.txt"
        if key_file.exists():
            api_key = key_file.read_text(encoding="utf-8").strip()
        else:
            raise ValueError("❌ Falta ELEVENLABS_API_KEY")

    client = ElevenLabs(api_key=api_key)

    audio = client.text_to_speech.convert(
        voice_id=JINGLE_VOICE_ID,
        text=text,
        model_id="eleven_multilingual_v2",
        voice_settings=VoiceSettings(
            stability=0.8,
            similarity_boost=0.8,
            style=0.4,
            use_speaker_boost=True,
        ),
        output_format="mp3_44100_128",
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "wb") as f:
        f.write(b"".join(audio))

    print(f"   ✅ Voz sintonía guardada: {output_path}")
    return output_path


# ---------------------------------------------------------------------------
# MEZCLA — voz sobre música (via FFmpeg)
# ---------------------------------------------------------------------------

def mix_voice_over_music(music_path: Path, voice_path: Path, output_path: Path,
                          voice_volume: float = 1.0, music_volume: float = 0.3) -> Path:
    """Mezcla la voz de la sintonía sobre la música con FFmpeg."""
    import subprocess

    cmd = [
        "ffmpeg", "-y",
        "-i", str(music_path),
        "-i", str(voice_path),
        "-filter_complex",
        f"[0:a]volume={music_volume}[music];"
        f"[1:a]volume={voice_volume},adelay=1500|1500[voice];"
        f"[music][voice]amix=inputs=2:duration=shortest[out]",
        "-map", "[out]",
        "-c:a", "libmp3lame", "-q:a", "2",
        str(output_path)
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise Exception(f"FFmpeg error: {result.stderr}")

    print(f"   ✅ Sintonía mezclada: {output_path}")
    return output_path


# ---------------------------------------------------------------------------
# GENERAR SINTONÍA COMPLETA
# ---------------------------------------------------------------------------

def generate_jingle(output_dir: str = "music/jingle", force: bool = False) -> dict:
    """
    Genera la sintonía completa (intro y outro):
    - música orquestal Suno
    - voz ElevenLabs encima
    - mezcla final con FFmpeg
    """
    jingle_dir = Path(output_dir)
    jingle_dir.mkdir(parents=True, exist_ok=True)

    intro_path = jingle_dir / "intro.mp3"
    outro_path = jingle_dir / "outro.mp3"

    if intro_path.exists() and outro_path.exists() and not force:
        print(f"   ℹ️  Sintonía ya existe en {jingle_dir}/ — usa --force para regenerar")
        return {"intro": str(intro_path), "outro": str(outro_path)}

    print("\n🎵 Generando sintonía...")
    print("=" * 55)

    # 1. Música instrumental con Suno
    music_path = jingle_dir / "jingle_music.mp3"
    if not music_path.exists() or force:
        generate_suno_track(
            prompt=JINGLE_PROMPT,
            title="Cuentos Infantiles Sintonía",
            style=JINGLE_STYLE,
            instrumental=True,
            output_path=music_path,
        )
    else:
        print(f"   ℹ️  Música ya existe: {music_path}")

    # 2. Voz con ElevenLabs
    voice_path = jingle_dir / "jingle_voice.mp3"
    if not voice_path.exists() or force:
        generate_jingle_voice(JINGLE_TEXT, voice_path)
    else:
        print(f"   ℹ️  Voz ya existe: {voice_path}")

    # 3. Mezclar intro
    mix_voice_over_music(music_path, voice_path, intro_path)

    # 4. Outro = misma mezcla (podría ser diferente en el futuro)
    import shutil
    shutil.copy2(str(intro_path), str(outro_path))
    print(f"   ✅ Outro copiado: {outro_path}")

    return {"intro": str(intro_path), "outro": str(outro_path)}


# ---------------------------------------------------------------------------
# GENERAR CANCIONES DEL CUENTO
# ---------------------------------------------------------------------------

def generate_story_songs(story_json_path: Path, output_dir: str = "music") -> list:
    """
    Lee el JSON del cuento, extrae las canciones marcadas con [CANCION:titulo]
    en el .txt correspondiente y las genera con Suno.
    """
    with open(story_json_path, "r", encoding="utf-8") as f:
        meta = json.load(f)

    lang  = meta.get("lang", "es")
    title = meta.get("title", "cuento")
    txt_file = Path(meta.get("txt_file", ""))

    if not txt_file.exists():
        raise FileNotFoundError(f"No encontrado: {txt_file}")

    with open(txt_file, "r", encoding="utf-8") as f:
        text = f.read()

    # Buscar bloques [CANCION:titulo]...[/CANCION]
    song_blocks = re.findall(
        r'\[CANCION:([^\]]+)\](.*?)\[/CANCION\]',
        text, re.DOTALL | re.IGNORECASE
    )

    if not song_blocks:
        print(f"   ℹ️  No hay canciones en {txt_file.name}")
        return []

    print(f"\n🎵 Generando {len(song_blocks)} canciones para '{title}'...")
    results = []

    slug = slugify(title)
    song_dir = Path(output_dir) / lang / slug
    song_dir.mkdir(parents=True, exist_ok=True)

    for i, (song_title, lyrics_raw) in enumerate(song_blocks, 1):
        song_title = song_title.strip()
        lyrics = lyrics_raw.strip()

        print(f"\n   🎶 [{i}/{len(song_blocks)}] '{song_title}'")

        song_slug = slugify(song_title)
        output_path = song_dir / f"song_{i:02d}_{song_slug}.mp3"

        if output_path.exists():
            print(f"   ℹ️  Ya existe: {output_path}")
            results.append({"title": song_title, "path": str(output_path)})
            continue

        try:
            has_lyrics = len(lyrics) > 20 and lyrics != "[INSTRUMENTAL]"

            generate_suno_track(
                prompt=SONG_BASE_STYLE + f", song titled '{song_title}', for children bedtime story",
                title=song_title,
                style="children's magical bedtime song",
                instrumental=not has_lyrics,
                lyrics=lyrics if has_lyrics else "",
                output_path=output_path,
            )
            results.append({"title": song_title, "path": str(output_path)})
            time.sleep(10)

        except Exception as e:
            print(f"   ❌ Error generando '{song_title}': {e}")
            results.append({"title": song_title, "path": None, "error": str(e)})

    return results


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Genera música para cuentos infantiles")
    parser.add_argument("--jingle",  action="store_true", help="Genera/regenera la sintonía")
    parser.add_argument("--force",   action="store_true", help="Fuerza regeneración aunque exista")
    parser.add_argument("--story",   help="Ruta al .json del cuento para generar sus canciones")
    parser.add_argument("--all",     action="store_true", help="Genera canciones de todos los cuentos")
    parser.add_argument("--output-dir", default="music")
    args = parser.parse_args()

    print("🎵 Cuentos Infantiles — Generador de música")
    print("=" * 55)

    if args.jingle:
        result = generate_jingle(
            output_dir=str(Path(args.output_dir) / "jingle"),
            force=args.force
        )
        print(f"\n✅ Sintonía lista:")
        print(f"   Intro: {result['intro']}")
        print(f"   Outro: {result['outro']}")

    elif args.story:
        results = generate_story_songs(Path(args.story), args.output_dir)
        print(f"\n✅ {len(results)} canciones generadas")

    elif args.all:
        json_files = [f for f in Path("stories").rglob("*.json")
                      if not f.name.endswith("_cover.json")]
        for jf in json_files:
            try:
                generate_story_songs(jf, args.output_dir)
            except Exception as e:
                print(f"❌ Error con {jf}: {e}")

    else:
        parser.print_help()
        print("\n💡 Ejemplos:")
        print("   python generate_music.py --jingle")
        print("   python generate_music.py --story stories/es/caye_y_la_linterna_magica.json")
        print("   python generate_music.py --all")


if __name__ == "__main__":
    main()
