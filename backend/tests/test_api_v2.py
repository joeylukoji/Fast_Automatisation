from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
WF = {"name": "Démo", "nodes": [{"id": "start", "type": "trigger_manual", "params": {}},
                                {"id": "t", "type": "telegram_send", "params": {"chat_id": "1", "text": "x"}}],
      "edges": [{"source": "start", "target": "t"}]}


def test_workflow_crud_and_run_history():
    rec = client.post("/api/workflows", json=WF)
    assert rec.status_code == 201
    wf_id = rec.json()["id"]
    assert [w["id"] for w in client.get("/api/workflows").json()] == [wf_id]
    upd = client.put(f"/api/workflows/{wf_id}", json=WF | {"name": "Renommé"})
    assert upd.json()["workflow"]["name"] == "Renommé"

    run = client.post("/api/run", json={"workflow": WF, "dry_run": True, "workflow_id": wf_id}).json()
    hist = client.get("/api/runs", params={"workflow_id": wf_id}).json()
    assert hist[0]["id"] == run["run_id"] and hist[0]["dry_run"] is True
    assert client.get(f"/api/runs/{run['run_id']}").json()["status"] == "success"

    assert client.delete(f"/api/workflows/{wf_id}").status_code == 204
    assert client.get(f"/api/workflows/{wf_id}").status_code == 404
    assert client.get(f"/api/runs/{run['run_id']}").status_code == 200  # l'historique survit


def test_validate_endpoint():
    bad = WF | {"edges": [{"source": "t", "target": "start"}]}
    assert client.post("/api/validate", json=WF).json() == {"errors": []}
    assert client.post("/api/validate", json=bad).json()["errors"]


def test_generate_reports_source_and_intent(monkeypatch):
    monkeypatch.setenv("KERNEL_LLM_LOCAL", "1")
    body = client.post("/api/generate", json={"prompt": "Résume ce texte et envoie-le sur Telegram"}).json()
    assert body["source"] == "local" and body["intent"] == "llm_telegram" and 0 < body["confidence"] <= 1
    assert client.get("/api/health").json()["generator"] == "local"


def test_fallback_to_local_when_gemma_unreachable(monkeypatch):
    monkeypatch.setenv("KERNEL_LLM_BASE_URL", "http://127.0.0.1:9/v1")  # port fermé
    monkeypatch.setenv("KERNEL_LLM_MODEL", "gemma")
    monkeypatch.setenv("KERNEL_LLM_FALLBACK", "local")
    body = client.post("/api/generate", json={"prompt": "Envoie un mail à a@b.fr"}).json()
    assert body["source"] == "local" and body["workflow"] is not None


def test_mock_source(monkeypatch):
    monkeypatch.setenv("KERNEL_LLM_MOCK", "1")
    assert client.post("/api/generate", json={"prompt": "x"}).json()["source"] == "mock"
