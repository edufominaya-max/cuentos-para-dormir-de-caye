#!/usr/bin/env python3
"""
run_pipeline.py — Pipeline completo: genera cuento → audio → carátula → RSS

Este es el script maestro. Ejecuta todo el flujo de un tirón.

Uso básico:
    python run_pipeline.py --lang es --topic "el miedo a la oscuridad" --title "Luca y la linterna mágica" --episode 1

Generar los 5 idiomas de una vez:
    python run_pipeline.py --all --episode 1

Solo texto (sin audio ni carátula):
    python run_pipeline.py --lang es --topic "la amistad" --title "Mi cuento" --skip-audio --skip-cover

Variables de entorno necesarias (ejecuta set_keys.bat primero):
    ANTHROPIC_API_KEY    → Para generar los cuentos (Claude)
    OPENAI_API_KEY       → Para las carátulas (DALL-E 3)
    ELEVENLABS_API_KEY   → Para el audio (ElevenLabs TTS)
"""

import argparse
import json
import os
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))


def run_step(step_name: str, func, *args, **kwargs):
    print(f"\n{'='*55}")
    print(f"  PASO: {step_name}")
    print(f"{'='*55}")
    try:
        result = func(*args, **kwargs)
        print(f"  ✅ {step_name} completado")
        return result
    except Exception as e:
        print(f"  ❌ Error en {step_name}: {e}")
        raise


def run_full_pipeline(lang: str, topic: str, title: str, episode_num: int,
                      skip_audio: bool = False, skip_cover: bool = False,
                      skip_upload: bool = False):

    from generate_story import generate_story, save_story

    results = {
        "lang": lang,
        "title": title,
        "topic": topic,
        "episode": episode_num,
        "started_at": datetime.now().isoformat(),
    }

    # ── PASO 1: Generar cuento ──────────────────────
    story_data = run_step(
        f"1/4 Generar cuento [{lang.upper()}]",
        generate_story, lang, topic, title
    )
    txt_path = run_step(
        "    Guardar texto",
        save_story, story_data
    )
    results["txt_path"] = str(txt_path)
    results["word_count"] = story_data["word_count"]

    # ── PASO 2: Generar audio (ElevenLabs) ─────────
    if not skip_audio:
        if not os.getenv("ELEVENLABS_API_KEY"):
            print("\n  ⚠️  PASO 2/4: ELEVENLABS_API_KEY no configurada — ejecuta set_keys.bat")
            results["mp3_path"] = None
        else:
            try:
                from generate_audio import generate_audio
                mp3_path = run_step(
                    f"2/4 Generar audio ElevenLabs [{lang.upper()}]",
                    generate_audio, txt_path, "audio", lang
                )
                results["mp3_path"] = str(mp3_path)
            except Exception as e:
                print(f"  ⚠️  Error generando audio: {e}")
                results["mp3_path"] = None
    else:
        print("\n  ⏭️  PASO 2/4: Audio omitido (--skip-audio)")
        results["mp3_path"] = None

    # ── PASO 3: Generar carátula ────────────────────
    if not skip_cover:
        if not os.getenv("OPENAI_API_KEY"):
            print("\n  ⚠️  PASO 3/4: OPENAI_API_KEY no configurada — saltando carátula")
            results["cover_path"] = None
        else:
            try:
                from generate_cover import generate_cover
                jpg_path = run_step(
                    f"3/4 Generar carátula [{lang.upper()}]",
                    generate_cover, title, topic, lang
                )
                results["cover_path"] = str(jpg_path)
            except Exception as e:
                print(f"  ⚠️  Error generando carátula: {e}")
                results["cover_path"] = None
    else:
        print("\n  ⏭️  PASO 3/4: Carátula omitida (--skip-cover)")
        results["cover_path"] = None

    # ── PASO 4: Actualizar RSS ──────────────────────
    if not skip_upload:
        try:
            from upload_podcast import generate_rss_feed
            rss_path = run_step(
                "4/4 Actualizar RSS feed",
                generate_rss_feed, "stories", "feed.xml"
            )
            results["rss_path"] = str(rss_path)
        except Exception as e:
            print(f"  ⚠️  Error actualizando RSS: {e}")
    else:
        print("\n  ⏭️  PASO 4/4: Upload omitido (--skip-upload)")

    results["completed_at"] = datetime.now().isoformat()

    # Guardar log
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / f"episode_{episode_num:03d}_{lang}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(log_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    return results


