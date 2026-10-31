from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from . import engine
from .ai import generator
from .ai.llm import LLMUnavailable
from .nodes import catalogue
from .schemas import GenerateRequest, GenerateResponse, RunRequest, RunResult

app = FastAPI(title="Kernel API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Historique en mémoire (SQLite si le temps le permet).
RUNS: dict[str, RunResult] = {}


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/nodes")
def list_nodes() -> list[dict]:
    return catalogue()


@app.post("/api/generate", response_model=GenerateResponse)
def generate(req: GenerateRequest) -> GenerateResponse:
    if not req.prompt.strip():
        raise HTTPException(400, "La description est vide.")
    try:
        workflow, errors, attempts = generator.generate(req.prompt)
    except LLMUnavailable as exc:
        raise HTTPException(503, str(exc)) from exc
    return GenerateResponse(workflow=workflow, errors=errors, attempts=attempts)


@app.post("/api/run", response_model=RunResult)
def run_workflow(req: RunRequest) -> RunResult:
    # Contrôle humain : aucune exécution réelle sans validation explicite.
    if not req.dry_run and not req.approved:
        raise HTTPException(400, "Une exécution réelle nécessite la validation explicite de l'utilisateur.")
    result = engine.run(req.workflow, dry_run=req.dry_run, trigger_payload=req.trigger_payload)
    RUNS[result.run_id] = result
    return result


@app.get("/api/runs/{run_id}", response_model=RunResult)
def get_run(run_id: str) -> RunResult:
    if run_id not in RUNS:
        raise HTTPException(404, "Exécution introuvable.")
    return RUNS[run_id]
