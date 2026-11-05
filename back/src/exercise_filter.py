"""Reduce the 1,324 exercises in SQLite to a manageable, relevant candidate set.

The dataset has no difficulty field, so difficulty is inferred from names/equipment:
see "Level handling" below (beginners lose Olympic/gymnastic/technical moves and get
barbell work ranked last; intermediates lose only the extreme skills). `level` also
influences prescription (sets/reps/rest) downstream in prompt_builder.py. `goal` has no
structural signal in the dataset either (no compound/isolation/power tagging), except for
`endurance`, which pulls in `cardio` body_part exercises. The real filtering dimensions are
equipment (hard filter) and body_part/target (which muscle groups each day needs).

Two name-based heuristics fill the gaps the dataset leaves (it has no stretch/mobility
tag and no compound/power tag): stretching/mobility drills are excluded outright, and
within each muscle group candidates are ranked by how well their name fits the goal.
"""
from __future__ import annotations

import re
from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models import Exercise
from src.schemas import EquipmentProfile, Goal, Level, Preferences

# --- Equipment mapping -------------------------------------------------------------
# The dataset uses 28 granular equipment strings (confirmed by inspecting the real
# data), not the 4 broad categories users pick from. Each profile below is additive:
# home includes bodyweight+dumbbells, full_gym includes everything.

# "assisted" (assist machines) and "roller" (foam roller, mobility work) are not
# bodyweight training, so they are left to full_gym only.
_BODYWEIGHT_EQUIPMENT = {"body weight", "wheel roller"}
_DUMBBELLS_EQUIPMENT = _BODYWEIGHT_EQUIPMENT | {"dumbbell", "weighted"}
_HOME_EQUIPMENT = _DUMBBELLS_EQUIPMENT | {
    "bosu ball",
    "band",
    "resistance band",
    "kettlebell",
    "stability ball",
    "medicine ball",
}
_ALL_EQUIPMENT = {
    "body weight", "cable", "leverage machine", "assisted", "medicine ball",
    "stability ball", "band", "barbell", "rope", "dumbbell", "ez barbell",
    "sled machine", "upper body ergometer", "kettlebell", "olympic barbell",
    "weighted", "bosu ball", "resistance band", "roller", "skierg machine",
    "hammer", "smith machine", "wheel roller", "stationary bike", "tire",
    "trap bar", "elliptical machine", "stepmill machine",
}

EQUIPMENT_PROFILES: dict[EquipmentProfile, set[str]] = {
    EquipmentProfile.BODYWEIGHT: _BODYWEIGHT_EQUIPMENT,
    EquipmentProfile.DUMBBELLS: _DUMBBELLS_EQUIPMENT,
    EquipmentProfile.HOME: _HOME_EQUIPMENT,
    EquipmentProfile.FULL_GYM: _ALL_EQUIPMENT,
}


def resolve_equipment(profiles: list[EquipmentProfile]) -> set[str]:
    values: set[str] = set()
    for profile in profiles:
        values |= EQUIPMENT_PROFILES[profile]
    return values


# --- Day templates ------------------------------------------------------------------
# body_part groups needed per day, plus an optional "extra" for the biceps/triceps
# split within the "upper arms" body_part (confirmed: upper arms == biceps or triceps
# target, lower arms == forearms, exactly, so this split is exact, not a guess).

_UPPER_ARMS_TRICEPS = ("upper arms", {"triceps"})
_UPPER_ARMS_BICEPS = ("upper arms", {"biceps"})
_UPPER_ARMS_BOTH = ("upper arms", None)

