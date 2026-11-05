# Gym AI MVP

MVP para validar si un LLM pequeño ejecutado localmente con [Ollama](https://ollama.com)
puede generar rutinas de gimnasio de buena calidad, usando
[exercises-dataset](https://github.com/hasaneyldrm/exercises-dataset) (1,324 ejercicios)
como fuente de ejercicios.

Pipeline: `preferencias → filtrado (SQLite) → prompt → Ollama → validación (Pydantic) → rutina`.

## Estructura

```
back/   API FastAPI + SQLite (src, tests, scripts, data, Dockerfile)
front/  Next.js
docker-compose.yml
```

## Setup

Todos los comandos de Python se ejecutan desde `back/`.

```bash
cd back
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

Asegúrate de tener [Ollama](https://ollama.com) corriendo localmente y el modelo de
`.env` descargado (`ollama pull <modelo>`).

## Uso

1. Importar el dataset a SQLite (solo la primera vez, o cuando cambie el dataset):

   ```bash
   python -m src.dataset_loader
   ```

2. Generar una rutina de forma interactiva:

   ```bash
   python -m src.main
   ```

3. Correr los tests offline (no requieren Ollama ni red):

   ```bash
   pytest
   ```

4. Correr los 10 casos de evaluación de calidad contra el LLM real (requiere Ollama
   corriendo y el dataset ya importado):

   ```bash
   python scripts/eval_cases.py
   ```

Cada generación (éxito o fallo) se guarda en `back/data/generations/` con las preferencias,
los candidatos enviados, el prompt, la respuesta cruda del modelo y el resultado de la
validación, para poder analizar el comportamiento del LLM.

## Web app (Next.js + API)

El frontend vive en `front/` (Next.js) y habla con una API FastAPI en `back/src/api.py`.
Se necesitan dos terminales:

```bash
# 1) API (desde back/, con el venv activo)
cd back
pip install -r requirements.txt
uvicorn src.api:app --reload --port 8001

# 2) Frontend
cd front
copy .env.local.example .env.local
npm install
npm run dev        # http://localhost:3000
```

Flujo: botón **Iniciar** → 5 preguntas (objetivo, nivel, días, duración, equipo) →
`POST /api/generate` → la rutina se muestra en tarjetas con GIF, músculo, series,
repeticiones y descanso. Los GIFs se cargan desde el repo del dataset (`MEDIA_BASE_URL`).

## Notas de diseño

- El dataset real **no tiene campo de dificultad** — el nivel del usuario no filtra
  ejercicios, solo ajusta sets/reps/descanso/cantidad de ejercicios y se comunica al LLM.
- El equipamiento del dataset tiene 28 valores granulares; `back/src/exercise_filter.py`
  mapea las 4 categorías de usuario (`full_gym`, `home`, `dumbbells`, `bodyweight`) a
  subconjuntos de esos valores.
- El LLM solo recibe una lista compacta de candidatos (id, nombre, grupo, target,
  equipo) y debe referenciar ejercicios exclusivamente por `exercise_id`. Nunca inventa
  ejercicios: eso lo garantiza `back/src/validator.py`.

## Idiomas (ES / EN)

El frontend tiene selector de idioma (arriba a la derecha). Las traducciones viven en
`front/lib/i18n.tsx`; la elección se guarda en `localStorage` y por defecto se usa el idioma
del navegador. El idioma se envía a la API (`language`) para que el LLM nombre la rutina y
los días en ese idioma. Los nombres de ejercicios y músculos vienen del dataset en inglés.

## Despliegue con Docker / Coolify

Archivos: `back/Dockerfile` (API), `front/Dockerfile` (Next.js standalone), `docker-compose.yml`,
`back/docker/entrypoint.sh` (importa el dataset en el primer arranque).

Local: `docker compose --env-file back/.env up --build` (con las variables de `back/.env.example` definidas).

En Coolify:
1. New Resource → repositorio → Build Pack **Docker Compose** (`docker-compose.yml`).
2. Asigna dominios: servicio `web` → `https://tudominio.com` (puerto 3000) y servicio
   `api` → `https://api.tudominio.com` (puerto 8001).
3. Variables de entorno: `NEXT_PUBLIC_API_URL=https://api.tudominio.com`,
   `CORS_ORIGINS=https://tudominio.com`, `LLM_API_URL`, `LLM_API_KEY`
   (o `OLLAMA_BASE_URL` + `OLLAMA_MODEL`). Marca `NEXT_PUBLIC_API_URL` como disponible en
   build time; si la cambias, hay que reconstruir el servicio `web` (carpeta `front/`).
4. El volumen `gym_data` persiste la base SQLite y las generaciones. Para reimportar el
   dataset define `FORCE_DATASET_IMPORT=1` en un despliegue.
