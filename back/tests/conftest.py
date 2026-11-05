import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from src.models import Base, Exercise

# A tiny, hand-built stand-in for real exercises-dataset records — enough to exercise
# normalize_record() without hitting the network. Field shapes copied from the real
# dataset (id zero-padded string, category==body_part, instructions per language, etc).
SAMPLE_RAW_RECORDS = [
    {
        "id": "0001",
        "name": "3/4 sit-up",
        "category": "waist",
        "body_part": "waist",
        "equipment": "body weight",
        "instructions": {"en": "Lie down and curl up.", "es": "Acuéstate y flexiona."},
        "instruction_steps": {"en": ["Lie down.", "Curl up."]},
        "muscle_group": "hip flexors",
        "secondary_muscles": ["hip flexors", "lower back"],
        "target": "abs",
        "image": "images/0001-2gPfomN.jpg",
        "gif_url": "videos/0001-2gPfomN.gif",
        "media_id": "2gPfomN",
        "created_at": "2026-03-18T12:31:32.854798+00:00",
        "attribution": "© Gym visual",
    },
    {
        "id": "0237",
        "name": "Barbell Bench Press",
        "category": "chest",
        "body_part": "chest",
        "equipment": "barbell",
        "instructions": {"en": "Press the bar off your chest."},
        "instruction_steps": {"en": ["Unrack.", "Lower.", "Press."]},
        "muscle_group": "chest",
        "secondary_muscles": ["triceps", "shoulders"],
        "target": "pectorals",
        "image": "images/0237-abc.jpg",
        "gif_url": "videos/0237-abc.gif",
        "media_id": "abc",
        "created_at": "2026-03-18T12:31:32.854798+00:00",
        "attribution": "© Gym visual",
    },
]


@pytest.fixture()
def sample_raw_records():
    return SAMPLE_RAW_RECORDS


def _make_exercise(
    id_, name, body_part, muscle_group, target_muscle, equipment, secondary=None
) -> Exercise:
    exercise = Exercise(
        id=id_,
        source_id=f"{id_:04d}",
        name=name,
        body_part=body_part,
        muscle_group=muscle_group,
        target_muscle=target_muscle,
        equipment=equipment,
        instructions="",
        thumbnail_url="",
        gif_url="",
    )
    exercise.secondary_muscles = secondary or []
    return exercise


# A small synthetic catalog spanning every body_part/equipment combination the filter
# logic cares about, so tests don't depend on the real 1,324-row dataset being imported.
SYNTHETIC_CATALOG = [
    _make_exercise(1, "Push-up", "chest", "chest", "pectorals", "body weight"),
    _make_exercise(2, "Barbell Bench Press", "chest", "chest", "pectorals", "barbell"),
    _make_exercise(3, "Cable Fly", "chest", "chest", "pectorals", "cable"),
    _make_exercise(4, "Pull-up", "back", "lats", "lats", "body weight"),
    _make_exercise(5, "Barbell Row", "back", "lats", "lats", "barbell"),
    _make_exercise(6, "Dumbbell Shoulder Press", "shoulders", "shoulders", "delts", "dumbbell"),
    _make_exercise(7, "Barbell Curl", "upper arms", "biceps", "biceps", "barbell"),
    _make_exercise(8, "Dumbbell Curl", "upper arms", "biceps", "biceps", "dumbbell"),
    _make_exercise(9, "Triceps Pushdown", "upper arms", "triceps", "triceps", "cable"),
    _make_exercise(10, "Dumbbell Triceps Extension", "upper arms", "triceps", "triceps", "dumbbell"),
    _make_exercise(11, "Wrist Curl", "lower arms", "forearms", "forearms", "dumbbell"),
    _make_exercise(12, "Barbell Squat", "upper legs", "quadriceps", "quads", "barbell"),
    _make_exercise(13, "Bodyweight Squat", "upper legs", "quadriceps", "quads", "body weight"),
    _make_exercise(14, "Calf Raise", "lower legs", "calves", "calves", "body weight"),
    _make_exercise(15, "Sit-up", "waist", "abdominals", "abs", "body weight"),
    _make_exercise(16, "Treadmill Run", "cardio", "cardiovascular system", "cardiovascular system", "body weight"),
]


@pytest.fixture()
def session():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    with Session(engine) as session_:
        session_.add_all(
            _make_exercise(e.id, e.name, e.body_part, e.muscle_group, e.target_muscle, e.equipment, e.secondary_muscles)
            for e in SYNTHETIC_CATALOG
        )
        session_.commit()
        yield session_
