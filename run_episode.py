#!/usr/bin/env python3
"""
run_episode.py — Lee episodes_config.py y genera el próximo episodio pendiente.
Llamado desde GitHub Actions en el Paso 1.

Uso:
    python run_episode.py --episode 1
    python run_episode.py --episode 1 --skip-cover
"""

import argparse
import subprocess
import sys

sys.path.insert(0, '.')
from episodes_config import get_next_episode


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--episode", type=int, default=1)
    parser.add_argument("--skip-cover", action="store_true")
    args = parser.parse_args()

    ep = get_next_episode()

    if ep is None:
        print("✅ Todos los episodios ya están generados")
        sys.exit(0)

    print(f"🌙 Generando episodio #{ep['episode']}: {ep['title']}")
    print(f"   Tema: {ep['topic']}")

    cmd = [
        "python", "run_pipeline.py",
        "--lang", ep["lang"],
        "--topic", ep["topic"],
        "--title", ep["title"],
        "--episode", str(ep["episode"]),
        "--skip-audio",
        "--skip-upload",
    ]

    if args.skip_cover:
        cmd.append("--skip-cover")

    result = subprocess.run(cmd)
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
