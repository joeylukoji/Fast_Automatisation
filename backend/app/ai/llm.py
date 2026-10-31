"""Client LLM unique, compatible avec l'API « chat completions » de type OpenAI.

Fonctionne avec un Gemma 4 auto-hébergé (Ollama, vLLM, llama.cpp server) ou avec tout
fournisseur exposant ce format. Variables d'environnement :

  KERNEL_LLM_BASE_URL   ex. http://localhost:11434/v1  (Ollama)
  KERNEL_LLM_MODEL      nom EXACT du modèle chez votre fournisseur (à vérifier)
  KERNEL_LLM_API_KEY    clé si nécessaire
  KERNEL_LLM_MOCK=1     renvoie un workflow d'exemple, sans appeler de modèle (démo hors-ligne)
  KERNEL_LLM_LOCAL=1    générateur local entraîné (ai/local_model.py) : hors-ligne, dépend du prompt
  KERNEL_LLM_FALLBACK=local  si Gemma n'est pas configuré ou ne répond pas, bascule sur le générateur local
"""
from __future__ import annotations

import contextvars
import json
import os
import re

import httpx


class LLMUnavailable(RuntimeError):
    pass


MOCK_WORKFLOW = {
    "name": "Résumé quotidien sur Telegram",
    "nodes": [
        {"id": "start", "type": "trigger_manual", "params": {}},
        {"id": "summary", "type": "llm", "params": {"prompt": "Résume en une phrase : {{start.text}}"}},
        {"id": "notify", "type": "telegram_send", "params": {"chat_id": "123456", "text": "{{summary.text}}"}},
    ],
    "edges": [{"source": "start", "target": "summary"}, {"source": "summary", "target": "notify"}],
}


# Générateur réellement utilisé pour la dernière complétion de la requête en cours.
LAST_SOURCE: contextvars.ContextVar[str | None] = contextvars.ContextVar("LAST_SOURCE", default=None)


def mode() -> str | None:
    """Générateur qui sera utilisé : "local", "mock", "gemma" ou None (rien de configuré)."""
    if os.getenv("KERNEL_LLM_LOCAL") == "1":
        return "local"
    if os.getenv("KERNEL_LLM_MOCK") == "1":
        return "mock"
    if os.getenv("KERNEL_LLM_BASE_URL") and os.getenv("KERNEL_LLM_MODEL"):
        return "gemma"
    return "local" if os.getenv("KERNEL_LLM_FALLBACK") == "local" else None


def _local(messages: list[dict]) -> str:
    from . import local_model
    prompt = next((m["content"] for m in messages if m["role"] == "user"), "")
    return json.dumps(local_model.generate(prompt), ensure_ascii=False)


def complete(messages: list[dict], json_mode: bool = False) -> str:
    current = mode()
    if current == "local" and json_mode:
        LAST_SOURCE.set("local")
        return _local(messages)
    if current == "gemma" and os.getenv("KERNEL_LLM_FALLBACK") == "local" and json_mode:
        try:
            out = _remote(messages, json_mode)
            LAST_SOURCE.set("gemma")
            return out
        except LLMUnavailable:
            LAST_SOURCE.set("local")
            return _local(messages)
    out = _remote(messages, json_mode)
    LAST_SOURCE.set("mock" if os.getenv("KERNEL_LLM_MOCK") == "1" else "gemma")
    return out


def _remote(messages: list[dict], json_mode: bool) -> str:
    if os.getenv("KERNEL_LLM_MOCK") == "1":
        return json.dumps(MOCK_WORKFLOW) if json_mode else "[réponse simulée du LLM]"

    base_url, model = os.getenv("KERNEL_LLM_BASE_URL"), os.getenv("KERNEL_LLM_MODEL")
    if not base_url or not model:
        raise LLMUnavailable(
            "Modèle non configuré : définissez KERNEL_LLM_BASE_URL et KERNEL_LLM_MODEL "
            "(ou KERNEL_LLM_MOCK=1 pour la démo hors-ligne)."
        )
    headers = {}
    if key := os.getenv("KERNEL_LLM_API_KEY"):
        headers["Authorization"] = f"Bearer {key}"
    payload: dict = {"model": model, "messages": messages, "temperature": 0.2}
    if json_mode:
        payload["response_format"] = {"type": "json_object"}
    url = f"{base_url.rstrip('/')}/chat/completions"
    try:
        resp = httpx.post(url, json=payload, headers=headers, timeout=120)
        # Certains fournisseurs (Gemma via l'API Gemini) rejettent response_format : on réessaie sans.
        if resp.status_code >= 400 and "response_format" in payload:
            payload.pop("response_format")
            resp = httpx.post(url, json=payload, headers=headers, timeout=120)
    except httpx.HTTPError as exc:
        raise LLMUnavailable(f"Fournisseur LLM injoignable : {exc}") from exc
    if resp.status_code >= 400:
        raise LLMUnavailable(f"Le fournisseur LLM a répondu {resp.status_code} : {resp.text[:300]}")
    content = resp.json()["choices"][0]["message"]["content"]
    # Gemma 4 peut préfixer sa réponse d'un bloc de raisonnement <thought>…</thought>.
    return re.sub(r"<thought>.*?</thought>", "", content, flags=re.DOTALL).strip()
