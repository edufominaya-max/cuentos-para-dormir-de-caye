#!/usr/bin/env python3
"""
mix_audio.py — Mezcla el audio final del cuento:
  INTRO (sintonía) + NARRACIÓN/DIÁLOGOS + CANCIONES + OUTRO (sintonía)

Prerequisitos:
    ffmpeg instalado en el sistema (https://ffmpeg.org)
    pip install pydub

Uso:
    python mix_audio.py --story stories/es/caye_y_la_linterna_magica.json
    python mix_audio.py --all
"""

import argparse
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path


# ---------------------------------------------------------------------------
# CONFIGURACIÓN
# ---------------------------------------------------------------------------

JINGLE_DIR   = Path("music/jingle")
INTRO_PATH   = JINGLE_DIR / "intro.mp3"
OUTRO_PATH   = JINGLE_DIR / "outro.mp3"

# Silencio entre segmentos (milisegundos)
SILENCE_BETWEEN_SEGMENTS = 500   # 0.5s entre párrafos
SILENCE_BEFORE_SONG      = 1500  # 1.5s antes de una canción
SILENCE_AFTER_SONG       = 1500  # 1.5s después de una canción
SILENCE_AFTER_INTRO      = 1000  # 1s después de la sintonía


# ---------------------------------------------------------------------------
# UTILIDADES FFmpeg
# ---------------------------------------------------------------------------

def check_ffmpeg():
    result = subprocess.run(["ffmpeg", "-version"], capture_output=True)
    if result.returncode != 0:
        raise EnvironmentError("❌ FFmpeg no está instalado. Descárgalo en https://ffmpeg.org")


def get_duration(path: Path) -> float:
    """Devuelve la duración en segundos de un MP3."""
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        capture_output=True, text=True
    )
    try:
        return float(result.stdout.strip())
    except:
        return 0.0


def generate_silence(duration_ms: int, output_path: Path):
    """Genera un archivo MP3 de silencio."""
    duration_s = duration_ms / 1000
    subprocess.run([
        "ffmpeg", "-y", "-f", "lavfi", "-i", f"anullsrc=r=44100:cl=stereo",
        "-t", str(duration_s), "-c:a", "libmp3lame", "-q:a", "2",
        str(output_path)
    ], capture_output=True)


def concatenate_mp3s(file_list: list, output_path: Path):
    """Concatena una lista de MP3s en un solo archivo."""
    # Crear archivo de lista para FFmpeg
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        for mp3 in file_list:
            f.write(f"file '{mp3}'\n")
        list_file = f.name

    subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", list_file, "-c", "copy", str(output_path)
    ], capture_output=True)

    os.unlink(list_file)


def add_background_music(narration_path: Path, music_path: Path,
                          output_path: Path, music_volume: float = 0.08):
    """Añade música de fondo suave bajo la narración."""
    subprocess.run([
        "ffmpeg", "-y",
        "-i", str(narration_path),
        "-i", str(music_path),
        "-filter_complex",
        f"[1:a]volume={music_volume},aloop=loop=-1:size=44100*300[bg];"
        f"[0:a][bg]amix=inputs=2:duration=first:weights=1 {music_volume}[out]",
        "-map", "[out]",
        "-c:a", "libmp3lame", "-q:a", "2",
        str(output_path)
    ], capture_output=True)


# ---------------------------------------------------------------------------
# PARSEO DEL GUIÓN PARA MEZCLA
# ---------------------------------------------------------------------------

def parse_mix_script(txt_path: Path, audio_dir: Path, music_dir: Path) -> list:
    """
    Lee el guión y devuelve lista ordenada de segmentos de audio:
    [{"type": "narration"|"song"|"silence", "path": Path, "duration_ms": int}]
    """
    with open(txt_path, "r", encoding="utf-8") as f:
        text = f.read()

    segments = []
    lang = None
    for part in txt_path.parts:
        if part in ["es", "en", "fr", "de", "zh"]:
            lang = part
            break
    lang = lang or "es"

    # Audio de narración generado por ElevenLabs
    narration_path = audio_dir / lang / f"{txt_path.stem}.mp3"
    if narration_path.exists():
        segments.append({"type": "narration", "path": narration_path})
    else:
        print(f"   ⚠️  No encontrado audio de narración: {narration_path}")

    # Canciones — buscar archivos generados por generate_music.py
    story_slug = re.sub(r'[^\w]', '_', txt_path.stem.lower())[:30]
    song_pattern = music_dir / lang / story_slug

    song_blocks = re.findall(
        r'\[CANCION:([^\]]+)\]',
        text, re.IGNORECASE
    )

    for i, song_title in enumerate(song_blocks, 1):
        song_slug = re.sub(r'[^\w]', '_', song_title.strip().lower())[:30]
        song_path = song_pattern / f"song_{i:02d}_{song_slug}.mp3"

        if song_path.exists():
            segments.append({"type": "song", "path": song_path, "title": song_title.strip()})
        else:
            print(f"   ⚠️  No encontrada canción: {song_path}")

    return segments


# ---------------------------------------------------------------------------
# MEZCLA FINAL
# ---------------------------------------------------------------------------

