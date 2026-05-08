#!/usr/bin/env python3
"""
generate_story.py — Genera cuentos infantiles para "Cuentos para dormir de Caye"
usando la API de Claude (Anthropic). Estilo: Raquel Tolmo. Mezcla valores/emociones
y aventuras/fantasía. Audiencia: 3-8 años.

Uso:
    python generate_story.py --lang es --topic "la amistad" --title "Luna y el dragón triste"
    python generate_story.py --lang en --topic "courage" --title "Benny the Brave Bear"
    python generate_story.py --all  # genera uno por cada idioma automáticamente
"""

import anthropic
import argparse
import json
import os
import re
from datetime import datetime
from pathlib import Path

# ──────────────────────────────────────────────
# CONFIGURACIÓN
# ──────────────────────────────────────────────

LANGUAGES = {
    "es": {
        "name": "español",
        "narrator_intro": "Hola, pequeños soñadores. Soy Caye, y esta noche os traigo una historia muy especial...",
        "voice_code": "es-ES-Neural2-C",   # Google TTS
        "prompt_lang": "español",
    },
    "en": {
        "name": "English",
        "narrator_intro": "Hello, little dreamers. I'm Caye, and tonight I have a very special story for you...",
        "voice_code": "en-GB-Neural2-C",
        "prompt_lang": "English",
    },
    "fr": {
        "name": "français",
        "narrator_intro": "Bonsoir, petits rêveurs. Je suis Caye, et ce soir je vous apporte une histoire très spéciale...",
        "voice_code": "fr-FR-Neural2-C",
        "prompt_lang": "français",
    },
    "de": {
        "name": "Deutsch",
        "narrator_intro": "Hallo, kleine Träumer. Ich bin Caye, und heute Abend bringe ich euch eine ganz besondere Geschichte...",
        "voice_code": "de-DE-Neural2-C",
        "prompt_lang": "Deutsch",
    },
    "zh": {
        "name": "中文",
        "narrator_intro": "你好，小梦想家们。我是Caye，今晚我为你们带来一个非常特别的故事……",
        "voice_code": "cmn-CN-Neural2-D",
        "prompt_lang": "中文（普通话）",
    },
}

# Temas predeterminados por idioma (para modo --all)
DEFAULT_TOPICS = {
    "es": {"topic": "el miedo a la oscuridad",   "title": "Luca y la linterna mágica"},
    "en": {"topic": "sharing with others",        "title": "Mia and the Magic Cake"},
    "fr": {"topic": "le courage face à l'inconnu","title": "Léo et la forêt enchantée"},
    "de": {"topic": "Freundschaft und Geduld",    "title": "Milo und der schlafende Riese"},
    "zh": {"topic": "勇气和友谊",                  "title": "小星星和月亮的秘密"},
}

STORY_PROMPT_TEMPLATE = """
Eres una narradora de cuentos infantiles profesional llamada Caye. Tu estilo es muy similar al de Raquel Tolmo 
en su podcast "Cuentos Infantiles Para Dormir": voz cálida, cercana, con ritmo pausado, lenguaje accesible, 
personajes entrañables (animales o niños), y siempre con un mensaje emocional o de valores claro al final.

Escribe un cuento infantil COMPLETO en {lang} con estas características:

TÍTULO: {title}
TEMA / VALOR: {topic}
EDAD OBJETIVO: mezcla de 3-5 y 5-8 años (lenguaje accesible para los pequeños, historia rica para los mayores)
DURACIÓN OBJETIVO: 10-14 minutos al escucharlo (~1.200-1.500 palabras)
ESTILO: mezcla de aventura/fantasía con valores y emociones (como Raquel Tolmo)

ESTRUCTURA OBLIGATORIA:
1. INTRODUCCIÓN CÁLIDA (2-3 párrafos): Presenta el personaje principal y su mundo. 
   Crea inmediatamente conexión emocional.
2. PROBLEMA O AVENTURA (4-5 párrafos): El personaje se enfrenta a un reto, miedo, 
   o situación que le hace crecer. Puede incluir un elemento de fantasía o magia.
3. DESARROLLO (3-4 párrafos): El personaje intenta resolver el problema, con ayuda 
   de amigos o figuras de apoyo. Momentos de emoción genuina.
4. RESOLUCIÓN Y MENSAJE (2-3 párrafos): El problema se resuelve de forma satisfactoria.
   El personaje aprende algo importante sobre sí mismo o sobre la vida.
5. CIERRE PARA DORMIR (1 párrafo): Termina con una frase suave y relajante que invite 
   a los niños a cerrar los ojos y soñar. Caye se despide hasta la próxima noche.

REGLAS DE ESCRITURA:
- Narración en primera persona de Caye (narradora externa que acompaña al oyente)
- Frases cortas y musicales, fáciles de escuchar
- Descripciones sensoriales suaves (colores, olores, texturas)
- Diálogos naturales y emotivos entre personajes
- Repeticiones rítmicas cuando sea apropiado (estilo oral)
- NUNCA violencia, sustos fuertes ni contenido inapropiado
- El mensaje final debe ser claro pero nunca sermoneador
- Termina SIEMPRE con "Hasta la próxima noche, pequeños soñadores. Dulces sueños. 🌙"

Escribe SOLO el cuento, sin comentarios ni metadatos. Empieza directamente con el título 
en formato: # TÍTULO DEL CUENTO
"""