def run_all_languages(episode_start: int = 1, **kwargs):
    from generate_story import DEFAULT_TOPICS

    all_results = []
    for i, (lang, config) in enumerate(DEFAULT_TOPICS.items()):
        print(f"\n\n{'🌙'*20}")
        print(f"  IDIOMA {i+1}/5: {lang.upper()} — {config['title']}")
        print(f"{'🌙'*20}")
        try:
            result = run_full_pipeline(
                lang=lang,
                topic=config["topic"],
                title=config["title"],
                episode_num=episode_start + i,
                **kwargs,
            )
            all_results.append(result)
        except Exception as e:
            print(f"  ❌ Error en idioma {lang}: {e}")
            all_results.append({"lang": lang, "error": str(e)})

    return all_results


def print_summary(results):
    print(f"\n\n{'='*55}")
    print("  📊 RESUMEN FINAL")
    print(f"{'='*55}")

    if isinstance(results, list):
        for r in results:
            lang = r.get("lang", "?").upper()
            if "error" in r:
                print(f"  ❌ [{lang}] Error: {r['error']}")
            else:
                txt   = "✅" if r.get("txt_path") else "❌"
                mp3   = "✅" if r.get("mp3_path") else "⏭️ "
                cover = "✅" if r.get("cover_path") else "⏭️ "
                print(f"  [{lang}] Texto {txt}  Audio {mp3}  Carátula {cover}  — {r.get('title','?')}")
    else:
        r = results
        print(f"  [{r.get('lang','?').upper()}] {r.get('title','?')}")
        print(f"  Palabras: {r.get('word_count','?')}")
        print(f"  Audio:    {r.get('mp3_path','No generado')}")
        print(f"  Carátula: {r.get('cover_path','No generada')}")

    print(f"\n  🌙 ¡Hasta la próxima noche, pequeños soñadores!")


def main():
    parser = argparse.ArgumentParser(
        description="Pipeline completo: cuento → audio → carátula → RSS"
    )
    parser.add_argument("--lang", choices=["es", "en", "fr", "de", "zh"])
    parser.add_argument("--topic")
    parser.add_argument("--title")
    parser.add_argument("--episode", type=int, default=1)
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--skip-audio",  action="store_true")
    parser.add_argument("--skip-cover",  action="store_true")
    parser.add_argument("--skip-upload", action="store_true")

    args = parser.parse_args()

    print("🌙 Las aventuras de Caye y Alvarito — Pipeline completo")
    print("=" * 55)
    print(f"   Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    print(f"   Modo:  {'TODOS LOS IDIOMAS' if args.all else args.lang.upper() if args.lang else '?'}")

    opts = {
        "skip_audio":  args.skip_audio,
        "skip_cover":  args.skip_cover,
        "skip_upload": args.skip_upload,
    }

    if args.all:
        results = run_all_languages(episode_start=args.episode, **opts)
        print_summary(results)
    elif args.lang and args.topic and args.title:
        result = run_full_pipeline(args.lang, args.topic, args.title, args.episode, **opts)
        print_summary(result)
    else:
        parser.print_help()
        print("\n💡 Ejemplos:")
        print('   python run_pipeline.py --all --episode 1')
        print('   python run_pipeline.py --lang es --topic "la amistad" --title "Luna y Estrella" --episode 1')
        print('   python run_pipeline.py --all --skip-audio --skip-cover')


if __name__ == "__main__":
    main()
