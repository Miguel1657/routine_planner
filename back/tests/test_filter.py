from src.exercise_filter import (
    estimate_exercises_per_day,
    goal_fit_score,
    is_training_exercise,
    get_exercise_candidates,
    resolve_equipment,
)
from src.schemas import EquipmentProfile, Goal, Level, Preferences


def _preferences(**overrides) -> Preferences:
    defaults = dict(
        goal=Goal.HYPERTROPHY,
        level=Level.INTERMEDIATE,
        days_per_week=3,
        session_duration_minutes=60,
        equipment=[EquipmentProfile.FULL_GYM],
    )
    defaults.update(overrides)
    return Preferences(**defaults)


def test_estimate_exercises_per_day_is_bounded():
    assert estimate_exercises_per_day(15) == 4
    assert estimate_exercises_per_day(60) == 6
    assert estimate_exercises_per_day(300) == 8


def test_resolve_equipment_bodyweight_is_a_subset_of_full_gym():
    bodyweight = resolve_equipment([EquipmentProfile.BODYWEIGHT])
    full_gym = resolve_equipment([EquipmentProfile.FULL_GYM])
    assert bodyweight < full_gym


def test_candidates_respect_equipment_filter(session):
    preferences = _preferences(equipment=[EquipmentProfile.BODYWEIGHT])
    candidates = get_exercise_candidates(preferences, session)

    assert candidates
    allowed = resolve_equipment([EquipmentProfile.BODYWEIGHT])
    assert all(exercise.equipment in allowed for exercise in candidates)


def test_candidate_count_is_not_a_fixed_number(session):
    one_day = get_exercise_candidates(_preferences(days_per_week=1), session)
    four_days = get_exercise_candidates(_preferences(days_per_week=4), session)

    assert len(one_day) != len(four_days)
    assert len(four_days) > len(one_day)


def test_endurance_goal_pulls_in_cardio(session):
    candidates = get_exercise_candidates(
        _preferences(goal=Goal.ENDURANCE, days_per_week=1), session
    )
    assert any(exercise.body_part == "cardio" for exercise in candidates)


def test_hypertrophy_goal_excludes_cardio_body_part_by_default(session):
    candidates = get_exercise_candidates(
        _preferences(goal=Goal.HYPERTROPHY, days_per_week=1), session
    )
    assert all(exercise.body_part != "cardio" for exercise in candidates)


def test_no_equipment_returns_no_candidates(session):
    # Preferences normally requires equipment to be non-empty; bypass that with
    # model_copy to make sure the filter itself degrades gracefully to [] rather
    # than accidentally matching everything.
    preferences = _preferences().model_copy(update={"equipment": []})
    candidates = get_exercise_candidates(preferences, session)
    assert candidates == []


def test_bodyweight_profile_excludes_assist_machines_and_foam_rollers():
    bodyweight = resolve_equipment([EquipmentProfile.BODYWEIGHT])
    assert {"assisted", "roller", "bosu ball"}.isdisjoint(bodyweight)


def test_stretching_and_mobility_exercises_are_not_training_candidates():
    from tests.conftest import _make_exercise

    stretch = _make_exercise(900, "rear deltoid stretch", "shoulders", "delts", "delts", "body weight")
    circles = _make_exercise(901, "ankle circles", "lower legs", "calves", "calves", "body weight")
    squat = _make_exercise(902, "jump squat", "upper legs", "quads", "quads", "body weight")

    assert not is_training_exercise(stretch)
    assert not is_training_exercise(circles)
    assert is_training_exercise(squat)


def test_power_goal_ranks_jumping_movements_above_generic_ones():
    from tests.conftest import _make_exercise

    jump = _make_exercise(910, "jump squat", "upper legs", "quads", "quads", "body weight")
    kicks = _make_exercise(911, "flutter kicks", "upper legs", "quads", "quads", "body weight")

    assert goal_fit_score(jump, Goal.POWER) > goal_fit_score(kicks, Goal.POWER)


def test_candidates_never_include_stretching(session):
    candidates = get_exercise_candidates(
        _preferences(equipment=[EquipmentProfile.BODYWEIGHT], days_per_week=4), session
    )
    assert all(is_training_exercise(exercise) for exercise in candidates)


def test_isolation_exercises_are_penalized_for_power_and_strength_only():
    from tests.conftest import _make_exercise

    curl = _make_exercise(920, "barbell curl", "upper arms", "biceps", "biceps", "barbell")
    squat = _make_exercise(921, "barbell squat", "upper legs", "quads", "quads", "barbell")

    assert goal_fit_score(curl, Goal.POWER) < goal_fit_score(squat, Goal.POWER)
    assert goal_fit_score(curl, Goal.STRENGTH) < goal_fit_score(squat, Goal.STRENGTH)
    assert goal_fit_score(curl, Goal.HYPERTROPHY) == 0


def test_hypertrophy_and_strength_favor_core_lifts_over_variants():
    from tests.conftest import _make_exercise

    bench = _make_exercise(930, "barbell bench press", "chest", "chest", "pectorals", "barbell")
    fly = _make_exercise(931, "cable fly", "chest", "chest", "pectorals", "cable")

    for goal in (Goal.HYPERTROPHY, Goal.STRENGTH, Goal.GENERAL_FITNESS):
        assert goal_fit_score(bench, goal) > goal_fit_score(fly, goal)