def mix_episode(story_json_path: Path,
                audio_dir: str = "audio",
                music_dir: str = "music",
                output_dir: str = "final",
                add_bg_music: bool = False) -> Path:
    """
    Mezcla el episodio completo:
    INTRO → SILENCIO → NARRACIÓN → CANCIONES (intercaladas) → SILENCIO → OUTRO
    """
    check_ffmpeg()

    with open(story_json_path, "r", encoding="utf-8") as f:
        meta = json.load(f)

    lang  = meta.get("lang", "es")
    title = meta.get("title", "cuento")
    txt_file = Path(meta.get("txt_file", ""))

    print(f"\n🎚️  Mezclando: '{title}' [{lang.upper()}]")
    print("=" * 55)

    # Verificar sintonía
    if not INTRO_PATH.exists():
        print(f"   ⚠️  No existe sintonía. Ejecuta: python generate_music.py --jingle")
        has_jingle = False
    else:
        has_jingle = True

    # Directorio temporal para fragmentos
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp = Path(tmp_dir)
        parts = []

        # 1. INTRO
        if has_jingle:
            parts.append(str(INTRO_PATH))
            sil = tmp / "sil_intro.mp3"
            generate_silence(SILENCE_AFTER_INTRO, sil)
            parts.append(str(sil))
            print(f"   ✅ Intro añadida")

        # 2. NARRACIÓN PRINCIPAL
        narration_path = Path(audio_dir) / lang / f"{txt_file.stem}.mp3"
        if narration_path.exists():
            parts.append(str(narration_path))
            print(f"   ✅ Narración añadida ({get_duration(narration_path):.0f}s)")
        else:
            print(f"   ❌ No encontrada narración: {narration_path}")
            return None

        # 3. CANCIONES (al final de la narración, antes del outro)
        story_slug = re.sub(r'[^\w]', '_', title.lower())[:30]
        song_dir = Path(music_dir) / lang / story_slug

        if song_dir.exists():
            songs = sorted(song_dir.glob("song_*.mp3"))
            for song_path in songs:
                sil_before = tmp / f"sil_before_{song_path.stem}.mp3"
                sil_after  = tmp / f"sil_after_{song_path.stem}.mp3"
                generate_silence(SILENCE_BEFORE_SONG, sil_before)
                generate_silence(SILENCE_AFTER_SONG, sil_after)
                parts.append(str(sil_before))
                parts.append(str(song_path))
                parts.append(str(sil_after))
                print(f"   ✅ Canción añadida: {song_path.name}")

        # 4. OUTRO
        if has_jingle:
            sil_outro = tmp / "sil_outro.mp3"
            generate_silence(SILENCE_AFTER_INTRO, sil_outro)
            parts.append(str(sil_outro))
            parts.append(str(OUTRO_PATH))
            print(f"   ✅ Outro añadida")

        # 5. CONCATENAR TODO
        slug = re.sub(r'[^\w]', '_', title.lower())[:50]
        lang_out_dir = Path(output_dir) / lang
        lang_out_dir.mkdir(parents=True, exist_ok=True)
        output_path = lang_out_dir / f"{slug}_final.mp3"

        print(f"\n   🎚️  Concatenando {len(parts)} segmentos...")
        concatenate_mp3s(parts, output_path)

    duration = get_duration(output_path)
    size_mb  = output_path.stat().st_size / 1024 / 1024
    print(f"\n✅ Episodio final: {output_path}")
    print(f"   Duración: {duration/60:.1f} min | Tamaño: {size_mb:.1f} MB")

    return output_path


def mix_all(audio_dir: str = "audio", music_dir: str = "music", output_dir: str = "final"):
    json_files = [f for f in Path("stories").rglob("*.json")
                  if not f.name.endswith("_cover.json")]
    if not json_files:
        print("⚠️  No hay .json de cuentos en stories/")
        return

    print(f"📚 {len(json_files)} episodios a mezclar")
    for jf in json_files:
        try:
            mix_episode(jf, audio_dir, music_dir, output_dir)
        except Exception as e:
            print(f"❌ Error con {jf}: {e}")


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Mezcla audio final de cuentos")
    parser.add_argument("--story",      help="Ruta al .json del cuento")
    parser.add_argument("--all",        action="store_true")
    parser.add_argument("--audio-dir",  default="audio")
    parser.add_argument("--music-dir",  default="music")
    parser.add_argument("--output-dir", default="final")
    args = parser.parse_args()

    print("🎚️  Cuentos Infantiles — Mezclador de audio")
    print("=" * 55)

    if args.all:
        mix_all(args.audio_dir, args.music_dir, args.output_dir)
    elif args.story:
        mix_episode(Path(args.story), args.audio_dir, args.music_dir, args.output_dir)
    else:
        parser.print_help()
        print("\n💡 Ejemplos:")
        print("   python mix_audio.py --story stories/es/caye_y_la_linterna_magica.json")
        print("   python mix_audio.py --all")
        print("\n⚠️  Requiere FFmpeg instalado: https://ffmpeg.org")


if __name__ == "__main__":
    main()
