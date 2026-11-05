"""Download, normalize and import the exercises dataset into SQLite.

Usage:
    python -m src.dataset_loader
"""
from __future__ import annotations

import json
import urllib.request
from collections import Counter

from src.config import EXERCISES_DATASET_URL, RAW_DATASET_PATH
from src.database import get_session, init_db, make_engine
from src.models import Base, Exercise


def download_dataset(force: bool = False) -> None:
    if RAW_DATASET_PATH.exists() and not force:
        return
    RAW_DATASET_PATH.parent.mkdir(parents=True, exist_ok=True)
    print(f"Descargando dataset desde {EXERCISES_DATASET_URL} ...")
    with urllib.request.urlopen(EXERCISES_DATASET_URL) as response:
        RAW_DATASET_PATH.write_bytes(response.read())


def load_raw_records() -> list[dict]:
    download_dataset()
    with open(RAW_DATASET_PATH, encoding="utf-8") as f:
        return json.load(f)


def normalize_record(record: dict) -> Exercise:
    """Map a raw exercises-dataset record to the internal Exercise model.

    Only the fields this MVP actually uses are kept: `category` is dropped because
    it is always identical to `body_part` in the source data, and only the English
    instruction text is stored (the LLM prompt never sends instructions anyway; the
    raw multilingual JSON stays available in data/raw/ if needed later).
    """
    exercise = Exercise(
        id=int(record["id"]),
        source_id=record["id"],
        name=record["name"],
        body_part=record["body_part"],
        muscle_group=record["muscle_group"],
        target_muscle=record["target"],
        equipment=record["equipment"],
        instructions=record.get("instructions", {}).get("en", ""),
        thumbnail_url=record.get("image", ""),
        gif_url=record.get("gif_url", ""),
    )
    exercise.secondary_muscles = record.get("secondary_muscles", [])
    return exercise


def import_dataset() -> dict:
    """Load, normalize, and insert the dataset. Returns stats for reporting."""
    records = load_raw_records()

    seen_ids: set[str] = set()
    exercises: list[Exercise] = []
    id_duplicates = 0
    for record in records:
        if record["id"] in seen_ids:
            id_duplicates += 1
            continue
        seen_ids.add(record["id"])
        exercises.append(normalize_record(record))

    name_counts = Counter(e.name.strip().lower() for e in exercises)
    duplicate_names = {name: count for name, count in name_counts.items() if count > 1}

    engine = make_engine()
    Base.metadata.drop_all(engine)
    init_db(engine)
    with get_session() as session:
        session.add_all(exercises)
        session.commit()

    return {
        "original_count": len(records),
        "imported_count": len(exercises),
        "id_duplicates_skipped": id_duplicates,
        "duplicate_name_groups": len(duplicate_names),
        "duplicate_name_records": sum(duplicate_names.values()),
        "body_part_counts": Counter(e.body_part for e in exercises),
        "equipment_counts": Counter(e.equipment for e in exercises),
    }


def print_stats(stats: dict) -> None:
    print("\nDataset importado correctamente\n")
    print(f"Ejercicios originales: {stats['original_count']}")
    print(f"Ejercicios importados: {stats['imported_count']}")
    print(f"Duplicados (mismo id, descartados): {stats['id_duplicates_skipped']}")
    print(
        f"Nombres duplicados (id distinto, se conservan): "
        f"{stats['duplicate_name_groups']} grupos / {stats['duplicate_name_records']} registros"
    )

    print("\nGrupos musculares (body_part):")
    for body_part, count in stats["body_part_counts"].most_common():
        print(f"  {body_part}: {count}")

    print("\nEquipamiento:")
    for equipment, count in stats["equipment_counts"].most_common():
        print(f"  {equipment}: {count}")


if __name__ == "__main__":
    print_stats(import_dataset())
