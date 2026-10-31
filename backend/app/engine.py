"""Validation et exécution d'un workflow (graphe orienté acyclique)."""
from __future__ import annotations

import re
import time
import uuid
from collections import defaultdict, deque
from typing import Any

from .nodes import RunContext, get_spec
from .schemas import Edge, RunResult, StepResult, Workflow

_TEMPLATE = re.compile(r"\{\{\s*([\w\-]+)\.([\w\.\-]+)\s*\}\}")


# --- Validation -------------------------------------------------------------
def validate(workflow: Workflow) -> list[str]:
    errors: list[str] = []
    ids = [n.id for n in workflow.nodes]
    if len(ids) != len(set(ids)):
        errors.append("Les identifiants de blocs doivent être uniques.")
    by_id = {n.id: n for n in workflow.nodes}

    if not workflow.nodes:
        return ["Le workflow ne contient aucun bloc."]

    for node in workflow.nodes:
        spec = get_spec(node.type)
        if spec is None:
            errors.append(f"Bloc « {node.id} » : type inconnu « {node.type} ».")
            continue
        for key in spec.params_schema.get("required", []):
            if node.params.get(key) in (None, ""):
                errors.append(f"Bloc « {node.id} » : paramètre obligatoire « {key} » manquant.")

    for e in workflow.edges:
        if e.source not in by_id or e.target not in by_id:
            errors.append(f"Lien {e.source} → {e.target} : bloc inexistant.")
            continue
        src_spec = get_spec(by_id[e.source].type)
        if src_spec and src_spec.branching and e.branch is None:
            errors.append(f"Lien depuis « {e.source} » : la branche « true » ou « false » est requise.")
        if src_spec and not src_spec.branching and e.branch is not None:
            errors.append(f"Lien depuis « {e.source} » : ce bloc n'a pas de branches.")
        tgt_spec = get_spec(by_id[e.target].type)
        if tgt_spec and tgt_spec.is_trigger:
            errors.append(f"Le déclencheur « {e.target} » ne peut pas avoir d'entrée.")

    if not any((s := get_spec(n.type)) and s.is_trigger for n in workflow.nodes):
        errors.append("Il faut au moins un déclencheur (trigger_manual).")

    if not errors and _topological_order(workflow) is None:
        errors.append("Le workflow contient un cycle.")
    return errors


def _topological_order(workflow: Workflow) -> list[str] | None:
    indeg = {n.id: 0 for n in workflow.nodes}
    out: dict[str, list[str]] = defaultdict(list)
    for e in workflow.edges:
        out[e.source].append(e.target)
        indeg[e.target] += 1
    queue = deque(i for i, d in indeg.items() if d == 0)
    order: list[str] = []
    while queue:
        cur = queue.popleft()
        order.append(cur)
        for nxt in out[cur]:
            indeg[nxt] -= 1
            if indeg[nxt] == 0:
                queue.append(nxt)
    return order if len(order) == len(indeg) else None


# --- Gabarits {{bloc.champ}} ------------------------------------------------
def _lookup(outputs: dict[str, dict], node_id: str, path: str) -> Any:
    cur: Any = outputs[node_id]
    for part in path.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        elif isinstance(cur, list) and part.isdigit() and int(part) < len(cur):
            cur = cur[int(part)]
        else:
            raise KeyError(f"{node_id}.{path}")
    return cur


def resolve(value: Any, outputs: dict[str, dict], strict: bool) -> Any:
    """Remplace {{bloc.champ}} par les sorties des blocs déjà exécutés.

    En simulation (strict=False), une référence introuvable est conservée telle quelle,
    car les sorties simulées n'ont pas les vrais champs.
    """
    if isinstance(value, str):
        def sub(m: re.Match) -> str:
            node_id, path = m.group(1), m.group(2)
            try:
                return str(_lookup(outputs, node_id, path))
            except KeyError:
                if strict:
                    raise ValueError(f"Référence introuvable : {{{{{node_id}.{path}}}}}")
                return m.group(0)

        return _TEMPLATE.sub(sub, value)
    if isinstance(value, dict):
        return {k: resolve(v, outputs, strict) for k, v in value.items()}
    if isinstance(value, list):
        return [resolve(v, outputs, strict) for v in value]
    return value


# --- Exécution --------------------------------------------------------------
def run(workflow: Workflow, dry_run: bool = True, trigger_payload: dict | None = None) -> RunResult:
    run_id = uuid.uuid4().hex[:12]
    errors = validate(workflow)
    if errors:
        return RunResult(run_id=run_id, dry_run=dry_run, status="error", validation_errors=errors)

    ctx = RunContext(dry_run=dry_run, trigger_payload=trigger_payload or {})
    by_id = {n.id: n for n in workflow.nodes}
    incoming: dict[str, list[Edge]] = defaultdict(list)
    for e in workflow.edges:
        incoming[e.target].append(e)

    outputs: dict[str, dict] = {}
    steps: list[StepResult] = []
    failed = False

    for node_id in _topological_order(workflow) or []:
        node, spec = by_id[node_id], get_spec(by_id[node_id].type)
        assert spec is not None

        if failed:
            steps.append(StepResult(node_id=node_id, status="skipped"))
            continue

        # Un bloc s'exécute s'il n'a pas d'entrée, ou si au moins un lien entrant est actif.
        edges = incoming[node_id]
        active = [
            e for e in edges
            if e.source in outputs and (e.branch is None or outputs[e.source].get("branch") == e.branch)
        ]
        if edges and not active:
            steps.append(StepResult(node_id=node_id, status="skipped"))
            continue

        started = time.perf_counter()
        simulated = dry_run and spec.simulated_in_dry_run
        try:
            params = resolve(node.params, outputs, strict=not dry_run)
            if simulated:
                output = {"simulated": True, "would_run_with": params}
            else:
                output = spec.run(params, {e.source: outputs[e.source] for e in active}, ctx)
            outputs[node_id] = output
            status, err = "success", None
        except Exception as exc:  # noqa: BLE001 - toute erreur de bloc est rapportée à l'utilisateur
            output, status, err = None, "error", str(exc)
            failed = True
        steps.append(
            StepResult(
                node_id=node_id,
                status=status,
                simulated=simulated,
                output=output,
                error=err,
                duration_ms=int((time.perf_counter() - started) * 1000),
            )
        )

    return RunResult(run_id=run_id, dry_run=dry_run, status="error" if failed else "success", steps=steps)
