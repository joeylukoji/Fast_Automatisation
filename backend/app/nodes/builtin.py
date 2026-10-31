"""Blocs du MVP : déclencheur, HTTP, LLM, condition, Telegram, Gmail."""
from __future__ import annotations

from typing import Any

import httpx

from ..connectors import gmail, telegram
from .registry import NodeSpec, RunContext, register


def _obj(properties: dict[str, Any], required: list[str] | None = None) -> dict[str, Any]:
    return {"type": "object", "properties": properties, "required": required or []}


def _str(title: str, description: str = "", default: str | None = None) -> dict[str, Any]:
    d: dict[str, Any] = {"type": "string", "title": title, "description": description}
    if default is not None:
        d["default"] = default
    return d


# --- Déclencheur manuel -----------------------------------------------------
def _run_trigger(params: dict, inputs: dict, ctx: RunContext) -> dict:
    return dict(ctx.trigger_payload)


register(
    NodeSpec(
        type="trigger_manual",
        label="Déclencheur manuel",
        description="Point de départ du workflow, lancé à la main.",
        params_schema=_obj({}),
        run=_run_trigger,
        is_trigger=True,
    )
)


# --- Requête HTTP -----------------------------------------------------------
def _run_http(params: dict, inputs: dict, ctx: RunContext) -> dict:
    method = (params.get("method") or "GET").upper()
    resp = httpx.request(method, params["url"], content=params.get("body") or None, timeout=15)
    try:
        data: Any = resp.json()
    except ValueError:
        data = None
    return {"status": resp.status_code, "json": data, "text": resp.text[:2000]}


register(
    NodeSpec(
        type="http_request",
        label="Requête HTTP",
        description="Appelle une URL et renvoie status, json et text.",
        params_schema=_obj(
            {
                "url": _str("URL"),
                "method": {"type": "string", "title": "Méthode", "enum": ["GET", "POST"], "default": "GET"},
                "body": _str("Corps (POST)"),
            },
            ["url"],
        ),
        run=_run_http,
        simulated_in_dry_run=True,
    )
)


# --- LLM --------------------------------------------------------------------
def _run_llm(params: dict, inputs: dict, ctx: RunContext) -> dict:
    from ..ai.llm import complete  # import tardif : évite une dépendance circulaire

    text = complete([{"role": "user", "content": params["prompt"]}])
    return {"text": text}


register(
    NodeSpec(
        type="llm",
        label="LLM (Gemma)",
        description="Envoie un prompt au modèle et renvoie {text}.",
        params_schema=_obj({"prompt": _str("Prompt")}, ["prompt"]),
        run=_run_llm,
        simulated_in_dry_run=True,
    )
)


# --- Condition --------------------------------------------------------------
_OPERATORS = ["equals", "not_equals", "contains", "gt", "lt"]


def _run_condition(params: dict, inputs: dict, ctx: RunContext) -> dict:
    left, right = str(params.get("left", "")), str(params.get("right", ""))
    op = params.get("operator", "equals")
    if op == "equals":
        result = left == right
    elif op == "not_equals":
        result = left != right
    elif op == "contains":
        result = right in left
    elif op in ("gt", "lt"):
        try:
            a, b = float(left), float(right)
        except ValueError as exc:
            raise ValueError(f"Comparaison numérique impossible : {left!r} / {right!r}") from exc
        result = a > b if op == "gt" else a < b
    else:
        raise ValueError(f"Opérateur inconnu : {op}")
    return {"result": result, "branch": "true" if result else "false"}


register(
    NodeSpec(
        type="condition",
        label="Condition",
        description="Compare deux valeurs et suit la sortie 'true' ou 'false'.",
        params_schema=_obj(
            {
                "left": _str("Valeur de gauche"),
                "operator": {"type": "string", "title": "Opérateur", "enum": _OPERATORS, "default": "equals"},
                "right": _str("Valeur de droite"),
            },
            ["left", "operator", "right"],
        ),
        run=_run_condition,
        branching=True,
    )
)


# --- Telegram ---------------------------------------------------------------
def _run_telegram(params: dict, inputs: dict, ctx: RunContext) -> dict:
    return telegram.send_message(params["chat_id"], params["text"])


register(
    NodeSpec(
        type="telegram_send",
        label="Telegram : envoyer",
        description="Envoie un message Telegram via un bot.",
        params_schema=_obj(
            {"chat_id": _str("Chat ID"), "text": _str("Message")},
            ["chat_id", "text"],
        ),
        run=_run_telegram,
        simulated_in_dry_run=True,
    )
)


# --- Gmail ------------------------------------------------------------------
def _run_gmail(params: dict, inputs: dict, ctx: RunContext) -> dict:
    return gmail.send_email(params["to"], params["subject"], params["body"], params.get("html") or None)


register(
    NodeSpec(
        type="gmail_send",
        label="Gmail : envoyer",
        description="Envoie un e-mail depuis le compte Gmail configuré.",
        params_schema=_obj(
            {"to": _str("Destinataire"), "subject": _str("Objet"), "body": _str("Message"),
             "html": _str("HTML (facultatif)", "Version HTML : e-mail multipart texte + HTML.")},
            ["to", "subject", "body"],
        ),
        run=_run_gmail,
        simulated_in_dry_run=True,
    )
)
