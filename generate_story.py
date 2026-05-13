#!/usr/bin/env python3
"""
generate_story.py — Genera cuentos infantiles para "Las aventuras de Caye y Alvarito"
usando la API de Claude (Anthropic). Protagonistas: Caye (7 años) y Álvaro (3 años).
"""

import anthropic
import argparse
import json
import os
import random
import re
from datetime import datetime
from pathlib import Path

# ──────────────────────────────────────────────
# INTROS ALEATORIAS
# ──────────────────────────────────────────────

NARRATOR_INTROS = {
    "es": [
        "Psssst... ¿sigues despierto? Qué suerte, porque esta noche tengo algo especial para ti. Soy Caye, y juntos vamos a descubrir una historia increíble...",
        "Hola, soy Caye. La luna ya está en el cielo y las estrellas te están esperando. Cierra los ojitos, que te llevo de viaje...",
        "Esta noche, antes de que cierres los ojos, yo, Caye, quiero contarte algo que solo tú vas a escuchar. Una historia que nació justo para este momento...",
        "Hola, soy Caye. Ya es hora de dormir... pero antes, ven, que tenemos una aventura pendiente tú y yo.",
        "Sssshhh... la noche ha llegado y con ella, una historia que te estaba esperando. Soy Caye, y esta noche viajamos juntos...",
        "¿Ya estás en la cama? Perfecto. Soy Caye, y esta noche tengo guardada una historia solo para ti. Una historia que empieza ahora mismo...",
        "Cierra los ojos un momento... ¿los tienes cerrados? Bien. Soy Caye, y esta noche vamos a un lugar muy especial. ¿Me acompañas?",
    ],
    "en": [
        "Psssst... still awake? How lucky, because tonight I have something very special for you. I'm Caye, and together we're going on an incredible adventure...",
        "Hello, I'm Caye. The moon is already up in the sky and the stars are waiting for you. Close your little eyes and let me take you on a journey...",
        "Tonight, before you close your eyes, I, Caye, want to tell you something only you will hear. A story that was born just for this moment...",
        "Hi, I'm Caye. It's time to sleep... but first, come here, because you and I have an adventure waiting for us.",
        "Shhhhh... night has arrived, and with it, a story that was waiting just for you. I'm Caye, and tonight we travel together...",
        "Are you already in bed? Perfect. I'm Caye, and tonight I have a story saved just for you. A story that begins right now...",
        "Close your eyes for a moment... got them closed? Good. I'm Caye, and tonight we're going somewhere very special. Will you come with me?",
    ],
    "fr": [
        "Psssst... tu es encore réveillé ? Quelle chance, parce que ce soir j'ai quelque chose de très spécial pour toi. Je suis Caye, et ensemble nous allons découvrir une histoire incroyable...",
        "Bonsoir, je suis Caye. La lune est déjà dans le ciel et les étoiles t'attendent. Ferme les yeux, je t'emmène en voyage...",
        "Ce soir, avant que tu fermes les yeux, moi, Caye, je veux te raconter quelque chose que toi seul vas entendre. Une histoire née juste pour ce moment...",
        "Chhhut... la nuit est arrivée, et avec elle, une histoire qui t'attendait. Je suis Caye, et cette nuit nous voyageons ensemble...",
        "Tu es déjà dans ton lit ? Parfait. Je suis Caye, et ce soir j'ai une histoire gardée rien que pour toi. Une histoire qui commence maintenant...",
        "Ferme les yeux un instant... tu les as fermés ? Bien. Je suis Caye, et ce soir nous allons dans un endroit très spécial. Tu m'accompagnes ?",
        "Psssst... tu veux entendre un secret ? Ce soir, j'ai une histoire magique qui n'attend que toi. Je suis Caye, et nous partons à l'aventure...",
    ],
    "de": [
        "Psssst... bist du noch wach? Welch ein Glück, denn heute Nacht habe ich etwas ganz Besonderes für dich. Ich bin Caye, und zusammen erleben wir eine unglaubliche Geschichte...",
        "Hallo, ich bin Caye. Der Mond steht schon am Himmel und die Sterne warten auf dich. Schließ deine Augen, ich nehme dich mit auf eine Reise...",
        "Heute Nacht, bevor du die Augen schließt, möchte ich, Caye, dir etwas erzählen, das nur du hören wirst. Eine Geschichte, die genau für diesen Moment entstanden ist...",
        "Schhhh... die Nacht ist da, und mit ihr eine Geschichte, die auf dich gewartet hat. Ich bin Caye, und heute Nacht reisen wir gemeinsam...",
        "Liegst du schon im Bett? Perfekt. Ich bin Caye, und heute Nacht habe ich eine Geschichte nur für dich. Eine Geschichte, die jetzt beginnt...",
        "Schließ kurz die Augen... hast du sie geschlossen? Gut. Ich bin Caye, und heute Nacht gehen wir an einen ganz besonderen Ort. Kommst du mit?",
        "Hey, kleiner Träumer... ich bin Caye. Heute Nacht wartet ein Abenteuer auf uns. Bist du bereit?",
    ],
    "zh": [
        "嘘……你还醒着吗？真幸运，因为今晚我为你准备了一些特别的东西。我是Caye，我们一起去发现一个精彩的故事吧……",
        "你好，我是Caye。月亮已经挂在天空中，星星们都在等着你。闭上小眼睛，让我带你去旅行……",
        "今晚，在你闭上眼睛之前，我，Caye，想告诉你一个只有你才能听到的故事。一个就为这一刻诞生的故事……",
        "嘘……夜晚来临了，带来了一个一直在等你的故事。我是Caye，今晚我们一起旅行……",
        "你已经躺在床上了吗？太好了。我是Caye，今晚我为你保存了一个专属故事。一个现在就要开始的故事……",
        "闭上眼睛一下……闭上了吗？很好。我是Caye，今晚我们要去一个非常特别的地方。你愿意和我一起去吗？",
        "小梦想家，你好……我是Caye。今晚有一段冒险在等着我们。准备好了吗？",
    ],
}


