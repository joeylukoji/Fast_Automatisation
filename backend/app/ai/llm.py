"""Client LLM unique, compatible avec l'API « chat completions » de type OpenAI.

Fonctionne avec un Gemma 4 auto-hébergé (Ollama, vLLM, llama.cpp server) ou avec tout
fournisseur exposant ce format. Variables d'environnement :

  KERNEL_LLM_BASE_URL   ex. http://localhost:11434/v1  (Ollama)
  KERNEL_LLM_MODEL      nom EXACT du modèle chez votre fournisseur (à vérifier)
  KERNEL_LLM_API_KEY    clé si nécessaire
  KERNEL_LLM_MOCK=1     renvoie un workflow d'exemple, sans appeler de modèle (démo hors-ligne)
  KERNEL_LLM_LOCAL=1    générateur local entraîné (ai/local_model.py) : hors-ligne, dépend du prompt
"""
from __future__ import annotations

import json
import os

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


def complete(messages: list[dict], json_mode: bool = False) -> str:
    if os.getenv("KERNEL_LLM_LOCAL") == "1" and json_mode:
        from . import local_model
        prompt = next((m["content"] for m in messages if m["role"] == "user"), "")
        return json.dumps(local_model.generate(prompt), ensure_ascii=False)
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
    resp = httpx.post(f"{base_url.rstrip('/')}/chat/completions", json=payload, headers=headers, timeout=120)
    if resp.status_code >= 400:
        raise LLMUnavailable(f"Le fournisseur LLM a répondu {resp.status_code} : {resp.text[:300]}")
    return resp.json()["choices"][0]["message"]["content"]
