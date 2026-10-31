"""Générateur local (hors-ligne) : prompt → intention → workflow.

Un classifieur TF-IDF + régression logistique (entraîné dans experiments/train.py, exporté en
JSON) prédit l'intention parmi INTENTS ; build_workflow() construit ensuite un workflow valide et
remplit les paramètres par extraction (URL, e-mail, chat id). Inférence en Python pur : aucune
dépendance d'apprentissage au moment de l'exécution.

Usage : KERNEL_LLM_LOCAL=1 (secours quand Gemma 4 n'est pas disponible).
"""
from __future__ import annotations

import json
import math
import re
import unicodedata
from pathlib import Path

MODEL_PATH = Path(__file__).with_name("local_model.json")

# Intention → chaîne de blocs. "cond:T>F" = condition dont la branche true va vers T et false vers F.
INTENTS: dict[str, list[str]] = {
    "telegram": ["telegram_send"],
    "gmail": ["gmail_send"],
    "telegram_gmail": ["telegram_send", "gmail_send"],
    "llm": ["llm"],
    "llm_telegram": ["llm", "telegram_send"],
    "llm_gmail": ["llm", "gmail_send"],
    "http": ["http_request"],
    "http_telegram": ["http_request", "telegram_send"],
    "http_gmail": ["http_request", "gmail_send"],
    "http_llm_telegram": ["http_request", "llm", "telegram_send"],
    "http_llm_gmail": ["http_request", "llm", "gmail_send"],
    "http_cond_telegram": ["http_request", "cond:telegram_send>"],
    "http_cond_gmail": ["http_request", "cond:gmail_send>"],
    "http_cond_telegram_gmail": ["http_request", "cond:telegram_send>gmail_send"],
}

_URL = re.compile(r"https?://[^\s«»\"'<>,]+")
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_CHAT = re.compile(r"(?:chat|canal|groupe|id)\D{0,12}(-?\d{4,})", re.I)
_STATUS = re.compile(r"\b([1-5]\d\d)\b")


def _params(block: str, prev: str | None, prompt: str) -> dict:
    url = (_URL.search(prompt) or [None])[0] or "https://example.com"
    email = (_EMAIL.search(prompt) or [None])[0] or "destinataire@example.com"
    chat = m.group(1) if (m := _CHAT.search(prompt)) else "123456"
    src = f"{{{{{prev}.text}}}}" if prev else prompt
    if block == "http_request":
        return {"url": url, "method": "GET"}
    if block == "llm":
        return {"prompt": f"Résume en quelques phrases : {src}"}
    if block == "telegram_send":
        return {"chat_id": chat, "text": src}
    if block == "gmail_send":
        return {"to": email, "subject": "Notification Kernel", "body": src}
    raise ValueError(block)


def build_workflow(intent: str, prompt: str) -> dict:
    """Construit un workflow conforme au schéma Kernel pour une intention donnée."""
    nodes = [{"id": "start", "type": "trigger_manual", "params": {}}]
    edges: list[dict] = []
    prev = "start"
    for i, step in enumerate(INTENTS[intent], 1):
        if step.startswith("cond:"):
            on_true, on_false = step[5:].split(">")
            status = (_STATUS.search(prompt) or [None, "200"])[1]
            nodes.append({"id": "check", "type": "condition",
                          "params": {"left": f"{{{{{prev}.status}}}}", "operator": "equals", "right": status}})
            edges.append({"source": prev, "target": "check"})
            for branch, block in (("true", on_true), ("false", on_false)):
                if block:
                    nid = f"{block.split('_')[0]}_{branch}"
                    nodes.append({"id": nid, "type": block, "params": _params(block, prev, prompt)})
                    edges.append({"source": "check", "target": nid, "branch": branch})
            continue
        nid = f"{step.split('_')[0]}_{i}"
        nodes.append({"id": nid, "type": step, "params": _params(step, None if prev == "start" else prev, prompt)})
        edges.append({"source": prev, "target": nid})
        # Deux envois en parallèle (telegram_gmail) : tous deux partent du même bloc.
        if not (intent == "telegram_gmail"):
            prev = nid
    return {"name": prompt[:60] or "Workflow", "nodes": nodes, "edges": edges}


# ---------- Classifieur (inférence pure Python, mêmes calculs que scikit-learn) ----------

def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", text.lower())
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = _URL.sub(" URL ", text)
    return _EMAIL.sub(" EMAIL ", text)


def _char_ngrams(text: str, lo: int, hi: int) -> list[str]:
    # Reproduit TfidfVectorizer(analyzer="char_wb").
    grams = []
    for word in re.sub(r"\s\s+", " ", text).split():
        w = f" {word} "
        for n in range(lo, hi + 1):
            grams += [w[i:i + n] for i in range(max(1, len(w) - n + 1))]
            if len(w) <= n:  # mot court compté une seule fois
                break
    return grams


class LocalModel:
    def __init__(self, path: Path = MODEL_PATH):
        m = json.loads(path.read_text())
        self.vocab: dict[str, int] = m["vocabulary"]
        self.idf: list[float] = m["idf"]
        self.coef: list[list[float]] = m["coef"]
        self.intercept: list[float] = m["intercept"]
        self.classes: list[str] = m["classes"]
        self.ngram = tuple(m["ngram_range"])

    def scores(self, prompt: str) -> list[float]:
        counts: dict[int, int] = {}
        for g in _char_ngrams(normalize(prompt), *self.ngram):
            if (j := self.vocab.get(g)) is not None:
                counts[j] = counts.get(j, 0) + 1
        vec = {j: (1 + math.log(c)) * self.idf[j] for j, c in counts.items()}  # sublinear_tf
        norm = math.sqrt(sum(v * v for v in vec.values())) or 1.0
        return [b + sum(w[j] * v / norm for j, v in vec.items()) for w, b in zip(self.coef, self.intercept)]

    def predict(self, prompt: str) -> tuple[str, float]:
        s = self.scores(prompt)
        mx = max(s)
        exp = [math.exp(x - mx) for x in s]
        k = s.index(mx)
        return self.classes[k], exp[k] / sum(exp)


_MODEL: LocalModel | None = None


def generate(prompt: str) -> dict:
    global _MODEL
    if _MODEL is None:
        _MODEL = LocalModel()
    intent, _ = _MODEL.predict(prompt)
    return build_workflow(intent, prompt)