def get_random_intro(lang: str) -> str:
    intros = NARRATOR_INTROS.get(lang, NARRATOR_INTROS["es"])
    return random.choice(intros)


# ──────────────────────────────────────────────
# CONFIGURACIÓN DE IDIOMAS
# ──────────────────────────────────────────────

LANGUAGES = {
    "es": {"name": "español",  "voice_code": "es-ES-Neural2-C", "prompt_lang": "español"},
    "en": {"name": "English",  "voice_code": "en-GB-Neural2-C", "prompt_lang": "English"},
    "fr": {"name": "français", "voice_code": "fr-FR-Neural2-C", "prompt_lang": "français"},
    "de": {"name": "Deutsch",  "voice_code": "de-DE-Neural2-C", "prompt_lang": "Deutsch"},
    "zh": {"name": "中文",      "voice_code": "cmn-CN-Neural2-D","prompt_lang": "中文（普通话）"},
}

DEFAULT_TOPICS = {
    "es": {"topic": "el miedo a la oscuridad",    "title": "Caye y la linterna mágica"},
    "en": {"topic": "sharing with others",         "title": "Alvaro and the Magic Cake"},
    "fr": {"topic": "le courage face à l'inconnu", "title": "Caye et la forêt enchantée"},
    "de": {"topic": "Geduld und Geschwisterliebe", "title": "Alvaro und der schlafende Riese"},
    "zh": {"topic": "勇气和兄弟姐妹之间的爱",        "title": "Caye和月亮的秘密"},
}

# ──────────────────────────────────────────────
# PROMPT
# ──────────────────────────────────────────────

