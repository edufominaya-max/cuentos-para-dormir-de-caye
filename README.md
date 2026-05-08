# 🌙 Cuentos para dormir de Caye

> Cuentos infantiles originales generados con IA, narrados con voz femenina cálida,
> en 5 idiomas: español, inglés, francés, alemán y chino.
> Distribuidos en Spotify, Apple Podcasts, Amazon Music, iVoox y más.

---

## 📁 Estructura del proyecto

```
cuentos-para-dormir-de-caye/
├── scripts/
│   ├── generate_story.py      # Genera cuentos con Claude API
│   ├── generate_audio.py      # Convierte a MP3 con Google TTS (gratis)
│   ├── generate_cover.py      # Genera carátulas JPG con DALL-E 3 (~$0.04/imagen)
│   ├── upload_podcast.py      # Sube a RSS / Buzzsprout
│   └── run_pipeline.py        # Script maestro (ejecuta todo)
├── stories/
│   ├── es/                    # Cuentos en español (.txt + .json)
│   ├── en/                    # Cuentos en inglés
│   ├── fr/                    # Cuentos en francés
│   ├── de/                    # Cuentos en alemán
│   └── zh/                    # Cuentos en chino
├── audio/
│   ├── es/                    # MP3 en español
│   ├── en/                    # MP3 en inglés
│   └── ...
├── covers/
│   ├── es/                    # Carátulas JPG en español
│   └── ...
├── logs/                      # Logs de cada episodio generado
├── feed.xml                   # RSS feed para distribución
└── .github/workflows/
    └── generate_episode.yml   # Automatización semanal
```

---

## 🚀 Setup inicial (una sola vez)

### 1. Clonar el repositorio
```bash
git clone https://github.com/TU_USUARIO/cuentos-para-dormir-de-caye.git
cd cuentos-para-dormir-de-caye
```

### 2. Instalar dependencias
```bash
pip install anthropic openai google-cloud-texttospeech pydub pillow requests mutagen
sudo apt-get install ffmpeg  # Linux / Mac: brew install ffmpeg
```

### 3. Configurar claves de API

Crea un archivo `.env` (nunca lo subas a GitHub):
```bash
# .env
ANTHROPIC_API_KEY=sk-ant-...        # https://console.anthropic.com
OPENAI_API_KEY=sk-...               # https://platform.openai.com (para DALL-E 3)
GOOGLE_APPLICATION_CREDENTIALS=path/to/google-key.json  # Para Google TTS
```

Para Google TTS (gratis 1M chars/mes):
1. Ve a https://console.cloud.google.com
2. Activa la API "Cloud Text-to-Speech"
3. Crea una cuenta de servicio → descarga el JSON de credenciales
4. `export GOOGLE_APPLICATION_CREDENTIALS="path/to/key.json"`

### 4. Configurar GitHub Secrets (para automatización)
En GitHub → Settings → Secrets and variables → Actions:
- `ANTHROPIC_API_KEY` → tu clave de Anthropic
- `OPENAI_API_KEY` → tu clave de OpenAI
- `GOOGLE_CREDENTIALS_JSON` → contenido completo del JSON de Google Cloud

---

## 🎙️ Uso manual

### Generar episodios en todos los idiomas de una vez:
```bash
cd scripts
python run_pipeline.py --all --episode 1
```

### Generar un episodio concreto:
```bash
python run_pipeline.py \
  --lang es \
  --topic "el miedo a la oscuridad" \
  --title "Luca y la linterna mágica" \
  --episode 1
```

### Solo el texto (sin audio ni carátula — rápido y gratis):
```bash
python run_pipeline.py --all --skip-audio --skip-cover
```

### Solo el audio (a partir de texto ya generado):
```bash
python generate_audio.py --input stories/es/luca_y_la_linterna_magica.txt
```

### Solo la carátula:
```bash
python generate_cover.py --story stories/es/luca_y_la_linterna_magica.json
```

---

## 📡 Distribución del podcast

### Opción A: Spotify for Podcasters (gratis, recomendada para empezar)
1. Ve a https://podcasters.spotify.com
2. Crea tu podcast "Cuentos para dormir de Caye"
3. En vez de subir el RSS, sube los MP3 directamente desde su panel
4. Desde ahí distribuye a: Spotify, Amazon Music, Apple Podcasts

### Opción B: RSS propio (máximo control)
1. Ejecuta `python upload_podcast.py --platform rss`
2. Sube el `feed.xml` a GitHub Pages:
   ```bash
   # En GitHub → Settings → Pages → Source: main branch
   # Tu feed quedará en: https://TU_USUARIO.github.io/cuentos-para-dormir-de-caye/feed.xml
   ```
3. Envía la URL del feed a cada plataforma:
   - **Spotify**: podcasters.spotify.com → "Add existing podcast"
   - **Apple Podcasts**: podcastsconnect.apple.com
   - **Amazon Music**: music.amazon.com/podcasts/submit
   - **iVoox**: ivoox.com → Mi cuenta → Importar RSS

### Opción C: Buzzsprout (API oficial, ~$12/mes, todo automático)
```bash
python upload_podcast.py \
  --platform buzzsprout \
  --mp3 audio/es/episodio1.mp3 \
  --cover covers/es/episodio1.jpg \
  --title "Luca y la linterna mágica" \
  --topic "el miedo a la oscuridad" \
  --lang es --episode 1 \
  --buzzsprout-token TU_TOKEN \
  --buzzsprout-id TU_PODCAST_ID
```

---

## 💰 Costes por episodio

| Componente | Herramienta | Coste |
|---|---|---|
| Texto (~1.400 palabras) | Claude claude-opus-4-5 | ~$0.05 |
| Audio (~13 min) | Google TTS Neural2 | **GRATIS** (1M chars/mes) |
| Carátula JPG | DALL-E 3 | ~$0.04 |
| Distribución | Spotify for Podcasters | **GRATIS** |
| **Total por episodio** | | **~$0.09** |
| **100 episodios** | | **~$9** |

---

## 🤖 Automatización semanal

El workflow `.github/workflows/generate_episode.yml` genera automáticamente
un nuevo episodio cada lunes a las 08:00 (Madrid) y hace commit al repo.

Para activarlo, asegúrate de tener los Secrets configurados en GitHub
(ver sección Setup → paso 4).

También puedes lanzarlo manualmente desde GitHub → Actions → "Generar episodio semanal".

---

## 🎭 Voces disponibles

| Idioma | Voz Google TTS | Característica |
|---|---|---|
| Español | es-ES-Neural2-C | Mujer, española, cálida |
| Inglés | en-GB-Neural2-C | Mujer, británica, suave |
| Francés | fr-FR-Neural2-C | Mujer, francesa, musical |
| Alemán | de-DE-Neural2-C | Mujer, alemana, clara |
| Chino | cmn-CN-Neural2-D | Mujer, mandarín, suave |

---

## 📜 Licencia

Los cuentos generados son originales y propiedad de "Cuentos para dormir de Caye".
Los scripts son de uso libre.

---

*🌙 Hasta la próxima noche, pequeños soñadores. Dulces sueños.*
