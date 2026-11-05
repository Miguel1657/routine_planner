"""Validation pipeline: raw LLM text -> JSON -> Pydantic -> business rules -> Workout.

Never raises for expected LLM failure modes (broken JSON, invented exercise_id, etc.) —
those are returned as an error list so the caller can log them and retry, per the
"never hide LLM failures" requirement.
"""
from __future__ import annotations

import json
import re

from pydantic import ValidationError

from src.models import Exercise
from src.schemas import Preferences, Workout

# Plain reps ("8-10"), timed holds ("30-60s", "30 seconds") and AMRAP are all legitimate
# prescriptions — planks and similar isometrics are normally programmed by time.
_REPS_PATTERN = re.compile(
    r"^(\d+(-\d+)?|\d+(-\d+)?\s*(s|sec|secs|seconds?|segundos?)|amrap|as many .*possible|max)$",
    re.IGNORECASE,
)
_MAX_REASONABLE_REST_SECONDS = 600
_CODE_FENCE_PATTERN = re.compile(r"^\s*```(?:json)?\s*(.*?)\s*```\s*$", re.DOTALL | re.IGNORECASE)


def _strip_code_fence(raw_response: str) -> str:
    """Some models wrap the JSON in a markdown fence even when told not to. The raw
    response is still saved untouched in the generation record."""
    match = _CODE_FENCE_PATTERN.match(raw_response)
    return match.group(1) if match else raw_response


def validate_workout(
    raw_response: str,
    preferences: Preferences,
    candidates: list[Exercise],
) -> tuple[Workout | None, list[str]]:
    try:
        data = json.loads(_strip_code_fence(raw_response))
    except json.JSONDecodeError as exc:
        return None, [f"JSON inválido: {exc}"]

    try:
        workout = Workout.model_validate(data)
    except ValidationError as exc:
        return None, [f"Estructura inválida (Pydantic): {exc}"]

    errors = _check_business_rules(workout, preferences, candidates)
    if errors:
        return None, errors
    return workout, []


def _check_business_rules(
    workout: Workout,
    preferences: Preferences,
    candidates: list[Exercise],
) -> list[str]:
    errors: list[str] = []
    candidate_ids = {exercise.id for exercise in candidates}

    if len(workout.days) != preferences.days_per_week:
        errors.append(
            f"Número de días incorrecto: esperado {preferences.days_per_week}, "
            f"recibido {len(workout.days)}"
        )

    for day in workout.days:
        if not day.exercises:
            errors.append(f"Día {day.day} ('{day.name}') no tiene ejercicios")

        for exercise in day.exercises:
            if exercise.exercise_id not in candidate_ids:
                errors.append(
                    f"exercise_id inválido: {exercise.exercise_id} (día {day.day}) "
                    "no pertenece al conjunto de candidatos proporcionado"
                )
            if not _REPS_PATTERN.match(exercise.reps.strip()):
                errors.append(
                    f"reps con formato inesperado: '{exercise.reps}' "
                    f"(día {day.day}, exercise_id {exercise.exercise_id})"
                )
            if exercise.rest_seconds > _MAX_REASONABLE_REST_SECONDS:
                errors.append(
                    f"rest_seconds fuera de rango razonable: {exercise.rest_seconds}s "
                    f"(día {day.day}, exercise_id {exercise.exercise_id})"
                )

    return errors
