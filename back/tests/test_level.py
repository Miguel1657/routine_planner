"""Level-aware candidate selection: no Olympic/gymnastic moves for beginners, barbell last."""
import pytest

from src.exercise_filter import (
    get_exercise_candidates,
    goal_fit_score,
    is_too_advanced,
)
from src.schemas import EquipmentProfile, Goal, Level, Preferences
from tests.conftest import _make_exercise


def _ex(id_, name, equipment="body weight", body_part="chest"):
    return _make_exercise(id_, name, body_part, body_part, "pectorals", equipment)


@pytest.mark.parametrize(
    "name,equipment",
    [
        ("barbell power clean", "barbell"),
        ("kettlebell double snatch", "kettlebell"),
        ("muscle up", "body weight"),
        ("front lever", "body weight"),
        ("single leg squat (pistol) male", "body weight"),
    ],
)
def test_extreme_moves_are_excluded_for_beginner_and_intermediate(name, equipment):
    exercise = _ex(1, name, equipment)
    assert is_too_advanced(exercise, Level.BEGINNER)
    assert is_too_advanced(exercise, Level.INTERMEDIATE)
    assert not is_too_advanced(exercise, Level.ADVANCED)


@pytest.mark.parametrize(
    "name,equipment",
    [
        ("barbell good morning", "barbell"),
        ("olympic barbell triceps extension", "olympic barbell"),
        ("push up on bosu ball", "bosu ball"),
        ("clap push up", "body weight"),
        ("dumbbell stiff leg deadlift", "dumbbell"),
    ],
)
def test_technical_moves_are_excluded_for_beginner_only(name, equipment):
    exercise = _ex(1, name, equipment)
    assert is_too_advanced(exercise, Level.BEGINNER)
    assert not is_too_advanced(exercise, Level.INTERMEDIATE)


@pytest.mark.parametrize(
    "name,equipment",
    [
        ("lever chest press", "leverage machine"),
        ("band kneeling one arm pulldown", "band"),
        ("barbell bench press", "barbell"),
        ("barbell full squat", "barbell"),
        ("cable fly", "cable"),
    ],
)
def test_basic_moves_are_not_excluded_for_beginners(name, equipment):
    assert not is_too_advanced(_ex(1, name, equipment), Level.BEGINNER)


def test_barbell_ranks_after_machine_cable_and_dumbbell_for_beginners():
    barbell = _ex(1, "barbell bench press", "barbell")
    for name, equipment in [
        ("lever chest press", "leverage machine"),
        ("cable fly", "cable"),
        ("dumbbell fly", "dumbbell"),
    ]:
        other = _ex(2, name, equipment)
        for goal in (Goal.STRENGTH, Goal.HYPERTROPHY, Goal.GENERAL_FITNESS):
            assert goal_fit_score(barbell, goal, Level.BEGINNER) < goal_fit_score(
                other, goal, Level.BEGINNER
            )
    # Unchanged for other levels.
    assert goal_fit_score(barbell, Goal.HYPERTROPHY, Level.INTERMEDIATE) == goal_fit_score(
        barbell, Goal.HYPERTROPHY
    )


def test_unassisted_pullups_are_demoted_but_assisted_ones_are_not():
    pullup = _ex(1, "pull-up", "body weight", "back")
    assisted = _ex(2, "assisted pull-up", "assisted", "back")
    assert goal_fit_score(pullup, Goal.HYPERTROPHY, Level.BEGINNER) < goal_fit_score(
        assisted, Goal.HYPERTROPHY, Level.BEGINNER
    )


def test_beginner_candidates_contain_no_advanced_moves(session):
    preferences = Preferences(
        goal=Goal.POWER,
        level=Level.BEGINNER,
        days_per_week=4,
        session_duration_minutes=60,
        equipment=[EquipmentProfile.FULL_GYM],
    )
    candidates = get_exercise_candidates(preferences, session)
    assert candidates
    assert not [c.name for c in candidates if is_too_advanced(c, Level.BEGINNER)]
