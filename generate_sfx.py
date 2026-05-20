#!/usr/bin/env python3
"""
generate_sfx.py — Descarga efectos de sonido de Freesound y los inserta en el timeline.

Prerequisitos:
    pip install requests
    FREESOUND_API_KEY en variables de entorno o secrets de GitHub

Etiquetas en el guión:
    [EFECTO:bosque_noche]    → sonido de bosque nocturno
    [EFECTO:rama_crujido]    → rama que cruje
    [EFECTO:trueno_suave]    → trueno lejano
    [EFECTO:magia]           → sonido mágico
    [EFECTO:viento]          → viento suave
    [EFECTO:agua_rio]        → río o arroyo
    [EFECTO:pasos]           → pasos en tierra
    [EFECTO:puerta]          → puerta que se abre
    [EFECTO:risa_nino]       → risa de niño
    [EFECTO:aplausos]        → aplausos
    [EFECTO:campanas]        → campanas mágicas
    [EFECTO:fuego]           → crepitar de fuego
    [EFECTO:mar]             → olas del mar
    [EFECTO:lluvia]          → lluvia suave
    [EFECTO:pajaros]         → pájaros cantando
"""

import os
import re
import json
import time
import requests
import subprocess
from pathlib import Path

# ---------------------------------------------------------------------------
# MAPEO DE ETIQUETAS → TÉRMINOS DE BÚSQUEDA EN FREESOUND
# ---------------------------------------------------------------------------

SFX_MAP = {
    "bosque_noche":  {"query": "forest night crickets", "duration_max": 10},
    "rama_crujido":  {"query": "branch crack twig snap", "duration_max": 3},
    "trueno_suave":  {"query": "thunder distant soft", "duration_max": 5},
    "magia":         {"query": "magic spell sparkle", "duration_max": 4},
    "viento":        {"query": "wind gentle breeze", "duration_max": 8},
    "agua_rio":      {"query": "river stream water", "duration_max": 8},
    "pasos":         {"query": "footsteps walking gravel", "duration_max": 4},
    "puerta":        {"query": "door open creak", "duration_max": 3},
    "risa_nino":     {"query": "child laugh giggle", "duration_max": 4},
    "aplausos":      {"query": "applause clapping", "duration_max": 4},
    "campanas":      {"query": "bells chime magical", "duration_max": 4},
    "fuego":         {"query": "fire crackling campfire", "duration_max": 6},
    "mar":           {"query": "ocean waves beach", "duration_max": 10},
    "lluvia":        {"query": "rain soft gentle", "duration_max": 8},
    "pajaros":       {"query": "birds singing morning", "duration_max": 8},
}

SFX_CACHE_DIR = Path("sfx_cache")
SFX_VOLUME    = 0.6  # Volumen de efectos respecto a la voz (0.0-1.0)


# ---------------------------------------------------------------------------
# DESCARGA DE FREESOUND
# ---------------------------------------------------------------------------

def get_freesound_sound(query: str, duration_max: int, api_key: str) -> dict:
    """Busca y descarga un sonido de Freesound."""
    url = "https://freesound.org/apiv2/search/text/"
    params = {
        "query": query,
        "filter": f"duration:[0 TO {duration_max}] license:\"Creative Commons 0\"",
        "fields": "id,name,previews,duration",
        "sort": "rating_desc",
        "page_size": 5,
        "token": api_key,
    }

    r = requests.get(url, params=params, timeout=15)
    if r.status_code != 200:
        raise Exception(f"Freesound error {r.status_code}: {r.text[:200]}")

    results = r.json().get("results", [])
    if not results:
        raise Exception(f"Sin resultados para: {query}")

    sound = results[0]
    preview_url = sound["previews"].get("preview-hq-mp3") or sound["previews"].get("preview-lq-mp3")

    audio = requests.get(preview_url, timeout=30)
    return {"id": sound["id"], "name": sound["name"], "audio": audio.content, "duration": sound["duration"]}


