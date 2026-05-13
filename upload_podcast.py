#!/usr/bin/env python3
"""
upload_podcast.py — Sube episodios a Spotify for Podcasters (antes Anchor).
Desde ahí se distribuye automáticamente a: Spotify, Apple Podcasts,
Amazon Music, iVoox, Google Podcasts, Pocket Casts, y más.

IMPORTANTE: Spotify for Podcasters NO tiene API pública oficial.
Este script usa la API no oficial documentada por la comunidad.
Alternativa recomendada: usar Buzzsprout (tiene API oficial).

Modos disponibles:
  --platform anchor    → Spotify for Podcasters (gratis, sin API oficial)
  --platform buzzsprout → Buzzsprout (API oficial, ~$12/mes)
  --platform rss       → Genera RSS feed local (máximo control)

Prerequisitos:
    pip install requests mutagen

Uso:
    python upload_podcast.py --mp3 audio/es/luca.mp3 --cover covers/es/luca.jpg \\
        --title "Luca y la linterna mágica" --topic "el miedo a la oscuridad" \\
        --lang es --episode 1

    python upload_podcast.py --all  # sube todo lo generado
"""

import argparse
import json
import os
import re
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from email.utils import formatdate
import time

# ──────────────────────────────────────────────
# CONFIGURACIÓN DEL PODCAST
# ──────────────────────────────────────────────

PODCAST_CONFIG = {
    "title": "Las aventuras de Caye y Alvarito",
    "description": (
        "🌙 Un espacio mágico donde los pequeños soñadores encuentran cuentos "
        "infantiles únicos llenos de valores, emociones y aventuras. "
        "Cuentos originales narrados con voz cálida para ayudar a los niños "
        "a conciliar el sueño en español, inglés, francés, alemán y chino. "
        "¡Hasta la próxima noche, pequeños soñadores! ✨"
    ),
    "author": "Caye",
    "email": "aventurasdecayeyalvarito@gmail.com",   # ← CAMBIAR
    "language_map": {
        "es": "es-ES",
        "en": "en-GB",
        "fr": "fr-FR",
        "de": "de-DE",
        "zh": "zh-CN",
    },
    "category": "Kids & Family",
    "subcategory": "Stories for Kids",
    "explicit": "false",
    "website": "https://aventurasdecayeyalvarito.com",  # ← CAMBIAR cuando tengas web
}

EPISODE_DESCRIPTIONS = {
    "es": "🌙 Un nuevo cuento de Caye para acompañar a los pequeños soñadores en su viaje al país de los sueños. ✨ #AventurasDeCaye #CuentosInfantiles #AventurasCayeAlvarito",
    "en": "🌙 A new story from Caye to accompany little dreamers on their journey to dreamland. ✨ #BedtimeStories #KidsStories #CayeStories",
    "fr": "🌙 Une nouvelle histoire de Caye pour accompagner les petits rêveurs dans leur voyage au pays des rêves. ✨ #ContesPourdormir #HistoiresEnfants",
    "de": "🌙 Eine neue Geschichte von Caye, die kleine Träumer auf ihrer Reise ins Traumland begleitet. ✨ #Gutenachtgeschichten #KinderGeschichten",
    "zh": "🌙 Caye的新故事，陪伴小梦想家们踏上梦乡之旅。✨ #睡前故事 #儿童故事 #Caye故事",
}

# ──────────────────────────────────────────────
# BUZZSPROUT API (recomendado — tiene API oficial)
# ──────────────────────────────────────────────

