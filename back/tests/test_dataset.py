from src.dataset_loader import normalize_record


def test_normalize_record_maps_fields(sample_raw_records):
    exercise = normalize_record(sample_raw_records[0])

    assert exercise.id == 1
    assert exercise.source_id == "0001"
    assert exercise.name == "3/4 sit-up"
    assert exercise.body_part == "waist"
    assert exercise.muscle_group == "hip flexors"
    assert exercise.target_muscle == "abs"
    assert exercise.equipment == "body weight"
    assert exercise.instructions == "Lie down and curl up."
    assert exercise.secondary_muscles == ["hip flexors", "lower back"]
    assert exercise.thumbnail_url == "images/0001-2gPfomN.jpg"
    assert exercise.gif_url == "videos/0001-2gPfomN.gif"


def test_normalize_record_strips_leading_zeros_from_id(sample_raw_records):
    exercise = normalize_record(sample_raw_records[1])
    assert exercise.id == 237
    assert exercise.source_id == "0237"


def test_normalize_record_handles_missing_english_instructions():
    record = {
        "id": "0999",
        "name": "Test Exercise",
        "category": "chest",
        "body_part": "chest",
        "equipment": "cable",
        "instructions": {"es": "Solo en español."},
        "muscle_group": "chest",
        "secondary_muscles": [],
        "target": "pectorals",
        "image": "images/x.jpg",
        "gif_url": "videos/x.gif",
    }
    exercise = normalize_record(record)
    assert exercise.instructions == ""
