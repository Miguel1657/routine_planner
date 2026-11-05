"""Runs the 10 evaluation cases from instrucciones.txt (§17) against the real LLM via
Ollama, and prints a structural/fidelity summary for manual quality scoring (1-5).

Requires: Ollama running with OLLAMA_MODEL pulled, and the dataset already imported
(`python -m src.dataset_loader`). Not a pytest suite — this is slow and non-deterministic
by nature (it's the point: we want to observe how the model actually behaves).

Usage:
    python scripts/eval_cases.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.exercise_filter import resolve_equipment
from src.schemas import EquipmentProfile, Goal, Level, Preferences
from src.workout_generator import generate_workout

CASES: list[Preferences] = [
    Preferences(goal=Goal.HYPERTROPHY, level=Level.BEGINNER, days_per_week=3,
                session_duration_minutes=45, equipment=[EquipmentProfile.FULL_GYM]),
    Preferences(goal=Goal.HYPERTROPHY, level=Level.INTERMEDIATE, days_per_week=4,
                session_duration_minutes=60, equipment=[EquipmentProfile.FULL_GYM]),
    Preferences(goal=Goal.STRENGTH, level=Level.INTERMEDIATE, days_per_week=4,
                session_duration_minutes=60, equipment=[EquipmentProfile.FULL_GYM]),
    Preferences(goal=Goal.POWER, level=Level.ADVANCED, days_per_week=3,
                session_duration_minutes=60, equipment=[EquipmentProfile.FULL_GYM]),
    Preferences(goal=Goal.GENERAL_FITNESS, level=Level.BEGINNER, days_per_week=3,
                session_duration_minutes=45, equipment=[EquipmentProfile.HOME]),
    Preferences(goal=Goal.ENDURANCE, level=Level.INTERMEDIATE, days_per_week=5,
                session_duration_minutes=45, equipment=[EquipmentProfile.BODYWEIGHT]),
    Preferences(goal=Goal.HYPERTROPHY, level=Level.ADVANCED, days_per_week=6,
                session_duration_minutes=75, equipment=[EquipmentProfile.FULL_GYM]),
    Preferences(goal=Goal.STRENGTH, level=Level.BEGINNER, days_per_week=2,
                session_duration_minutes=60, equipment=[EquipmentProfile.DUMBBELLS]),
    Preferences(goal=Goal.POWER, level=Level.INTERMEDIATE, days_per_week=4,
                session_duration_minutes=60, equipment=[EquipmentProfile.FULL_GYM]),
    Preferences(goal=Goal.GENERAL_FITNESS, level=Level.ADVANCED, days_per_week=4,
                session_duration_minutes=60, equipment=[EquipmentProfile.HOME]),
]


def _summarize(case_number: int, preferences: Preferences) -> dict:
    record = generate_workout(preferences)
    allowed_equipment = resolve_equipment(preferences.equipment)
    equipment_by_id = {c.id: c.equipment for c in record.candidate_exercises}

    json_valid = record.workout is not None or not any(
        "JSON inválido" in e for e in record.validation_errors
    )
    structurally_valid = record.workout is not None

    equipment_respected = True
    if record.workout is not None:
        for day in record.workout.days:
            for exercise in day.exercises:
                if equipment_by_id.get(exercise.exercise_id) not in allowed_equipment:
                    equipment_respected = False

    return {
        "case": case_number,
        "goal": preferences.goal.value,
        "level": preferences.level.value,
        "days": preferences.days_per_week,
        "json_valid": json_valid,
        "structurally_valid": structurally_valid,
        "equipment_respected": equipment_respected if structurally_valid else "n/a",
        "attempts": record.attempt,
        "errors": record.validation_errors,
    }


def main() -> None:
    results = [_summarize(i, case) for i, case in enumerate(CASES, start=1)]

    print(f"\n{'#':<3}{'goal':<16}{'level':<14}{'days':<6}{'JSON':<7}{'struct':<8}{'equip':<8}{'intentos':<9}")
    for r in results:
        print(
            f"{r['case']:<3}{r['goal']:<16}{r['level']:<14}{r['days']:<6}"
            f"{str(r['json_valid']):<7}{str(r['structurally_valid']):<8}"
            f"{str(r['equipment_respected']):<8}{r['attempts']:<9}"
        )
        if r["errors"]:
            for error in r["errors"]:
                print(f"      ! {error}")

    valid_count = sum(1 for r in results if r["structurally_valid"])
    print(f"\n{valid_count}/{len(results)} casos produjeron una rutina válida.")
    print("Revisa data/generations/ para la evaluación manual de calidad (1-5).")


if __name__ == "__main__":
    main()
