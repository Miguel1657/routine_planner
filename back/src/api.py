"""HTTP API around `generate_workout` for the Next.js frontend.

Run with:
    uvicorn src.api:app --reload --port 8001
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import select

from src.config import CORS_ORIGINS, MEDIA_BASE_URL
from src.database import get_session
from src.models import Exercise
from src.schemas import Preferences
from src.workout_generator import generate_workout

app = FastAPI(title="Gym AI API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["POST", "GET"],
    allow_headers=["Content-Type"],
)


class ExerciseCard(BaseModel):
    exercise_id: int
    name: str
    body_part: str
    target_muscle: str
    equipment: str
    sets: int
    reps: str
    rest_seconds: int
    image_url: str
    gif_url: str


class DayCard(BaseModel):
    day: int
    name: str
    exercises: list[ExerciseCard]


class GenerateResponse(BaseModel):
    ok: bool
    name: str | None
    days: list[DayCard]
    model: str
    attempts: int
    candidates: int
    errors: list[str]


def _media_url(path: str) -> str:
    return f"{MEDIA_BASE_URL.rstrip('/')}/{path.lstrip('/')}" if path else ""


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


# Plain `def` on purpose: generation blocks for a while on the LLM call, and FastAPI
# runs sync endpoints in a worker thread instead of blocking the event loop.
@app.post("/api/generate", response_model=GenerateResponse)
def generate(preferences: Preferences) -> GenerateResponse:
    record = generate_workout(preferences)

    days: list[DayCard] = []
    if record.workout is not None:
        ids = {e.exercise_id for d in record.workout.days for e in d.exercises}
        with get_session() as session:
            by_id = {
                ex.id: ex
                for ex in session.scalars(select(Exercise).where(Exercise.id.in_(ids)))
            }
        for day in record.workout.days:
            days.append(
                DayCard(
                    day=day.day,
                    name=day.name,
                    exercises=[
                        ExerciseCard(
                            exercise_id=e.exercise_id,
                            name=by_id[e.exercise_id].name,
                            body_part=by_id[e.exercise_id].body_part,
                            target_muscle=by_id[e.exercise_id].target_muscle,
                            equipment=by_id[e.exercise_id].equipment,
                            sets=e.sets,
                            reps=e.reps,
                            rest_seconds=e.rest_seconds,
                            image_url=_media_url(by_id[e.exercise_id].thumbnail_url),
                            gif_url=_media_url(by_id[e.exercise_id].gif_url),
                        )
                        for e in day.exercises
                    ],
                )
            )

    return GenerateResponse(
        ok=record.workout is not None,
        name=record.workout.name if record.workout else None,
        days=days,
        model=record.model,
        attempts=record.attempt,
        candidates=len(record.candidate_exercises),
        errors=record.validation_errors,
    )
