from __future__ import annotations

import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from . import engine, erp, store
from .ai import generator, llm, local_model
from .apps.router import router as apps_router
from .ai.llm import LLMUnavailable
from .nodes import catalogue
from .schemas import GenerateRequest, GenerateResponse, RunRequest, RunResult, Workflow, WorkflowRecord

app = FastAPI(title="Kernel API", version="0.2.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("KERNEL_CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(erp.router)
app.include_router(apps_router)


@app.get("/api/health")
def health() -> dict:
    store.conn()  # vérifie que la base est accessible
    return {"status": "ok", "generator": llm.mode(), "fallback": os.getenv("KERNEL_LLM_FALLBACK") or None,
            "local_model": local_model.MODEL_PATH.exists()}


@app.get("/api/nodes")
def list_nodes() -> list[dict]:
    return catalogue()


@app.post("/api/generate", response_model=GenerateResponse)
def generate(req: GenerateRequest) -> GenerateResponse:
    if not req.prompt.strip():
        raise HTTPException(400, "La description est vide.")
    llm.LAST_SOURCE.set(None)
    try:
        workflow, errors, attempts = generator.generate(req.prompt)
    except LLMUnavailable as exc:
        raise HTTPException(503, str(exc)) from exc
    source = llm.LAST_SOURCE.get()
    intent = confidence = None
    if source == "local":
        intent, confidence = local_model.predict(req.prompt)
    return GenerateResponse(workflow=workflow, errors=errors, attempts=attempts, source=source,
                            intent=intent, confidence=confidence)


@app.post("/api/validate")
def validate(workflow: Workflow) -> dict:
    """Validation seule (utilisée par l'éditeur pour signaler les erreurs en direct)."""
    return {"errors": engine.validate(workflow)}


@app.post("/api/run", response_model=RunResult)
def run_workflow(req: RunRequest) -> RunResult:
    # Contrôle humain : aucune exécution réelle sans validation explicite.
    if not req.dry_run and not req.approved:
        raise HTTPException(400, "Une exécution réelle nécessite la validation explicite de l'utilisateur.")
    result = engine.run(req.workflow, dry_run=req.dry_run, trigger_payload=req.trigger_payload)
    store.save_run(result, req.workflow_id)
    return result


@app.get("/api/runs")
def list_runs(workflow_id: str | None = None, limit: int = 20) -> list[dict]:
    return store.list_runs(workflow_id, min(max(limit, 1), 100))


@app.get("/api/runs/{run_id}", response_model=RunResult)
def get_run(run_id: str) -> RunResult:
    if (run := store.get_run(run_id)) is None:
        raise HTTPException(404, "Exécution introuvable.")
    return run


@app.get("/api/workflows", response_model=list[WorkflowRecord])
def list_workflows() -> list[WorkflowRecord]:
    return store.list_workflows()


@app.post("/api/workflows", response_model=WorkflowRecord, status_code=201)
def create_workflow(workflow: Workflow) -> WorkflowRecord:
    return store.save_workflow(workflow)


@app.get("/api/workflows/{wf_id}", response_model=WorkflowRecord)
def get_workflow(wf_id: str) -> WorkflowRecord:
    if (rec := store.get_workflow(wf_id)) is None:
        raise HTTPException(404, "Workflow introuvable.")
    return rec


@app.put("/api/workflows/{wf_id}", response_model=WorkflowRecord)
def update_workflow(wf_id: str, workflow: Workflow) -> WorkflowRecord:
    if store.get_workflow(wf_id) is None:
        raise HTTPException(404, "Workflow introuvable.")
    return store.save_workflow(workflow, wf_id)


@app.delete("/api/workflows/{wf_id}", status_code=204)
def delete_workflow(wf_id: str) -> None:
    if not store.delete_workflow(wf_id):
        raise HTTPException(404, "Workflow introuvable.")
