#!/usr/bin/env python3
"""
generate_cover.py — Genera carátulas JPG para cada episodio usando DALL-E 3.
"""

import argparse
import base64
import json
import os
import re
import requests
from pathlib import Path
from datetime import datetime

COVER_SIZE    = "1024x1024"
COVER_QUALITY = "standard"

PALETTE_DESCRIPTION = """
Soft watercolor illustration style for a children's bedtime podcast called "Cuentos para dormir de Caye".
Visual style requirements:
- Warm, dreamy watercolor technique with soft edges and gentle color bleeding
- Pastel color palette: warm creams, soft blues, dusty roses, warm yellows, sage greens
- Nighttime atmosphere: stars, moon, soft glowing light
- Cozy, safe, magical feeling — never scary or intense
- Rounded, friendly character shapes (no sharp edges)
- Gentle bokeh or soft star effects in background
- Overall mood: peaceful, warm, inviting sleep
- Style reference: Beatrix Potter meets modern Scandinavian children's book illustration
- DO NOT include any text, letters, or writing in the image
- Square format (1:1), centered composition
"""

COVER_PROMPT_TEMPLATE = """
{palette}

For this specific episode:
Title: "{title}"
Theme/Value: "{topic}"
Language/Culture: {culture}

Create a single charming scene that visually represents this story's main character and theme.
The main character should be: {character_hint}
Scene mood: peaceful bedtime, magical but calming, warm light sources (lantern, moon, fireflies, etc.)
"""

CULTURE_HINTS = {
    "es": "Spanish/Mediterranean warmth — warm oranges, golden light",
    "en": "English countryside charm — soft greens, misty morning colors",
    "fr": "French storybook elegance — lavender, soft blues, romantic starlight",
    "de": "German forest fairy tale — deep forest greens, amber, enchanted woods",
    "zh": "Chinese paper-cut inspired — red lanterns, cherry blossoms, jade green",
}

CHARACTER_HINTS = {
    "es": "a small animal or child with big expressive eyes, holding a lantern or looking at the moon",
    "en": "a gentle woodland creature or child wrapped in a cozy blanket under the stars",
    "fr": "a dreamy fox or rabbit in a magical forest clearing with glowing mushrooms",
    "de": "a small bear or hedgehog in a cozy forest cottage with warm candlelight",
    "zh": "a panda or rabbit with traditional paper lanterns and cherry blossom petals",
}


def generate_cover(title: str, topic: str, lang: str, output_dir: str = "covers",
                   api_key: str = None) -> Path:
    """Genera una carátula JPG usando DALL-E 3."""
    try:
        from openai import OpenAI
        from PIL import Image
        import io
    except ImportError:
        print("  ❌ Instala: pip install openai pillow")
        raise

    client = OpenAI(api_key=api_key) if api_key else OpenAI()

    prompt = COVER_PROMPT_TEMPLATE.format(
        palette=PALETTE_DESCRIPTION,
        title=title,
        topic=topic,
        culture=CULTURE_HINTS.get(lang, CULTURE_HINTS["es"]),
        character_hint=CHARACTER_HINTS.get(lang, CHARACTER_HINTS["es"]),
    )

    print(f"  🎨 Generando carátula: '{title}' [{lang.upper()}]...")

    # Generar imagen y descargar via URL (compatible con openai>=2.0)
    response = client.images.generate(
        model="dall-e-3",
        prompt=prompt,
        size=COVER_SIZE,
        quality=COVER_QUALITY,
        n=1,
    )

    image_url      = response.data[0].url
    revised_prompt = response.data[0].revised_prompt
    img_response   = requests.get(image_url, timeout=60)
    img_response.raise_for_status()
    image_bytes    = img_response.content

    # Convertir a JPG 3000x3000
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    img = img.resize((3000, 3000), Image.LANCZOS)

    slug = re.sub(r'[^\w\s-]', '', title.lower())
    slug = re.sub(r'[\s]+', '_', slug.strip())[:50]

    lang_cover_dir = Path(output_dir) / lang
    lang_cover_dir.mkdir(parents=True, exist_ok=True)

    jpg_path = lang_cover_dir / f"{slug}.jpg"
    img.save(jpg_path, "JPEG", quality=95, optimize=True)

    meta_path = lang_cover_dir / f"{slug}_cover.json"
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump({
            "title": title,
            "topic": topic,
            "lang": lang,
            "jpg_file": str(jpg_path),
            "revised_prompt": revised_prompt,
            "generated_at": datetime.now().isoformat(),
            "size_px": "3000x3000",
            "model": "dall-e-3",
        }, f, ensure_ascii=False, indent=2)

    print(f"  ✅ Carátula guardada: {jpg_path}")
    return jpg_path


def generate_covers_from_json(json_path: Path, output_dir: str = "covers",
                               api_key: str = None) -> Path:
    with open(json_path, "r", encoding="utf-8") as f:
        meta = json.load(f)
    return generate_cover(
        title=meta["title"],
        topic=meta["topic"],
        lang=meta["lang"],
        output_dir=output_dir,
        api_key=api_key,
    )


def generate_all_covers(stories_dir: str = "stories", output_dir: str = "covers",
                        api_key: str = None):
    json_files = [f for f in Path(stories_dir).rglob("*.json")
                  if not f.name.endswith("_cover.json")]
    if not json_files:
        print(f"  ⚠️  No se encontraron archivos .json en {stories_dir}/")
        return
    print(f"  🎨 Generando carátulas para {len(json_files)} episodios")
    results = []
    for json_file in json_files:
        try:
            jpg_path = generate_covers_from_json(json_file, output_dir, api_key)
            results.append({"json": str(json_file), "jpg": str(jpg_path), "ok": True})
        except Exception as e:
            print(f"  ❌ Error con {json_file}: {e}")
            results.append({"json": str(json_file), "error": str(e), "ok": False})
    ok = sum(1 for r in results if r["ok"])
    print(f"\n  ✨ Completado: {ok}/{len(results)} carátulas en {output_dir}/")
    return results


def main():
    parser = argparse.ArgumentParser(description="Genera carátulas JPG con DALL-E 3")
    parser.add_argument("--story",      help="Ruta al .json del cuento")
    parser.add_argument("--title",      help="Título del episodio")
    parser.add_argument("--topic",      help="Tema del episodio")
    parser.add_argument("--lang",       choices=["es", "en", "fr", "de", "zh"])
    parser.add_argument("--all",        action="store_true")
    parser.add_argument("--output-dir", default="covers")
    parser.add_argument("--api-key",    help="OpenAI API key")
    args = parser.parse_args()

    print("🎨 Cuentos para dormir de Caye — Generador de carátulas")
    print("=" * 55)

    if args.all:
        generate_all_covers(output_dir=args.output_dir, api_key=args.api_key)
    elif args.story:
        generate_covers_from_json(Path(args.story), args.output_dir, args.api_key)
    elif args.title and args.topic and args.lang:
        generate_cover(args.title, args.topic, args.lang, args.output_dir, args.api_key)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
