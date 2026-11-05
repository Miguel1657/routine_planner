"""Builds the prompt sent to the LLM. Kept independent of the Ollama client so the
prompt itself can be inspected/tested without a model running."""
from __future__ import annotations

from src.exercise_filter import estimate_exercises_per_day
from src.models import Exercise
from src.schemas import Goal, Level, Preferences

# Rough sets/reps/rest guidance per goal — the LLM decides the exact numbers per
# exercise, this just anchors it to sane ranges instead of guessing from scratch.
_GOAL_GUIDANCE = {
    Goal.STRENGTH: "3-5 sets of 3-6 reps, rest 120-240s between sets.",
    Goal.HYPERTROPHY: "3-4 sets of 8-12 reps, rest 60-120s between sets.",
    Goal.POWER: "3-5 sets of 1-5 reps of explosive/ballistic movement, rest 120-240s between sets.",
    Goal.ENDURANCE: "2-3 sets of 15-25 reps, rest 30-60s between sets.",
    Goal.GENERAL_FITNESS: "2-4 sets of 8-15 reps, rest 45-90s between sets.",
}

# The dataset has no difficulty rating, so level cannot filter exercises. It only
# adjusts overall volume/complexity guidance given to the model.
_LEVEL_GUIDANCE = {
    Level.BEGINNER: (
        "Beginner: favor simpler, more stable movements from the list, moderate volume, "
        "and be conservative with total exercises per day."
    ),
    Level.INTERMEDIATE: "Intermediate: normal volume and exercise variety.",
    Level.ADVANCED: (
        "Advanced: can handle higher volume, more exercises per day, and more technically "
        "demanding movements from the list."
    ),
}

CRITICAL_RULE = """CRITICAL RULES:
- USE ONLY THE EXERCISES PROVIDED BELOW. DO NOT INVENT EXERCISES.
- EVERY EXERCISE IN YOUR RESPONSE MUST BE REFERENCED BY ITS exercise_id FROM THE LIST BELOW.
- DO NOT USE ANY exercise_id THAT IS NOT IN THE LIST BELOW.
- Respond with ONLY a single JSON object. No markdown, no code fences, no commentary."""


def _format_candidates(candidates: list[Exercise]) -> str:
    lines = ["ID | Name | Body part | Target muscle | Equipment"]
    for exercise in candidates:
        lines.append(
            f"{exercise.id} | {exercise.name} | {exercise.body_part} | "
            f"{exercise.target_muscle} | {exercise.equipment}"
        )
    return "\n".join(lines)


def _output_schema_example() -> str:
    return """{
  "name": "string - short workout program name",
  "days": [
    {
      "day": 1,
      "name": "string - e.g. 'Chest and Triceps'",
      "exercises": [
        {
          "exercise_id": 237,
          "sets": 4,
          "reps": "8-10",
          "rest_seconds": 90
        }
      ]
    }
  ]
}"""


_LANGUAGE_NAMES = {"es": "Spanish", "en": "English"}


def build_prompt(preferences: Preferences, candidates: list[Exercise]) -> str:
    exercises_per_day = estimate_exercises_per_day(preferences.session_duration_minutes)

    preferences_block = "\n".join([
        f"Goal: {preferences.goal.value}",
        f"Level: {preferences.level.value}",
        f"Days per week: {preferences.days_per_week}",
        f"Session duration: {preferences.session_duration_minutes} minutes",
        f"Equipment available: {', '.join(p.value for p in preferences.equipment)}",
    ])

    return f"""You are a fitness coach building a structured workout program.

PREFERENCES:
{preferences_block}

PRESCRIPTION GUIDANCE:
- {_GOAL_GUIDANCE[preferences.goal]}
- {_LEVEL_GUIDANCE[preferences.level]}
- Aim for about {exercises_per_day} exercises per day, appropriate for a
  {preferences.session_duration_minutes}-minute session.

AVAILABLE EXERCISES ({len(candidates)} candidates):
{_format_candidates(candidates)}

{CRITICAL_RULE}

The program must have exactly {preferences.days_per_week} day(s).
Write the program "name" and every day "name" in {_LANGUAGE_NAMES[preferences.language]}. Keep all JSON keys in English.

Respond with ONLY a JSON object matching this exact structure:
{_output_schema_example()}"""