def upload_to_buzzsprout(mp3_path: Path, cover_path: Path, title: str, topic: str,
                          lang: str, episode_num: int, api_token: str,
                          podcast_id: str) -> dict:
    """
    Sube un episodio a Buzzsprout via API oficial.
    
    Obtén tu API token en: buzzsprout.com → Settings → API
    Plan gratuito: 3 horas/mes. Plan $12/mes: ilimitado.
    """
    
    base_url = f"https://www.buzzsprout.com/api/{podcast_id}/episodes.json"
    headers = {"Authorization": f"Token token={api_token}"}
    
    lang_name = {"es": "Español", "en": "English", "fr": "Français",
                  "de": "Deutsch", "zh": "中文"}
    
    description = (
        f"Tema: {topic}\n\n"
        f"{EPISODE_DESCRIPTIONS.get(lang, EPISODE_DESCRIPTIONS['es'])}\n\n"
        f"Idioma: {lang_name.get(lang, lang)}\n"
        f"Podcast: {PODCAST_CONFIG['title']}"
    )
    
    print(f"  📤 Subiendo a Buzzsprout: '{title}'...")
    
    with open(mp3_path, "rb") as mp3_file:
        files = {"audio_file": (mp3_path.name, mp3_file, "audio/mpeg")}
        data = {
            "title": title,
            "description": description,
            "summary": f"Cuento infantil: {topic}",
            "episode_number": episode_num,
            "explicit": False,
            "private": False,
        }
        
        response = requests.post(base_url, headers=headers, files=files, data=data)
        response.raise_for_status()
        result = response.json()
    
    episode_id = result["id"]
    
    # Subir carátula del episodio si existe
    if cover_path and cover_path.exists():
        artwork_url = f"https://www.buzzsprout.com/api/{podcast_id}/episodes/{episode_id}.json"
        with open(cover_path, "rb") as img_file:
            requests.patch(
                artwork_url,
                headers=headers,
                files={"artwork": (cover_path.name, img_file, "image/jpeg")},
            )
    
    print(f"  ✅ Subido a Buzzsprout: ID {episode_id}")
    print(f"     URL: {result.get('audio_url', 'pendiente')}")
    return result


# ──────────────────────────────────────────────
# RSS FEED LOCAL (máximo control, sin dependencias de terceros)
# ──────────────────────────────────────────────

def generate_rss_feed(episodes_dir: str = ".", output_path: str = "feed.xml") -> Path:
    """
    Genera un RSS feed XML completo a partir de los episodios locales.
    Puedes alojar este XML en GitHub Pages o cualquier hosting gratuito.
    Spotify, Apple Podcasts, Amazon Music aceptan RSS feeds directamente.
    """
    
    # Cargar todos los episodios desde los JSON de metadata
    episodes = []
    
    for json_file in Path(episodes_dir).rglob("*.json"):
        if "cover" in json_file.name:
            continue
        try:
            with open(json_file) as f:
                meta = json.load(f)
            if "title" in meta and "lang" in meta:
                episodes.append(meta)
        except Exception:
            continue
    
    episodes.sort(key=lambda e: e.get("generated_at", ""), reverse=True)
    
    # Construir XML RSS 2.0 con namespace iTunes
    rss = ET.Element("rss", {
        "version": "2.0",
        "xmlns:itunes": "http://www.itunes.com/dtds/podcast-1.0.dtd",
        "xmlns:content": "http://purl.org/rss/1.0/modules/content/",
    })
    
    channel = ET.SubElement(rss, "channel")
    
    # Metadata del canal
    ET.SubElement(channel, "title").text = PODCAST_CONFIG["title"]
    ET.SubElement(channel, "description").text = PODCAST_CONFIG["description"]
    ET.SubElement(channel, "link").text = PODCAST_CONFIG["website"]
    ET.SubElement(channel, "language").text = "es-ES"
    ET.SubElement(channel, "itunes:author").text = PODCAST_CONFIG["author"]
    ET.SubElement(channel, "itunes:explicit").text = PODCAST_CONFIG["explicit"]
    
    itunes_category = ET.SubElement(channel, "itunes:category",
                                     {"text": PODCAST_CONFIG["category"]})
    ET.SubElement(itunes_category, "itunes:category",
                  {"text": PODCAST_CONFIG["subcategory"]})
    
    owner = ET.SubElement(channel, "itunes:owner")
    ET.SubElement(owner, "itunes:name").text = PODCAST_CONFIG["author"]
    ET.SubElement(owner, "itunes:email").text = PODCAST_CONFIG["email"]
    
    # Episodios
    for i, ep in enumerate(episodes, 1):
        item = ET.SubElement(channel, "item")
        ET.SubElement(item, "title").text = ep.get("title", f"Episodio {i}")
        
        desc = (
            f"Tema: {ep.get('topic', '')}\n\n"
            f"{EPISODE_DESCRIPTIONS.get(ep.get('lang', 'es'), '')}"
        )
        ET.SubElement(item, "description").text = desc
        ET.SubElement(item, "itunes:summary").text = desc
        ET.SubElement(item, "itunes:author").text = PODCAST_CONFIG["author"]
        ET.SubElement(item, "itunes:explicit").text = "false"
        ET.SubElement(item, "itunes:episode").text = str(i)
        ET.SubElement(item, "pubDate").text = formatdate(
            datetime.fromisoformat(ep.get("generated_at",
                datetime.now().isoformat())).timestamp()
        )
        
        # GUID único
        slug = re.sub(r'[^\w]', '-', ep.get('title', str(i)).lower())
        ET.SubElement(item, "guid", {"isPermaLink": "false"}).text = (
            f"caye-{ep.get('lang', 'es')}-{slug}"
        )
        
        # Audio enclosure (ajustar URL base cuando tengas hosting)
        mp3_name = re.sub(r'[^\w\s-]', '', ep.get('title', '').lower())
        mp3_name = re.sub(r'\s+', '_', mp3_name.strip())[:50] + ".mp3"
        audio_url = f"{PODCAST_CONFIG['website']}/audio/{ep.get('lang', 'es')}/{mp3_name}"
        
        ET.SubElement(item, "enclosure", {
            "url": audio_url,
            "type": "audio/mpeg",
            "length": "0",  # Actualizar con tamaño real del archivo
        })
    
    # Escribir XML
    tree = ET.ElementTree(rss)
    ET.indent(tree, space="  ")
    
    output = Path(output_path)
    tree.write(output, encoding="unicode", xml_declaration=True)
    
    print(f"  ✅ RSS feed generado: {output} ({len(episodes)} episodios)")
    return output


