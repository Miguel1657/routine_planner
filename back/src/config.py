"""Central configuration loaded from environment variables / .env."""
from pathlib import Path

from dotenv import load_dotenv
import os

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

# OpenAI (primary provider). When OPENAI_API_KEY is set it takes precedence over the
# remote endpoint and Ollama. Provider order: OpenAI -> remote LLM_API_URL -> Ollama.
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5-nano")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
# Reasoning models bill their "thinking" tokens as output. minimal|low|medium|high; empty = model default.
OPENAI_REASONING_EFFORT = os.getenv("OPENAI_REASONING_EFFORT", "low")
# Cap includes reasoning tokens, so keep it generous.
OPENAI_MAX_OUTPUT_TOKENS = int(os.getenv("OPENAI_MAX_OUTPUT_TOKENS", "16000"))

# Remote LLM endpoint (POST {system_instruction, user_instruction, temperature}, x-api-key header).
# When LLM_API_URL is set it takes precedence over Ollama.
LLM_API_URL = os.getenv("LLM_API_URL", "")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.1"))
LLM_TIMEOUT_SECONDS = float(os.getenv("LLM_TIMEOUT_SECONDS", "300"))
LLM_LABEL = OPENAI_MODEL if OPENAI_API_KEY else ("remote-api" if LLM_API_URL else OLLAMA_MODEL)

EXERCISES_DATASET_URL = os.getenv(
    "EXERCISES_DATASET_URL",
    "https://raw.githubusercontent.com/hasaneyldrm/exercises-dataset/main/data/exercises.json",
)

DATABASE_PATH = PROJECT_ROOT / os.getenv("DATABASE_PATH", "data/app.db")
GENERATIONS_DIR = PROJECT_ROOT / os.getenv("GENERATIONS_DIR", "data/generations")
RAW_DATASET_PATH = PROJECT_ROOT / "data" / "raw" / "exercises.json"

# Exercise images/GIFs are stored as paths relative to the dataset repo root.
MEDIA_BASE_URL = os.getenv(
    "MEDIA_BASE_URL",
    "https://raw.githubusercontent.com/hasaneyldrm/exercises-dataset/main/",
)
CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
    if origin.strip()
]