STORY_PROMPT_TEMPLATE = """
Eres una narradora de cuentos infantiles profesional. Tu estilo es muy similar al de Raquel Tolmo
en su podcast "Cuentos Infantiles Para Dormir": voz cálida, cercana, con ritmo pausado, lenguaje
accesible, personajes entrañables, y siempre con un mensaje emocional o de valores claro al final.

Escribe un cuento infantil COMPLETO en {lang} con estas características:

TÍTULO: {title}
TEMA / VALOR: {topic}
EDAD OBJETIVO: mezcla de 3-5 y 5-8 años (accesible para pequeños, rico para mayores)
DURACIÓN OBJETIVO: 10-14 minutos al escucharlo (~1.200-1.500 palabras)
ESTILO: mezcla de aventura/fantasía con valores y emociones

PROTAGONISTAS (MUY IMPORTANTE):
Los personajes principales son CAYE y ÁLVARO, dos hermanos:
- CAYE: 7 años. Dulce, responsable, empática, protectora. Le encanta cuidar a su hermano,
  le gustan los animales, las flores y la magia. Siempre piensa antes de actuar.
- ÁLVARO: 3 años (casi 4). Travieso, curioso, divertido, impulsivo. Se mete en líos sin
  querer, pregunta el porqué de todo, tiene una risa contagiosa. Adora a su hermana mayor.
- A veces el cuento es protagonizado solo por CAYE, a veces solo por ÁLVARO,
  a veces por los DOS JUNTOS. Elige según el título y el tema.
- Cuando están juntos: se cuidan, se complementan, a veces discuten pero siempre
  se quieren con locura.
- Los demás personajes pueden ser animales fantásticos, hadas, dragones amigos,
  duendes, estrellas parlantes, etc.

ESTRUCTURA OBLIGATORIA:
1. INTRODUCCIÓN CÁLIDA (2-3 párrafos): Presenta al protagonista/s y su mundo.
   Crea inmediatamente conexión emocional.
2. PROBLEMA O AVENTURA (4-5 párrafos): El personaje se enfrenta a un reto, miedo,
   o situación que le hace crecer. Incluye un elemento de fantasía o magia.
3. DESARROLLO (3-4 párrafos): El personaje intenta resolver el problema, con ayuda
   de amigos o de su hermano/a. Momentos de emoción genuina.
4. RESOLUCIÓN Y MENSAJE (2-3 párrafos): El problema se resuelve de forma satisfactoria.
   El personaje aprende algo importante sobre sí mismo o sobre la vida.
5. CIERRE PARA DORMIR (1 párrafo): Termina con una frase suave y relajante que invite
   a los niños a cerrar los ojos y soñar. Despedida hasta la próxima noche.

REGLAS DE ESCRITURA:
- Narración en tercera persona, con voz cálida de narradora externa
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

    narrator_intro = f"\n\n{get_random_intro(lang)}\n\n"
    story_with_intro = re.sub(r'^(# .+\n)', r'\1' + narrator_intro, story_text, count=1)

    result = {
        "lang": lang,
        "title": title,
        "topic": topic,
        "text": story_with_intro,
        "word_count": len(story_text.split()),
        "voice_code": lang_config["voice_code"],
        "generated_at": datetime.now().isoformat(),
        "model": "claude-opus-4-5",
        "podcast_name": "Las aventuras de Caye y Alvarito",
    }

    print(f"  ✅ Cuento generado: {result['word_count']} palabras")
    return result


def save_story(story_data: dict, output_dir: str = "stories") -> Path:
    lang = story_data["lang"]
    slug = re.sub(r'[^\w\s-]', '', story_data["title"].lower())
    slug = re.sub(r'[\s]+', '_', slug.strip())[:50]

    lang_dir = Path(output_dir) / lang
    lang_dir.mkdir(parents=True, exist_ok=True)

    txt_path = lang_dir / f"{slug}.txt"
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(story_data["text"])

    json_path = lang_dir / f"{slug}.json"
    meta = {k: v for k, v in story_data.items() if k != "text"}
    meta["txt_file"] = str(txt_path)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    print(f"  💾 Guardado: {txt_path}")
    return txt_path


def generate_all_languages(api_key: str = None) -> list:
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
        description="Genera cuentos infantiles para 'Las aventuras de Caye y Alvarito'"
    )
    parser.add_argument("--lang", choices=list(LANGUAGES.keys()))
    parser.add_argument("--topic")
    parser.add_argument("--title")
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--output-dir", default="stories")
    parser.add_argument("--api-key")

    args = parser.parse_args()

    print("🌙 Las aventuras de Caye y Alvarito — Generador de historias")
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


if __name__ == "__main__":
    main()