# ──────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Sube episodios de 'Las aventuras de Caye y Alvarito' a plataformas"
    )
    parser.add_argument("--mp3", help="Ruta al archivo MP3")
    parser.add_argument("--cover", help="Ruta a la carátula JPG")
    parser.add_argument("--title", help="Título del episodio")
    parser.add_argument("--topic", help="Tema del episodio")
    parser.add_argument("--lang", choices=["es", "en", "fr", "de", "zh"])
    parser.add_argument("--episode", type=int, default=1, help="Número de episodio")
    parser.add_argument("--platform",
                        choices=["buzzsprout", "rss"],
                        default="rss",
                        help="Plataforma destino (default: rss)")
    parser.add_argument("--rss-output", default="feed.xml",
                        help="Ruta del RSS feed generado (default: feed.xml)")
    parser.add_argument("--buzzsprout-token", help="API token de Buzzsprout")
    parser.add_argument("--buzzsprout-id", help="Podcast ID de Buzzsprout")
    
    args = parser.parse_args()
    
    print("📡 Las aventuras de Caye y Alvarito — Subida a plataformas")
    print("=" * 55)
    
    if args.platform == "rss":
        print("  📋 Generando RSS feed local...")
        generate_rss_feed(output_path=args.rss_output)
        print("\n  📌 Próximos pasos:")
        print("  1. Sube el feed.xml a GitHub Pages (gratis)")
        print("  2. Envía la URL del feed a Spotify for Podcasters: podcasters.spotify.com")
        print("  3. Envía a Apple Podcasts Connect: podcastsconnect.apple.com")
        print("  4. Envía a Amazon Music/Audible: music.amazon.com/podcasts/submit")
        print("  5. Envía a iVoox: ivoox.com (importar RSS)")
    
    elif args.platform == "buzzsprout":
        if not all([args.mp3, args.title, args.topic, args.lang,
                    args.buzzsprout_token, args.buzzsprout_id]):
            print("  ❌ Para Buzzsprout necesitas: --mp3 --title --topic --lang "
                  "--buzzsprout-token --buzzsprout-id")
            return
        
        upload_to_buzzsprout(
            mp3_path=Path(args.mp3),
            cover_path=Path(args.cover) if args.cover else None,
            title=args.title,
            topic=args.topic,
            lang=args.lang,
            episode_num=args.episode,
            api_token=args.buzzsprout_token,
            podcast_id=args.buzzsprout_id,
        )


if __name__ == "__main__":
    main()
