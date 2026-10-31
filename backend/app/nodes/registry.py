"""Registre des blocs.

Un bloc est défini UNE seule fois ici ; sa définition sert à la fois :
- d'outil/catalogue pour Gemma 4 (GET /api/nodes, prompt du générateur),
- de formulaire de paramètres dans l'éditeur,
- de code d'exécution dans le moteur.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class RunContext:
    dry_run: bool = True
    trigger_payload: dict[str, Any] = field(default_factory=dict)


RunFn = Callable[[dict[str, Any], dict[str, Any], RunContext], dict[str, Any]]


@dataclass
class NodeSpec:
    type: str
    label: str
    description: str
    params_schema: dict[str, Any]  # JSON Schema (properties, required)
    run: RunFn
    # Bloc à effet de bord ou coûteux : simulé (non exécuté) en dry-run.
    simulated_in_dry_run: bool = False
    # Bloc à deux sorties "true"/"false".
    branching: bool = False
    # Bloc de départ (aucune entrée).
    is_trigger: bool = False


REGISTRY: dict[str, NodeSpec] = {}


def register(spec: NodeSpec) -> NodeSpec:
    REGISTRY[spec.type] = spec
    return spec


def get_spec(node_type: str) -> NodeSpec | None:
    return REGISTRY.get(node_type)


def catalogue() -> list[dict[str, Any]]:
    return [
        {
            "type": s.type,
            "label": s.label,
            "description": s.description,
            "params_schema": s.params_schema,
            "branching": s.branching,
            "is_trigger": s.is_trigger,
            "simulated_in_dry_run": s.simulated_in_dry_run,
        }
        for s in REGISTRY.values()
    ]
