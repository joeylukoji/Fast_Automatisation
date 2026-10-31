import json

from fastapi.testclient import TestClient

from app import engine
from app.ai import generator
from app.main import app
from app.schemas import Edge, Node, Workflow

client = TestClient(app)


def branching_workflow() -> Workflow:
    return Workflow(
        nodes=[
            Node(id="start", type="trigger_manual"),
            Node(id="check", type="condition", params={"left": "{{start.n}}", "operator": "gt", "right": "10"}),
            Node(id="big", type="telegram_send", params={"chat_id": "1", "text": "grand"}),
            Node(id="small", type="telegram_send", params={"chat_id": "1", "text": "petit"}),
        ],
        edges=[
            Edge(source="start", target="check"),
            Edge(source="check", target="big", branch="true"),
            Edge(source="check", target="small", branch="false"),
        ],
    )


def test_cycle_detected():
    wf = Workflow(
        nodes=[Node(id="a", type="trigger_manual"), Node(id="b", type="condition", params={"left": "1", "operator": "equals", "right": "1"})],
        edges=[Edge(source="b", target="b", branch="true")],
    )
    assert any("cycle" in e.lower() for e in engine.validate(wf))


def test_missing_param_and_unknown_type():
    wf = Workflow(nodes=[Node(id="a", type="trigger_manual"), Node(id="b", type="gmail_send"), Node(id="c", type="nope")])
    errors = engine.validate(wf)
    assert any("« to »" in e for e in errors)
    assert any("inconnu" in e for e in errors)


def test_condition_branches_real_run():
    res = engine.run(branching_workflow(), dry_run=False, trigger_payload={"n": 42})
    # Les blocs Telegram échouent sans token : on vérifie seulement l'aiguillage.
    status = {s.node_id: s.status for s in res.steps}
    assert status["check"] == "success"
    assert status["small"] == "skipped"
    assert status["big"] in ("success", "error")


def test_dry_run_simulates_side_effects():
    res = engine.run(branching_workflow(), dry_run=True, trigger_payload={"n": 3})
    by = {s.node_id: s for s in res.steps}
    assert res.status == "success"
    assert by["small"].simulated and by["small"].status == "success"
    assert by["big"].status == "skipped"


def test_generator_repairs_invalid_output():
    good = {
        "name": "t",
        "nodes": [{"id": "s", "type": "trigger_manual", "params": {}}],
        "edges": [],
    }
    bad = {"name": "t", "nodes": [{"id": "s", "type": "inconnu", "params": {}}], "edges": []}
    replies = iter([json.dumps(bad), "```json\n" + json.dumps(good) + "\n```"])
    wf, errors, attempts = generator.generate("x", complete=lambda messages, json_mode=False: next(replies))
    assert wf is not None and errors == [] and attempts == 2


def test_generator_gives_up_after_repairs():
    wf, errors, attempts = generator.generate("x", complete=lambda messages, json_mode=False: "pas du json")
    assert wf is None and errors and attempts == generator.MAX_REPAIRS + 1


def test_api_nodes_and_approval_gate():
    nodes = client.get("/api/nodes").json()
    assert {n["type"] for n in nodes} >= {"trigger_manual", "condition", "telegram_send", "gmail_send"}

    body = {"workflow": branching_workflow().model_dump(), "dry_run": False, "approved": False}
    assert client.post("/api/run", json=body).status_code == 400

    body = {"workflow": branching_workflow().model_dump(), "dry_run": True, "trigger_payload": {"n": 50}}
    r = client.post("/api/run", json=body)
    assert r.status_code == 200
    assert client.get(f"/api/runs/{r.json()['run_id']}").status_code == 200


def test_generate_without_llm_config_returns_503(monkeypatch):
    monkeypatch.delenv("KERNEL_LLM_BASE_URL", raising=False)
    monkeypatch.delenv("KERNEL_LLM_MOCK", raising=False)
    assert client.post("/api/generate", json={"prompt": "hello"}).status_code == 503


def test_generate_mock_mode(monkeypatch):
    monkeypatch.setenv("KERNEL_LLM_MOCK", "1")
    r = client.post("/api/generate", json={"prompt": "hello"})
    assert r.status_code == 200 and r.json()["workflow"] is not None
