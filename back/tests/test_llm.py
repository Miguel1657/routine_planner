"""OpenAI provider: request shape and error handling, without network."""
import json

import pytest

from src import llm


class _Resp:
    def __init__(self, payload, status=200):
        self._payload, self.status_code, self.text = payload, status, json.dumps(payload)

    def json(self):
        return self._payload


def _ok(content="{}", finish="stop", refusal=None):
    return _Resp({"choices": [{"finish_reason": finish, "message": {"content": content, "refusal": refusal}}]})


@pytest.fixture
def openai_on(monkeypatch):
    monkeypatch.setattr(llm, "OPENAI_API_KEY", "sk-test")
    monkeypatch.setattr(llm, "OPENAI_REASONING_EFFORT", "low")


def test_request_has_enum_of_candidate_ids_and_no_temperature(monkeypatch, openai_on):
    sent = {}

    def fake_post(url, headers, json, timeout):
        sent.update(url=url, headers=headers, body=json)
        return _ok('{"name": "x", "days": []}')

    monkeypatch.setattr(llm.httpx, "post", fake_post)
    out = llm.generate_workout_json("prompt", candidate_ids=[5, 3, 5])

    assert out == '{"name": "x", "days": []}'
    assert sent["url"].endswith("/chat/completions")
    assert sent["headers"]["Authorization"] == "Bearer sk-test"
    assert "temperature" not in sent["body"]
    assert sent["body"]["reasoning_effort"] == "low"
    schema = sent["body"]["response_format"]["json_schema"]["schema"]
    ex = schema["properties"]["days"]["items"]["properties"]["exercises"]["items"]
    assert ex["properties"]["exercise_id"]["enum"] == [3, 5]


def test_length_cutoff_raises(monkeypatch, openai_on):
    monkeypatch.setattr(llm.httpx, "post", lambda *a, **k: _ok("{", finish="length"))
    with pytest.raises(RuntimeError, match="límite de tokens"):
        llm.generate_workout_json("p")


def test_http_error_raises(monkeypatch, openai_on):
    monkeypatch.setattr(llm.httpx, "post", lambda *a, **k: _Resp({"error": "bad"}, status=401))
    with pytest.raises(RuntimeError, match="401"):
        llm.generate_workout_json("p")
