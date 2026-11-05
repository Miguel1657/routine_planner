"""Orchestrates preferences -> candidates -> prompt -> LLM -> validation -> Workout.

This is the reusable core (`generate_workout`) that main.py, tests, and a future
FastAPI endpoint can all call the same way — it knows nothing about the CLI.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from src.config import GENERATIONS_DIR, LLM_LABEL
from src.database import get_session
from src.exercise_filter import get_exercise_candidates
from src.llm import generate_workout_json
from src.prompt_builder import build_prompt
from src.schemas import CandidateExercise, GenerationRecord, Preferences
from src.validator import validate_workout

MAX_ATTEMPTS = 2


def _save_generation(record: GenerationRecord, file_stub: str, attempt: int) -> Path:
    GENERATIONS_DIR.mkdir(parents=True, exist_ok=True)
    suffix = "" if attempt == 1 else f"_attempt{attempt}"
    path = GENERATIONS_DIR / f"generation_{file_stub}{suffix}.json"
    path.write_text(record.model_dump_json(indent=2), encoding="utf-8")
    return path


def generate_workout(preferences: Preferences, max_attempts: int = MAX_ATTEMPTS) -> GenerationRecord:
    with get_session() as session:
        candidates = get_exercise_candidates(preferences, session)
        candidate_dtos = [
            CandidateExercise(
                id=exercise.id,
                name=exercise.name,
                body_part=exercise.body_part,
                target_muscle=exercise.target_muscle,
                equipment=exercise.equipment,
            )
            for exercise in candidates
        ]

    prompt = build_prompt(preferences, candidates)

    generated_at = datetime.now()
    file_stub = generated_at.strftime("%Y-%m-%d_%H%M%S")

    record: GenerationRecord | None = None
    for attempt in range(1, max_attempts + 1):
        raw_response = ""
        try:
            raw_response = generate_workout_json(
                prompt, candidate_ids=[exercise.id for exercise in candidates]
            )
            workout, errors = validate_workout(raw_response, preferences, candidates)
        except Exception as exc:  # LLM/connection failures are also part of what we observe
            workout, errors = None, [f"Error llamando al LLM: {exc}"]

        record = GenerationRecord(
            preferences=preferences,
            candidate_exercises=candidate_dtos,
            model=LLM_LABEL,
            prompt=prompt,
            response=raw_response,
            workout=workout,
            validation_errors=errors,
            attempt=attempt,
            timestamp=generated_at.isoformat(),
        )
        _save_generation(record, file_stub, attempt)

        if workout is not None:
            break

    assert record is not None
    return record
