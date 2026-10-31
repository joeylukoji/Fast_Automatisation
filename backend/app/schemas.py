"""Schéma interne de Kernel : source de vérité du format de workflow.

L'éditeur visuel (React Flow) et Gemma 4 produisent/consomment ce format.
"""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class Node(BaseModel):
    id: str
    type: str
    params: dict[str, Any] = Field(default_factory=dict)


class Edge(BaseModel):
    source: str
    target: str
    # Pour les blocs à embranchement (condition) : sortie "true" ou "false".
    branch: Literal["true", "false"] | None = None


class Workflow(BaseModel):
    name: str = "Nouveau workflow"
    nodes: list[Node]
    edges: list[Edge] = Field(default_factory=list)


class RunRequest(BaseModel):
    workflow: Workflow
    # Par défaut : simulation. Une exécution réelle exige approved=True.
    dry_run: bool = True
    approved: bool = False
    trigger_payload: dict[str, Any] = Field(default_factory=dict)
    # Facultatif : rattache l'exécution à un workflow enregistré (historique).
    workflow_id: str | None = None


class StepResult(BaseModel):
    node_id: str
    status: Literal["success", "error", "skipped"]
    simulated: bool = False
    output: dict[str, Any] | None = None
    error: str | None = None
    duration_ms: int = 0


class RunResult(BaseModel):
    run_id: str
    dry_run: bool
    status: Literal["success", "error"]
    steps: list[StepResult] = Field(default_factory=list)
    validation_errors: list[str] = Field(default_factory=list)


class GenerateRequest(BaseModel):
    prompt: str


class GenerateResponse(BaseModel):
    workflow: Workflow | None
    errors: list[str] = Field(default_factory=list)
    attempts: int = 0
    # Générateur effectivement utilisé : "gemma" | "local" | "mock".
    source: str | None = None
    # Générateur local : intention prédite et confiance (probabilité softmax).
    intent: str | None = None
    confidence: float | None = None


class WorkflowRecord(BaseModel):
    id: str
    workflow: Workflow
    created_at: str
    updated_at: str
