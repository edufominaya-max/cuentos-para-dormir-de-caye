#!/usr/bin/env python3
"""
mix_audio.py — Mezcla el audio final del cuento:
  INTRO (sintonía) + NARRACIÓN/DIÁLOGOS + CANCIONES + OUTRO (sintonía)
"""

import argparse
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path

JINGLE_DIR  = Path("music/jingle")
INTRO_PATH  = JINGLE_DIR / "intro.mp3"
OUTRO_PATH  = JINGLE_DIR / "outro.mp3"

SILENCE_AFTER_INTRO = 1000
SILENCE_BEFORE_SONG = 1500
SILENCE_AFTER_SONG  = 1500

_SLUG_RE = re.compile(r'[^\w]')


def check_ffmpeg():
    result = subprocess.run(["ffmpeg", "-version"], capture_output=True)
    if result.returncode != 0:
        raise EnvironmentError("❌ FFmpeg no está instalado.")


def slugify(text: str, max_len: int = 50) -> str:
    return _SLUG_RE.sub('_', text.lower())[:max_len]


def get_duration(path: Path) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        capture_output=True, text=True
    )
    try:
        return float(result.stdout.strip())
    except Exception:
        return 0.0


def generate_silence(duration_ms: int, output_path: Path):
    duration_s = duration_ms / 1000
    result = subprocess.run([
        "ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
        "-t", str(duration_s), "-c:a", "libmp3lame", "-q:a", "2",
        str(output_path)
    ], capture_output=True, text=True)
    if result.returncode != 0:
        raise Exception(f"Error generando silencio: {result.stderr}")


def concatenate_mp3s(file_list: list, output_path: Path):
    """Concatena MP3s usando rutas absolutas para evitar problemas con caracteres especiales."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Escribir lista con rutas absolutas y escapado correcto
    list_file = output_path.parent / "_concat_list.txt"
    with open(list_file, "w", encoding="utf-8") as f:
        for mp3 in file_list:
            abs_path = str(Path(mp3).resolve())
            # FFmpeg concat format: escapar comillas simples
            abs_path = abs_path.replace("\\", "/")
            f.write(f"file '{abs_path}'\n")

    result = subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", str(list_file),
        "-c:a", "libmp3lame", "-q:a", "2", "-ar", "44100", "-ac", "2",
        str(output_path.resolve())
    ], capture_output=True, text=True)

    list_file.unlink(missing_ok=True)

    if result.returncode != 0:
        raise Exception(f"FFmpeg concat error:\n{result.stderr[-500:]}")


def mix_episode(story_json_path: Path,
                audio_dir: str = "audio",
                music_dir: str = "music",
                output_dir: str = "final") -> Path:
    check_ffmpeg()

    with open(story_json_path, "r", encoding="utf-8") as f:
        meta = json.load(f)

    lang  = meta.get("lang", "es")
    title = meta.get("title", "cuento")
    txt_file = Path(meta.get("txt_file", ""))

    print(f"\n🎚️  Mezclando: '{title}' [{lang.upper()}]")
    print("=" * 55)

    has_jingle = INTRO_PATH.exists() and OUTRO_PATH.exists()
    if not has_jingle:
        print(f"   ⚠️  No existe sintonía — se generará sin intro/outro")

    # Usar narración directa (audio_sfx desactivado hasta fix)
    narration_path = Path(audio_dir) / lang / f"{txt_file.stem}.mp3"
    if not narration_path.exists():
        print(f"   ❌ No encontrada narración: {narration_path}")
        return None
    print(f"   🎙️ Narración: {narration_path.name}")

    # Directorio de salida
    output_path = Path(output_dir) / lang / f"{slugify(title)}_final.mp3"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp = Path(tmp_dir)
        parts = []

        # 1. INTRO
        if has_jingle:
            parts.append(str(INTRO_PATH.resolve()))
            sil = tmp / "sil_intro.mp3"
            generate_silence(SILENCE_AFTER_INTRO, sil)
            parts.append(str(sil))
            print(f"   ✅ Intro añadida")

        # 2. NARRACIÓN
        parts.append(str(narration_path.resolve()))
        dur = get_duration(narration_path)
        print(f"   ✅ Narración añadida ({dur:.0f}s)")

        # 3. CANCIONES
        story_slug = slugify(title, 30)
        song_dir = Path(music_dir) / lang / story_slug
        if song_dir.exists():
            songs = sorted(song_dir.glob("song_*.mp3"))
            for song_path in songs:
                sil_before = tmp / f"sil_b_{song_path.stem}.mp3"
                sil_after  = tmp / f"sil_a_{song_path.stem}.mp3"
                generate_silence(SILENCE_BEFORE_SONG, sil_before)
                generate_silence(SILENCE_AFTER_SONG, sil_after)
                parts.append(str(sil_before))
                parts.append(str(song_path.resolve()))
                parts.append(str(sil_after))
                print(f"   ✅ Canción añadida: {song_path.name}")

        # 4. OUTRO
        if has_jingle:
            sil_outro = tmp / "sil_outro.mp3"
            generate_silence(SILENCE_AFTER_INTRO, sil_outro)
            parts.append(str(sil_outro))
            parts.append(str(OUTRO_PATH.resolve()))
            print(f"   ✅ Outro añadida")

        print(f"\n   🎚️  Concatenando {len(parts)} segmentos...")
        concatenate_mp3s(parts, output_path)

    if not output_path.exists():
        raise FileNotFoundError(f"FFmpeg no generó el archivo: {output_path}")

    dur_final = get_duration(output_path)
    size_mb   = output_path.stat().st_size / 1024 / 1024
    print(f"\n✅ Episodio final: {output_path}")
    print(f"   Duración: {dur_final/60:.1f} min | Tamaño: {size_mb:.1f} MB")
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


if __name__ == "__main__":
    main()
