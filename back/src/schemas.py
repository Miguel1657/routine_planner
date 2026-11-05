"""Pydantic schemas: user preferences, LLM output contract, and generation records."""
from __future__ import annotations

from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class Goal(StrEnum):
    STRENGTH = "strength"
    HYPERTROPHY = "hypertrophy"
    POWER = "power"
    ENDURANCE = "endurance"
    GENERAL_FITNESS = "general_fitness"


class Level(StrEnum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class EquipmentProfile(StrEnum):
    FULL_GYM = "full_gym"
    HOME = "home"
    DUMBBELLS = "dumbbells"
    BODYWEIGHT = "bodyweight"


class Preferences(BaseModel):
    goal: Goal
    level: Level
    days_per_week: int = Field(ge=1, le=7)
    session_duration_minutes: int = Field(ge=15, le=180)
    equipment: list[EquipmentProfile] = Field(min_length=1)
    # Language for the free-text parts of the workout (program and day names).
    language: Literal["es", "en"] = "es"


class WorkoutExercise(BaseModel):
    exercise_id: int
    sets: int = Field(gt=0)
    reps: str
    rest_seconds: int = Field(ge=0)


class WorkoutDay(BaseModel):
    day: int
    name: str
    exercises: list[WorkoutExercise]


class Workout(BaseModel):
    name: str
    days: list[WorkoutDay]

    @field_validator("days")
    @classmethod
    def must_have_days(cls, days: list[WorkoutDay]) -> list[WorkoutDay]:
        if not days:
            raise ValueError("workout must contain at least one day")
        return days


class CandidateExercise(BaseModel):
    """Compact representation of an exercise, as sent to the LLM / stored for review."""

    id: int
    name: str
    body_part: str
    target_muscle: str
    equipment: str


class GenerationRecord(BaseModel):
    """Everything about one generation attempt, saved to data/generations/ for analysis."""

    preferences: Preferences
    candidate_exercises: list[CandidateExercise]
    model: str
    prompt: str
    response: str
    workout: Workout | None
    validation_errors: list[str]
    attempt: int
    timestamp: str
    extra: dict[str, Any] = Field(default_factory=dict)
