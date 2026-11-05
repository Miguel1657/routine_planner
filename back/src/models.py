"""SQLAlchemy ORM models for the local exercises database."""
import json

from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Exercise(Base):
    """Normalized exercise, independent of the original dataset's field names."""

    __tablename__ = "exercises"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_id: Mapped[str] = mapped_column(String(16), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255), index=True)
    body_part: Mapped[str] = mapped_column(String(64), index=True)
    muscle_group: Mapped[str] = mapped_column(String(64), index=True)
    target_muscle: Mapped[str] = mapped_column(String(64))
    secondary_muscles_json: Mapped[str] = mapped_column(Text, default="[]")
    equipment: Mapped[str] = mapped_column(String(64), index=True)
    instructions: Mapped[str] = mapped_column(Text, default="")
    thumbnail_url: Mapped[str] = mapped_column(String(255), default="")
    gif_url: Mapped[str] = mapped_column(String(255), default="")

    @property
    def secondary_muscles(self) -> list[str]:
        return json.loads(self.secondary_muscles_json)

    @secondary_muscles.setter
    def secondary_muscles(self, muscles: list[str]) -> None:
        self.secondary_muscles_json = json.dumps(muscles)

    def __repr__(self) -> str:  # pragma: no cover
        return f"Exercise(id={self.id}, name={self.name!r}, equipment={self.equipment!r})"