def get_or_download_sfx(sfx_name: str, api_key: str) -> Path:
    """Devuelve la ruta al efecto de sonido, descargándolo si no está en caché."""
    SFX_CACHE_DIR.mkdir(exist_ok=True)
    cache_path = SFX_CACHE_DIR / f"{sfx_name}.mp3"

    if cache_path.exists():
        return cache_path

    if sfx_name not in SFX_MAP:
        raise ValueError(f"Efecto desconocido: {sfx_name}")

    config = SFX_MAP[sfx_name]
    print(f"   🔊 Descargando efecto '{sfx_name}' de Freesound...")

    sound = get_freesound_sound(config["query"], config["duration_max"], api_key)

    with open(cache_path, "wb") as f:
        f.write(sound["audio"])

    print(f"   ✅ Efecto guardado: {cache_path} ({sound['duration']:.1f}s)")
    time.sleep(0.5)  # Rate limiting
    return cache_path


# ---------------------------------------------------------------------------
# PARSEO DE EFECTOS EN EL GUIÓN
# ---------------------------------------------------------------------------

def extract_sfx_positions(txt_path: Path) -> list:
    """
    Lee el guión y extrae los efectos con su posición en líneas.
    Devuelve: [{"line": int, "sfx": str}, ...]
    """
    with open(txt_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    effects = []
    for i, line in enumerate(lines):
        match = re.search(r'\[EFECTO:(\w+)\]', line, re.IGNORECASE)
        if match:
            effects.append({"line": i, "sfx": match.group(1).lower()})

    return effects


# ---------------------------------------------------------------------------
# MEZCLA DE EFECTOS CON FFMPEG
# ---------------------------------------------------------------------------

def get_audio_duration(path: Path) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        capture_output=True, text=True
    )
    try:
        return float(result.stdout.strip())
    except Exception:
        return 0.0


