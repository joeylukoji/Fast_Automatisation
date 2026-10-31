"""Génération de workflow : prompt → JSON → validation Pydantic + moteur → réparation."""
from __future__ import annotations

import json
import re
from typing import Callable

from pydantic import ValidationError

from .. import engine
from ..nodes import catalogue
from ..schemas import Workflow
from . import llm

MAX_REPAIRS = 2

LLMFn = Callable[..., str]


def system_prompt() -> str:
    blocks = [
        {"type": b["type"], "description": b["description"], "params": b["params_schema"]["properties"],
         "required": b["params_schema"]["required"], "branching": b["branching"]}
        for b in catalogue()
    ]
    return (
        "Tu génères des workflows d'automatisation au format JSON strict, sans texte autour.\n"
        'Format : {"name": str, "nodes": [{"id": str, "type": str, "params": {}}], '
        '"edges": [{"source": str, "target": str, "branch": "true"|"false"|null}]}\n'
        "Règles :\n"
        "- Utilise UNIQUEMENT les types de blocs listés ci-dessous, avec leurs paramètres.\n"
        "- Un seul déclencheur au début. Pas de cycle.\n"
        "- Un bloc « condition » a deux sorties : chaque lien qui en part porte branch=\"true\" ou \"false\".\n"
        "- Pour utiliser la sortie d'un bloc, écris {{id_du_bloc.champ}} dans un paramètre.\n"
        "- N'invente pas de valeurs secrètes ; mets des valeurs d'exemple claires.\n\n"
        f"Blocs disponibles :\n{json.dumps(blocks, ensure_ascii=False)}"
    )


def _extract_json(text: str) -> dict:
    text = text.strip()
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if fence:
        text = fence.group(1).strip()
    return json.loads(text)


def _check(raw: str) -> tuple[Workflow | None, list[str]]:
    try:
        wf = Workflow.model_validate(_extract_json(raw))
    except json.JSONDecodeError as exc:
        return None, [f"Réponse non JSON : {exc}"]
    except ValidationError as exc:
        return None, [f"{'.'.join(map(str, e['loc']))} : {e['msg']}" for e in exc.errors()]
    errors = engine.validate(wf)
    return (wf if not errors else None), errors


def generate(prompt: str, complete: LLMFn = llm.complete) -> tuple[Workflow | None, list[str], int]:
    """Retourne (workflow valide | None, erreurs de la dernière tentative, nombre de tentatives)."""
    messages = [{"role": "system", "content": system_prompt()}, {"role": "user", "content": prompt}]
    errors: list[str] = []
    for attempt in range(1, MAX_REPAIRS + 2):
        raw = complete(messages, json_mode=True)
        wf, errors = _check(raw)
        if wf is not None:
            return wf, [], attempt
        messages += [
            {"role": "assistant", "content": raw},
            {"role": "user", "content": "Ce workflow est invalide. Corrige-le et renvoie le JSON complet. Erreurs :\n- "
             + "\n- ".join(errors)},
        ]
    return None, errors, MAX_REPAIRS + 1