# ──────────────────────────────────────────────
# FUNCIONES
# ──────────────────────────────────────────────

def generate_story(lang: str, topic: str, title: str, api_key: str = None) -> dict:
    """Genera un cuento usando Claude API."""
    
    client = anthropic.Anthropic(api_key=api_key) if api_key else anthropic.Anthropic()
    lang_config = LANGUAGES[lang]
    
    prompt = STORY_PROMPT_TEMPLATE.format(
        lang=lang_config["prompt_lang"],
        title=title,
        topic=topic,
    )
    
    print(f"  ✍️  Generando cuento: '{title}' [{lang.upper()}]...")
    
    message = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}]
    )
    
    story_text = message.content[0].text
    
    # Añadir intro de Caye al principio
    narrator_intro = f"\n\n{lang_config['narrator_intro']}\n\n"
    story_with_intro = re.sub(r'^(# .+\n)', r'\1' + narrator_intro, story_text, count=1)
    
    # Construir metadata
    result = {
        "lang": lang,
        "title": title,
        "topic": topic,
        "text": story_with_intro,
        "word_count": len(story_text.split()),
        "voice_code": lang_config["voice_code"],
        "generated_at": datetime.now().isoformat(),
        "model": "claude-opus-4-5",
        "podcast_name": "Cuentos para dormir de Caye",
    }
    
    print(f"  ✅ Cuento generado: {result['word_count']} palabras")
    return result


def save_story(story_data: dict, output_dir: str = "stories") -> Path:
    """Guarda el cuento como .txt y .json con metadata."""
    
    lang = story_data["lang"]
    # Slug del título para el nombre de archivo
    slug = re.sub(r'[^\w\s-]', '', story_data["title"].lower())
    slug = re.sub(r'[\s]+', '_', slug.strip())[:50]
    
    lang_dir = Path(output_dir) / lang
    lang_dir.mkdir(parents=True, exist_ok=True)
    
    # Guardar texto
    txt_path = lang_dir / f"{slug}.txt"
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(story_data["text"])
    
    # Guardar metadata JSON
    json_path = lang_dir / f"{slug}.json"
    meta = {k: v for k, v in story_data.items() if k != "text"}
    meta["txt_file"] = str(txt_path)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    
    print(f"  💾 Guardado: {txt_path}")
    return txt_path


def generate_all_languages(api_key: str = None) -> list:
    """Genera un cuento por cada idioma usando los temas predeterminados."""
    results = []
    for lang, config in DEFAULT_TOPICS.items():
        print(f"\n📖 [{lang.upper()}] Generando: {config['title']}")
        story = generate_story(lang, config["topic"], config["title"], api_key)
        path = save_story(story)
        results.append({"lang": lang, "path": str(path), "title": config["title"]})
    return results


# ──────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Genera cuentos infantiles para 'Cuentos para dormir de Caye'"
    )
    parser.add_argument("--lang", choices=list(LANGUAGES.keys()),
                        help="Idioma del cuento (es/en/fr/de/zh)")
    parser.add_argument("--topic", help="Tema o valor del cuento")
    parser.add_argument("--title", help="Título del cuento")
    parser.add_argument("--all", action="store_true",
                        help="Genera un cuento en cada idioma con temas predeterminados")
    parser.add_argument("--output-dir", default="stories",
                        help="Directorio de salida (default: stories/)")
    parser.add_argument("--api-key", help="Anthropic API key (o usa ANTHROPIC_API_KEY env var)")
    
    args = parser.parse_args()
    
    print("🌙 Cuentos para dormir de Caye — Generador de historias")
    print("=" * 55)
    
    if args.all:
        results = generate_all_languages(args.api_key)
        print(f"\n✨ Generados {len(results)} cuentos:")
        for r in results:
            print(f"   [{r['lang'].upper()}] {r['title']} → {r['path']}")
    
    elif args.lang and args.topic and args.title:
        story = generate_story(args.lang, args.topic, args.title, args.api_key)
        save_story(story, args.output_dir)
    
    else:
        parser.print_help()
        print("\n💡 Ejemplo rápido:")
        print('   python generate_story.py --lang es --topic "la amistad" --title "Luna y el dragón triste"')
        print('   python generate_story.py --all')


if __name__ == "__main__":
    main()
