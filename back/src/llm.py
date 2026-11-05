"""LLM providers behind a single function. workout_generator.py only depends on
`generate_workout_json`.

Provider order: OpenAI (OPENAI_API_KEY) -> remote endpoint (LLM_API_URL) -> Ollama."""
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
    OPENAI_API_KEY,
    OPENAI_BASE_URL,
    OPENAI_MAX_OUTPUT_TOKENS,
    OPENAI_MODEL,
    OPENAI_REASONING_EFFORT,
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


def _workout_json_schema(candidate_ids: list[int] | None) -> dict:
    """Strict JSON schema for the workout. When the candidate ids are known, exercise_id is
    an enum of them, so the model cannot return an id outside the provided list."""
    exercise_id: dict = {"type": "integer"}
    if candidate_ids:
        exercise_id["enum"] = sorted(set(candidate_ids))
    exercise = {
        "type": "object",
        "properties": {
            "exercise_id": exercise_id,
            "sets": {"type": "integer"},
            "reps": {"type": "string"},
            "rest_seconds": {"type": "integer"},
        },
        "required": ["exercise_id", "sets", "reps", "rest_seconds"],
        "additionalProperties": False,
    }
    day = {
        "type": "object",
        "properties": {
            "day": {"type": "integer"},
            "name": {"type": "string"},
            "exercises": {"type": "array", "items": exercise},
        },
        "required": ["day", "name", "exercises"],
        "additionalProperties": False,
    }
    return {
        "type": "object",
        "properties": {"name": {"type": "string"}, "days": {"type": "array", "items": day}},
        "required": ["name", "days"],
        "additionalProperties": False,
    }


def _generate_openai(prompt: str, candidate_ids: list[int] | None, model: str | None) -> str:
    # Plain REST call (httpx is already a dependency). No `temperature`: GPT-5 reasoning
    # models only accept the default.
    body: dict = {
        "model": model or OPENAI_MODEL,
        "messages": [
            {"role": "system", "content": _REMOTE_SYSTEM_INSTRUCTION},
            {"role": "user", "content": prompt},
        ],
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "workout",
                "strict": True,
                "schema": _workout_json_schema(candidate_ids),
            },
        },
        "max_completion_tokens": OPENAI_MAX_OUTPUT_TOKENS,
    }
    if OPENAI_REASONING_EFFORT:
        body["reasoning_effort"] = OPENAI_REASONING_EFFORT

    response = httpx.post(
        f"{OPENAI_BASE_URL}/chat/completions",
        headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
        json=body,
        timeout=LLM_TIMEOUT_SECONDS,
    )
    if response.status_code >= 400:
        raise RuntimeError(f"OpenAI HTTP {response.status_code}: {response.text[:500]}")

    choice = response.json()["choices"][0]
    message = choice["message"]
    if message.get("refusal"):
        raise RuntimeError(f"OpenAI rechazó la solicitud: {message['refusal']}")
    if choice.get("finish_reason") == "length":
        raise RuntimeError(
            "OpenAI cortó la respuesta por límite de tokens; "
            "sube OPENAI_MAX_OUTPUT_TOKENS o baja OPENAI_REASONING_EFFORT."
        )
    return message.get("content") or ""


def generate_workout_json(
    prompt: str,
    model: str | None = None,
    candidate_ids: list[int] | None = None,
) -> str:
    if OPENAI_API_KEY:
        return _generate_openai(prompt, candidate_ids, model)

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