def estimate_position_seconds(txt_path: Path, target_line: int, total_audio_duration: float) -> float:
    """
    Usa el archivo de timestamps generado por generate_audio.py para obtener
    la posición exacta en segundos. Si no existe, usa proporción de líneas.
    """
    import json as _json
    
    # Buscar archivo de timestamps (mismo nombre que el MP3 pero .timestamps.json)
    # El txt_path es stories/es/cuento.txt, el timestamps está en audio/es/cuento.timestamps.json
    lang = None
    for part in txt_path.parts:
        if part in ["es", "en", "fr", "de", "zh"]:
            lang = part
            break
    lang = lang or "es"
    
    ts_path = Path("audio") / lang / f"{txt_path.stem}.timestamps.json"
    
    if ts_path.exists():
        with open(ts_path) as f:
            timestamps = _json.load(f)
        
        # Encontrar el timestamp más cercano a target_line
        best_time = 0.0
        best_diff = float("inf")
        for ts in timestamps:
            diff = abs(ts["line_approx"] - target_line)
            if diff < best_diff:
                best_diff = diff
                best_time = ts["time_start"]
        
        return min(best_time, total_audio_duration * 0.95)
    
    # Fallback: proporción de líneas
    with open(txt_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    content_lines = [(i, l) for i, l in enumerate(lines)
                     if l.strip() and not re.match(r"\[EFECTO:", l.strip(), re.IGNORECASE)]

    total_content = len(content_lines)
    if total_content == 0:
        return 0.0

    lines_before = sum(1 for i, l in content_lines if i < target_line)
    ratio = lines_before / total_content
    return ratio * total_audio_duration


def mix_sfx_into_audio(narration_path: Path, sfx_effects: list,
                        txt_path: Path, output_path: Path) -> Path:
    """
    Mezcla los efectos de sonido en el audio de narración en los momentos correctos.
    """
    if not sfx_effects:
        return narration_path

    total_duration = get_audio_duration(narration_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Construir filtro FFmpeg con todos los efectos
    inputs = ["-i", str(narration_path)]
    filter_parts = ["[0:a]volume=1.0[main]"]
    mix_inputs = ["[main]"]

    valid_effects = []
    for i, effect in enumerate(sfx_effects):
        sfx_path = effect.get("path")
        if not sfx_path or not Path(sfx_path).exists():
            continue

        position = estimate_position_seconds(txt_path, effect["line"], total_duration)
        delay_ms = int(position * 1000)

        inputs.extend(["-i", str(sfx_path)])
        idx = len(valid_effects) + 1
        filter_parts.append(
            f"[{idx}:a]volume={SFX_VOLUME},adelay={delay_ms}|{delay_ms}[sfx{idx}]"
        )
        mix_inputs.append(f"[sfx{idx}]")
        valid_effects.append(effect)

    if not valid_effects:
        return narration_path

    n_inputs = len(valid_effects) + 1
    mix_str = ''.join(mix_inputs)
    filter_parts.append(
        f"{mix_str}amix=inputs={n_inputs}:duration=first:dropout_transition=0:normalize=0[out]"
    )

    cmd = ["ffmpeg", "-y"] + inputs + [
        "-filter_complex", ";".join(filter_parts),
        "-map", "[out]",
        "-c:a", "libmp3lame", "-q:a", "2",
        str(output_path)
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"   ❌ FFmpeg SFX error completo:")
        print(result.stderr[-1000:])
        print(f"   ❌ Comando: {' '.join(cmd[:10])}...")
        raise Exception(f"FFmpeg SFX falló con código {result.returncode}")

    print(f"   ✅ Efectos mezclados: {output_path}")
    return output_path


# ---------------------------------------------------------------------------
# FUNCIÓN PRINCIPAL
# ---------------------------------------------------------------------------

def generate_sfx_for_story(txt_path: Path, narration_path: Path,
                            output_path: Path, api_key: str = None) -> Path:
    """
    Lee el guión, descarga los efectos necesarios y los mezcla con la narración.
    """
    if not api_key:
        api_key = os.environ.get("FREESOUND_API_KEY")
    if not api_key:
        print("   ⚠️  Sin FREESOUND_API_KEY — omitiendo efectos de sonido")
        return narration_path

    effects_in_script = extract_sfx_positions(txt_path)
    if not effects_in_script:
        print("   ℹ️  No hay efectos en el guión")
        return narration_path

    print(f"   🔊 {len(effects_in_script)} efectos detectados en el guión")

    # Descargar efectos
    for effect in effects_in_script:
        try:
            sfx_path = get_or_download_sfx(effect["sfx"], api_key)
            effect["path"] = str(sfx_path)
        except Exception as e:
            print(f"   ⚠️  Error descargando '{effect['sfx']}': {e}")
            effect["path"] = None

    # Mezclar
    return mix_sfx_into_audio(narration_path, effects_in_script, txt_path, output_path)


def process_all_stories(stories_dir: str = "stories", audio_dir: str = "audio",
                        output_dir: str = "audio_sfx", api_key: str = None):
    """Procesa todos los cuentos añadiendo efectos de sonido."""
    txt_files = list(Path(stories_dir).rglob("*.txt"))
    if not txt_files:
        print("⚠️  No hay cuentos en stories/")
        return

    for txt_path in txt_files:
        lang = None
        for part in txt_path.parts:
            if part in ["es", "en", "fr", "de", "zh"]:
                lang = part
                break
        lang = lang or "es"

        narration_path = Path(audio_dir) / lang / f"{txt_path.stem}.mp3"
        if not narration_path.exists():
            print(f"   ⚠️  Sin audio para: {txt_path.name}")
            continue

        output_path = Path(output_dir) / lang / f"{txt_path.stem}.mp3"
        output_path.parent.mkdir(parents=True, exist_ok=True)

        print(f"\n🔊 Procesando efectos: {txt_path.name}")
        generate_sfx_for_story(txt_path, narration_path, output_path, api_key)


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Añade efectos de sonido a los cuentos")
    parser.add_argument("--story",       help="Ruta al .txt del cuento")
    parser.add_argument("--narration",   help="Ruta al MP3 de narración")
    parser.add_argument("--output",      help="Ruta de salida del MP3 con efectos")
    parser.add_argument("--all",         action="store_true")
    parser.add_argument("--api-key",     help="Freesound API key")
    args = parser.parse_args()

    print("🔊 Cuentos Infantiles — Generador de efectos de sonido")
    print("=" * 55)

    if args.all:
        process_all_stories(api_key=args.api_key)
    elif args.story and args.narration and args.output:
        generate_sfx_for_story(
            Path(args.story), Path(args.narration), Path(args.output), args.api_key
        )
    else:
        parser.print_help()
        print("\n💡 Ejemplo:")
        print("   python generate_sfx.py --story stories/es/mi_cuento.txt \\")
        print("          --narration audio/es/mi_cuento.mp3 \\")
        print("          --output audio_sfx/es/mi_cuento.mp3")


if __name__ == "__main__":
    main()
