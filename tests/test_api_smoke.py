from fastapi.testclient import TestClient

from discourse_engine.api.server import app


client = TestClient(app)


def test_discourse_analysis_raw_text():
    payload = {
        "sourceType": "raw_text",
        "rawText": "Either you support this bill or you hate this country.",
    }
    resp = client.post("/api/analysis/discourse", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "segments" in data
    assert "originalText" in data
    assert data["originalText"].startswith("Either you support")


def test_character_arcs_raw_text():
    payload = {
        "sourceType": "raw_text",
        "rawText": "Speaker: Hello there.\nSpeaker: We must protect our people from this threat.",
    }
    resp = client.post("/api/character-arcs/analyze", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "characters" in data
    assert "arcs" in data
    assert data["originalText"].startswith("Speaker:")