_TEMPLATES_BY_DAYS: dict[int, list[dict]] = {
    1: [
        {"name": "Full Body", "body_parts": {
            "chest", "back", "shoulders", "upper legs", "lower legs", "waist",
        }, "extra": _UPPER_ARMS_BOTH},
    ],
    2: [
        {"name": "Upper Body", "body_parts": {"chest", "back", "shoulders", "lower arms"},
         "extra": _UPPER_ARMS_BOTH},
        {"name": "Lower Body", "body_parts": {"upper legs", "lower legs", "waist"}},
    ],
    3: [
        {"name": "Push (Chest/Shoulders/Triceps)", "body_parts": {"chest", "shoulders"},
         "extra": _UPPER_ARMS_TRICEPS},
        {"name": "Pull (Back/Biceps)", "body_parts": {"back", "lower arms"},
         "extra": _UPPER_ARMS_BICEPS},
        {"name": "Legs/Core", "body_parts": {"upper legs", "lower legs", "waist"}},
    ],
    4: [
        {"name": "Chest/Triceps", "body_parts": {"chest"}, "extra": _UPPER_ARMS_TRICEPS},
        {"name": "Back/Biceps", "body_parts": {"back", "lower arms"}, "extra": _UPPER_ARMS_BICEPS},
        {"name": "Legs", "body_parts": {"upper legs", "lower legs"}},
        {"name": "Shoulders/Core", "body_parts": {"shoulders", "waist"}},
    ],
    5: [
        {"name": "Chest", "body_parts": {"chest"}},
        {"name": "Back", "body_parts": {"back"}},
        {"name": "Legs", "body_parts": {"upper legs", "lower legs"}},
        {"name": "Shoulders", "body_parts": {"shoulders"}},
        {"name": "Arms/Core", "body_parts": {"waist", "lower arms"}, "extra": _UPPER_ARMS_BOTH},
    ],
    6: [
        {"name": "Push", "body_parts": {"chest", "shoulders"}, "extra": _UPPER_ARMS_TRICEPS},
        {"name": "Pull", "body_parts": {"back", "lower arms"}, "extra": _UPPER_ARMS_BICEPS},
        {"name": "Legs", "body_parts": {"upper legs", "lower legs"}},
        {"name": "Push", "body_parts": {"chest", "shoulders"}, "extra": _UPPER_ARMS_TRICEPS},
        {"name": "Pull", "body_parts": {"back", "lower arms"}, "extra": _UPPER_ARMS_BICEPS},
        {"name": "Legs/Core", "body_parts": {"upper legs", "lower legs", "waist"}},
    ],
}


def build_day_templates(days_per_week: int) -> list[dict]:
    if days_per_week <= 6:
        return _TEMPLATES_BY_DAYS[days_per_week]
    # 7 days: reuse the 6-day split and append a full-body / weak-points day.
    return _TEMPLATES_BY_DAYS[6] + [
        {"name": "Full Body / Weak Points", "body_parts": {
            "chest", "back", "shoulders", "upper legs", "lower legs", "waist",
        }, "extra": _UPPER_ARMS_BOTH},
    ]


def estimate_exercises_per_day(session_duration_minutes: int) -> int:
    """~10 minutes per exercise (sets + rest + transition), clamped to a sane range."""
    return max(4, min(8, round(session_duration_minutes / 10)))


# --- Name-based heuristics ----------------------------------------------------------

_NON_TRAINING_PATTERN = re.compile(
    r"stretch|circles|mobility|foam|release|pelvic tilt|balance board|roller|roll",
    re.IGNORECASE,
)

_STAPLE_PATTERN = re.compile(
    r"push-?up|pull-?up|chin-?up|squat|lunge|deadlift|press|row|dip|plank|burpee",
    re.IGNORECASE,
)

_ISOLATION_PATTERN = re.compile(
    r"curl|extension|fly|flye|raise|kickback|concentration|pullover|shrug|wrist",
    re.IGNORECASE,
)
# Goals where single-joint work is poor use of a limited number of slots.
_ISOLATION_PENALIZED_GOALS = {Goal.STRENGTH, Goal.POWER}

# Big multi-joint lifts that should win slots over arbitrary variants (the dataset has
# no compound/isolation tag, so we recognize them by name).
_CORE_LIFT_PATTERN = re.compile(
    r"bench press|squat|deadlift|overhead press|military press|shoulder press|"
    r"row|pulldown|pull-?up|chin-?up|dip|lunge|leg press|hip thrust",
    re.IGNORECASE,
)
_CORE_LIFT_GOALS = {Goal.STRENGTH, Goal.HYPERTROPHY, Goal.GENERAL_FITNESS}

_GOAL_KEYWORDS: dict[Goal, re.Pattern] = {
    Goal.POWER: re.compile(
        r"jump|hop|clap|burpee|sprint|plyo|explosive|snatch|clean|swing|throw|slam|bound",
        re.IGNORECASE,
    ),
    Goal.STRENGTH: re.compile(
        r"squat|deadlift|press|pull-?up|chin-?up|row|dip|lunge|clean|pulldown",
        re.IGNORECASE,
    ),
    Goal.ENDURANCE: re.compile(
        r"burpee|jack|mountain climber|high knees|sprint|jump rope|skater|run",
        re.IGNORECASE,
    ),
}


# --- Level handling -------------------------------------------------------------------
# Olympic lifts, gymnastic skills and similar: excluded for beginner AND intermediate.
_EXTREME_PATTERN = re.compile(
    r"snatch|\bclean\b|\bjerk\b|muscle[- ]?up|handstand|planche|front lever|back lever|"
    r"human flag|pistol|dragon flag|turkish|get[- ]?up|windmill|kipping|"
    r"one[- ]arm (chin|pull)[- ]?up|skin the cat|\bl[- ]sit\b|jefferson|overhead squat",
    re.IGNORECASE,
)
# Technically demanding or injury-prone for novices: excluded for beginners only.
_TECHNICAL_PATTERN = re.compile(
    r"good morning|behind[- ](the[- ])?(neck|head)|stiff|archer|\bclap\b|depth|deficit|"
    r"sissy|single[- ]leg (squat|deadlift)",
    re.IGNORECASE,
)
_TECHNICAL_EQUIPMENT = {"olympic barbell", "tire", "bosu ball", "wheel roller"}
# Free-weight barbell work is allowed for beginners but ranked after everything else.
_BARBELL_EQUIPMENT = {"barbell", "ez barbell"}
_BEGINNER_DEMANDING_PATTERN = re.compile(
    r"pull-?up|chin-?up|\bdip\b|deadlift|burpee", re.IGNORECASE
)
_BARBELL_LAST_PENALTY = 10


