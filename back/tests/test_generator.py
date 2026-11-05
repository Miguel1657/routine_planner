import json

import pytest

from src.models import Exercise
from src.schemas import Goal, Level, Preferences
from src.validator import validate_workout


def _exercise(id_: int) -> Exercise:
    return Exercise(
        id=id_, source_id=f"{id_:04d}", name=f"Exercise {id_}", body_part="chest",
        muscle_group="chest", target_muscle="pectorals", equipment="barbell",
    )


@pytest.fixture()
def candidates():
    return [_exercise(1), _exercise(2), _exercise(3)]


@pytest.fixture()
def preferences():
    return Preferences(
        goal=Goal.HYPERTROPHY, level=Level.INTERMEDIATE, days_per_week=1,
        session_duration_minutes=45, equipment=["full_gym"],
    )


def _workout_json(days: list[dict]) -> str:
    return json.dumps({"name": "Test Program", "days": days})


def test_valid_response_produces_workout(candidates, preferences):
    raw = _workout_json([
        {"day": 1, "name": "Chest Day", "exercises": [
            {"exercise_id": 1, "sets": 3, "reps": "8-10", "rest_seconds": 90},
            {"exercise_id": 2, "sets": 3, "reps": "10", "rest_seconds": 60},
        ]},
    ])
    workout, errors = validate_workout(raw, preferences, candidates)
    assert errors == []
    assert workout is not None
    assert len(workout.days) == 1


def test_invalid_json_is_rejected(candidates, preferences):
    workout, errors = validate_workout("{not valid json", preferences, candidates)
    assert workout is None
    assert any("JSON inválido" in e for e in errors)


def test_wrong_day_count_is_rejected(candidates, preferences):
    raw = _workout_json([
        {"day": 1, "name": "Day 1", "exercises": [{"exercise_id": 1, "sets": 3, "reps": "10", "rest_seconds": 60}]},
        {"day": 2, "name": "Day 2", "exercises": [{"exercise_id": 2, "sets": 3, "reps": "10", "rest_seconds": 60}]},
    ])
    workout, errors = validate_workout(raw, preferences, candidates)
    assert workout is None
    assert any("días" in e for e in errors)


def test_invented_exercise_id_is_rejected(candidates, preferences):
    raw = _workout_json([
        {"day": 1, "name": "Day 1", "exercises": [{"exercise_id": 999, "sets": 3, "reps": "10", "rest_seconds": 60}]},
    ])
    workout, errors = validate_workout(raw, preferences, candidates)
    assert workout is None
    assert any("exercise_id inválido" in e for e in errors)


def test_negative_sets_is_rejected_by_schema(candidates, preferences):
    raw = _workout_json([
        {"day": 1, "name": "Day 1", "exercises": [{"exercise_id": 1, "sets": -1, "reps": "10", "rest_seconds": 60}]},
    ])
    workout, errors = validate_workout(raw, preferences, candidates)
    assert workout is None
    assert any("inválida" in e for e in errors)


def test_malformed_reps_is_rejected(candidates, preferences):
    raw = _workout_json([
        {"day": 1, "name": "Day 1", "exercises": [{"exercise_id": 1, "sets": 3, "reps": "8 to 10 reps", "rest_seconds": 60}]},
    ])
    workout, errors = validate_workout(raw, preferences, candidates)
    assert workout is None
    assert any("reps" in e for e in errors)


def test_unreasonable_rest_seconds_is_rejected(candidates, preferences):
    raw = _workout_json([
        {"day": 1, "name": "Day 1", "exercises": [{"exercise_id": 1, "sets": 3, "reps": "10", "rest_seconds": 99999}]},
    ])
    workout, errors = validate_workout(raw, preferences, candidates)
    assert workout is None
    assert any("rest_seconds" in e for e in errors)


def test_empty_day_is_rejected(candidates, preferences):
    raw = _workout_json([{"day": 1, "name": "Day 1", "exercises": []}])
    workout, errors = validate_workout(raw, preferences, candidates)
    assert workout is None
    assert any("no tiene ejercicios" in e for e in errors)


def test_reps_accept_timed_and_amrap_prescriptions():
    from src.validator import _REPS_PATTERN

    for ok in ["8-10", "12", "30-60s", "30 seconds", "45 sec", "AMRAP", "As many as possible", "As Many Reps as Possible"]:
        assert _REPS_PATTERN.match(ok), ok
    for bad in ["", "lots", "ten", "8 to 10 reps"]:
        assert not _REPS_PATTERN.match(bad), bad
