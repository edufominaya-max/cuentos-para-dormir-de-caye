#!/usr/bin/env python3
"""
episodes_config.py — Lista de episodios planificados para
"Las aventuras de Caye y Alvarito".

El pipeline lee este archivo y genera los episodios en orden,
saltando los que ya existen en stories/es/.
"""

EPISODES = [
    {
        "episode": 1,
        "lang": "es",
        "title": "El dragón verde del volcán",
        "topic": "la valentía ante lo desconocido",
    },
    {
        "episode": 2,
        "lang": "es",
        "title": "La estrella que cayó al jardín",
        "topic": "ayudar a los demás sin esperar nada a cambio",
    },
    {
        "episode": 3,
        "lang": "es",
        "title": "El bosque que se durmió",
        "topic": "la paciencia y esperar tu momento",
    },
    {
        "episode": 4,
        "lang": "es",
        "title": "El gigante de nubes",
        "topic": "los celos entre hermanos y el amor que los supera",
    },
    {
        "episode": 5,
        "lang": "es",
        "title": "El río que sabía secretos",
        "topic": "escuchar antes de actuar",
    },
    {
        "episode": 6,
        "lang": "es",
        "title": "La luna que se escondió",
        "topic": "el miedo a separarse de mamá",
    },
    {
        "episode": 7,
        "lang": "es",
        "title": "Las piedras del camino mágico",
        "topic": "la generosidad",
    },
    {
        "episode": 8,
        "lang": "es",
        "title": "El puente de los sueños",
        "topic": "superar las pesadillas",
    },
    {
        "episode": 9,
        "lang": "es",
        "title": "La semilla más pequeña",
        "topic": "la perseverancia",
    },
    {
        "episode": 10,
        "lang": "es",
        "title": "El hada sin voz",
        "topic": "defender a quien no puede hablar por sí mismo",
    },
    {
        "episode": 11,
        "lang": "es",
        "title": "La noche de la tormenta de estrellas",
        "topic": "el miedo a los truenos y encontrar seguridad en la familia",
    },
    {
        "episode": 12,
        "lang": "es",
        "title": "El último deseo del verano",
        "topic": "aprender a decir adiós y que los finales también son bonitos",
    },
]


def get_next_episode() -> dict | None:
    """
    Devuelve el próximo episodio que no se ha generado aún.
    Comprueba si existe el .txt en stories/es/.
    """
    import re
    from pathlib import Path

    for ep in EPISODES:
        slug = re.sub(r'[^\w\s-]', '', ep["title"].lower())
        slug = re.sub(r'[\s]+', '_', slug.strip())[:50]
        txt_path = Path("stories") / ep["lang"] / f"{slug}.txt"

        if not txt_path.exists():
            return ep

    return None  # Todos generados


def get_all_pending() -> list:
    """Devuelve todos los episodios pendientes de generar."""
    import re
    from pathlib import Path

    pending = []
    for ep in EPISODES:
        slug = re.sub(r'[^\w\s-]', '', ep["title"].lower())
        slug = re.sub(r'[\s]+', '_', slug.strip())[:50]
        txt_path = Path("stories") / ep["lang"] / f"{slug}.txt"

        if not txt_path.exists():
            pending.append(ep)

    return pending


if __name__ == "__main__":
    next_ep = get_next_episode()
    if next_ep:
        print(f"Próximo episodio: #{next_ep['episode']} — {next_ep['title']}")
    else:
        print("✅ Todos los episodios generados")

    pending = get_all_pending()
    print(f"\nPendientes: {len(pending)}/12")
    for ep in pending:
        print(f"  #{ep['episode']} — {ep['title']}")
