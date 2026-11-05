"""Interactive CLI to exercise the generation pipeline end-to-end.

Usage:
    python -m src.main
"""
from __future__ import annotations

import sys

# Force UTF-8 stdout regardless of the Windows console codepage, so accented
# characters in the Spanish CLI text (á, í, ó...) render correctly.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from src.database import get_session
from src.exercise_filter import get_exercise_candidates
from src.schemas import EquipmentProfile, Goal, GenerationRecord, Level, Preferences
from src.workout_generator import generate_workout

_GOAL_OPTIONS: dict[str, Goal] = {
    "1": Goal.STRENGTH,
    "2": Goal.HYPERTROPHY,
    "3": Goal.POWER,
    "4": Goal.ENDURANCE,
    "5": Goal.GENERAL_FITNESS,
}
_GOAL_LABELS = {
    "1": "Fuerza", "2": "Hipertrofia", "3": "Potencia",
    "4": "Resistencia", "5": "Fitness general",
}

_LEVEL_OPTIONS: dict[str, Level] = {
    "1": Level.BEGINNER,
    "2": Level.INTERMEDIATE,
    "3": Level.ADVANCED,
}
_LEVEL_LABELS = {"1": "Básico", "2": "Intermedio", "3": "Avanzado"}

_EQUIPMENT_OPTIONS: dict[str, EquipmentProfile] = {
    "1": EquipmentProfile.FULL_GYM,
    "2": EquipmentProfile.HOME,
    "3": EquipmentProfile.DUMBBELLS,
    "4": EquipmentProfile.BODYWEIGHT,
}
_EQUIPMENT_LABELS = {
    "1": "Gimnasio completo", "2": "Casa", "3": "Mancuernas", "4": "Peso corporal",
}


def _ask_choice(question: str, labels: dict[str, str]) -> str:
    print(question)
    for key, label in labels.items():
        print(f"{key}. {label}")
    while True:
        choice = input("> ").strip()
        if choice in labels:
            return choice
        print(f"Opción inválida. Elige una de: {', '.join(labels)}")


def _ask_int(question: str, minimum: int, maximum: int) -> int:
    while True:
        raw = input(f"{question} ").strip()
        if raw.isdigit() and minimum <= int(raw) <= maximum:
            return int(raw)
        print(f"Ingresa un número entre {minimum} y {maximum}.")


def ask_preferences() -> Preferences:
    goal_choice = _ask_choice("¿Qué deseas entrenar?", _GOAL_LABELS)
    print()
    level_choice = _ask_choice("Nivel:", _LEVEL_LABELS)
    print()
    days = _ask_int("Días por semana:", 1, 7)
    duration = _ask_int("Duración por sesión (minutos):", 15, 180)
    print()
    equipment_choice = _ask_choice("Equipamiento:", _EQUIPMENT_LABELS)

    return Preferences(
        goal=_GOAL_OPTIONS[goal_choice],
        level=_LEVEL_OPTIONS[level_choice],
        days_per_week=days,
        session_duration_minutes=duration,
        equipment=[_EQUIPMENT_OPTIONS[equipment_choice]],
    )


def print_result(record: GenerationRecord) -> None:
    if record.workout is None:
        print("\nNo se pudo generar una rutina válida.\n")
        print("Errores de validación:")
        for error in record.validation_errors:
            print(f"  - {error}")
        print(f"\n(La respuesta cruda del modelo se guardó en data/generations/ para revisión.)")
        return

    workout = record.workout
    names_by_id = {c.id: c.name for c in record.candidate_exercises}

    print("\n" + "=" * 40)
    print(f"RUTINA: {workout.name.upper()}")
    print("=" * 40)

    used_ids: set[int] = set()
    for day in workout.days:
        print(f"\nDÍA {day.day} — {day.name.upper()}\n")
        for i, exercise in enumerate(day.exercises, start=1):
            used_ids.add(exercise.exercise_id)
            name = names_by_id.get(exercise.exercise_id, f"(id desconocido {exercise.exercise_id})")
            print(f"{i}. {name}")
            print(f"   {exercise.sets} × {exercise.reps}")
            print(f"   Descanso: {exercise.rest_seconds}s\n")

    print("=" * 40)
    print(f"Modelo: {record.model}")
    print(f"Ejercicios candidatos: {len(record.candidate_exercises)}")
    print(f"Ejercicios utilizados: {len(used_ids)}")
    print(f"Validación: {'OK' if not record.validation_errors else 'ERROR'}")
    print("=" * 40)


def main() -> None:
    preferences = ask_preferences()

    print("\nBuscando ejercicios compatibles...")
    with get_session() as session:
        candidate_count = len(get_exercise_candidates(preferences, session))
    print(f"Ejercicios encontrados: {candidate_count}")

    if candidate_count == 0:
        print(
            "\nNo hay ejercicios candidatos con esos filtros (equipamiento demasiado "
            "restrictivo o base de datos vacía). Ejecuta 'python -m src.dataset_loader' "
            "si aún no has importado el dataset."
        )
        return

    print("\nEnviando candidatos al LLM...")
    print("Generando rutina...")

    record = generate_workout(preferences)
    print_result(record)


if __name__ == "__main__":
    main()