def is_too_advanced(exercise: Exercise, level: Level) -> bool:
    """True if the exercise needs more technique than `level` should be handed."""
    if level == Level.ADVANCED:
        return False
    if _EXTREME_PATTERN.search(exercise.name):
        return True
    if level == Level.BEGINNER:
        return bool(
            _TECHNICAL_PATTERN.search(exercise.name)
            or exercise.equipment in _TECHNICAL_EQUIPMENT
        )
    return False


def is_training_exercise(exercise: Exercise) -> bool:
    """False for stretches / mobility drills, which the dataset does not tag."""
    return not _NON_TRAINING_PATTERN.search(exercise.name)


def goal_fit_score(exercise: Exercise, goal: Goal, level: Level | None = None) -> int:
    score = 0
    if _STAPLE_PATTERN.search(exercise.name):
        score += 1
    if goal in _CORE_LIFT_GOALS and _CORE_LIFT_PATTERN.search(exercise.name):
        score += 2
    goal_pattern = _GOAL_KEYWORDS.get(goal)
    if goal_pattern and goal_pattern.search(exercise.name):
        score += 3
    if goal in _ISOLATION_PENALIZED_GOALS and _ISOLATION_PATTERN.search(exercise.name):
        score -= 2
    if level == Level.BEGINNER:
        if exercise.equipment in _BARBELL_EQUIPMENT:
            score -= _BARBELL_LAST_PENALTY
        if exercise.equipment != "assisted" and _BEGINNER_DEMANDING_PATTERN.search(exercise.name):
            score -= 4
    return score


def _pick_diverse(
    pool: list[Exercise], limit: int, goal: Goal, level: Level | None = None
) -> list[Exercise]:
    """Round-robin across muscle_group so one heavily-populated group doesn't crowd out
    the rest of the day's candidates. Within a group, best goal fit comes first."""
    groups: dict[str, list[Exercise]] = defaultdict(list)
    for exercise in pool:
        groups[exercise.muscle_group].append(exercise)
    for group in groups.values():
        group.sort(key=lambda e: (-goal_fit_score(e, goal, level), e.id))

    order = list(groups.keys())
    result: list[Exercise] = []
    i = 0
    while len(result) < limit and any(groups.values()):
        group_key = order[i % len(order)]
        if groups[group_key]:
            result.append(groups[group_key].pop(0))
        i += 1
    return result


CANDIDATE_MARGIN = 3  # oversupply factor so the LLM has real choice, not just filler


def get_exercise_candidates(preferences: Preferences, session: Session) -> list[Exercise]:
    equipment_values = resolve_equipment(preferences.equipment)
    if not equipment_values:
        return []

    all_matching = [
        exercise
        for exercise in session.scalars(
            select(Exercise).where(Exercise.equipment.in_(equipment_values))
        )
        if is_training_exercise(exercise)
    ]

    # Level-appropriate subset; a day falls back to the full list only if this leaves it
    # with fewer exercises than the session needs.
    suitable = [e for e in all_matching if not is_too_advanced(e, preferences.level)]

    templates = build_day_templates(preferences.days_per_week)
    exercises_per_day = estimate_exercises_per_day(preferences.session_duration_minutes)
    limit_per_day = exercises_per_day * CANDIDATE_MARGIN

    candidates: dict[int, Exercise] = {}
    for template in templates:
        body_parts: set[str] = set(template["body_parts"])
        if preferences.goal == Goal.ENDURANCE:
            body_parts.add("cardio")

        extra = template.get("extra")

        def build_pool(source: list[Exercise]) -> list[Exercise]:
            pool = [e for e in source if e.body_part in body_parts]
            if extra:
                extra_body_part, target_filter = extra
                pool += [
                    e for e in source
                    if e.body_part == extra_body_part
                    and (target_filter is None or e.target_muscle in target_filter)
                ]
            return pool

        pool = build_pool(suitable)
        if len(pool) < exercises_per_day:
            pool = build_pool(all_matching)

        for exercise in _pick_diverse(pool, limit_per_day, preferences.goal, preferences.level):
            candidates[exercise.id] = exercise

    return sorted(candidates.values(), key=lambda e: e.id)
