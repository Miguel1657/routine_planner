"""Thin wrapper around the Ollama client. workout_generator.py only depends on
`generate_workout_json`, so swapping HTTP clients or pointing at a remote Ollama
instance later is a one-file change."""
from __future__ import annotations

import httpx
import ollama

from src.config import (
    LLM_API_KEY,
    LLM_API_URL,
    LLM_TEMPERATURE,
    LLM_TIMEOUT_SECONDS,
    OLLAMA_BASE_URL,
    OLLAMA_MODEL,
)

_REMOTE_SYSTEM_INSTRUCTION = (
    "Eres un entrenador personal. Responde UNICAMENTE con un objeto JSON valido, "
    "sin markdown, sin bloques de codigo y sin texto adicional."
)
_RESPONSE_TEXT_KEYS = ("response", "text", "output", "content", "result", "message", "answer")


class LLMConfigError(RuntimeError):
    pass


def _extract_text(payload) -> str:
    if isinstance(payload, str):
        return payload
    if isinstance(payload, dict):
        for key in _RESPONSE_TEXT_KEYS:
            if key in payload:
                return _extract_text(payload[key])
    raise ValueError(f"No se pudo extraer el texto de la respuesta del LLM remoto: {payload!r}"[:500])


def _generate_remote(prompt: str) -> str:
    if not LLM_API_KEY:
        raise LLMConfigError("LLM_API_KEY no está configurado. Defínelo en tu archivo .env.")
    response = httpx.post(
        LLM_API_URL,
        headers={"x-api-key": LLM_API_KEY},
        json={
            "system_instruction": _REMOTE_SYSTEM_INSTRUCTION,
            "user_instruction": prompt,
            "temperature": LLM_TEMPERATURE,
        },
        timeout=LLM_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    try:
        return _extract_text(response.json())
    except ValueError:
        if response.headers.get("content-type", "").startswith("application/json"):
            raise
        return response.text


def generate_workout_json(prompt: str, model: str | None = None) -> str:
    if LLM_API_URL:
        return _generate_remote(prompt)

    model_name = model or OLLAMA_MODEL
    if not model_name:
        raise LLMConfigError(
            "OLLAMA_MODEL no está configurado. Define OLLAMA_MODEL en tu archivo .env."
        )

    client = ollama.Client(host=OLLAMA_BASE_URL)
    response = client.generate(model=model_name, prompt=prompt, format="json", stream=False)
    return response["response"]
