"""Entraînement, sélection sur validation, évaluation finale sur test synthétique et test manuel.

Usage (depuis la racine du dépôt) : python experiments/train.py
Sorties : experiments/experiments.csv, experiments/results.json, experiments/data_manifest.json,
          backend/app/ai/local_model.json (modèle retenu, inférence pure Python).
"""
import csv, hashlib, json, platform, random, sys
from pathlib import Path

import numpy as np
import sklearn
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score
from sklearn.neighbors import KNeighborsClassifier

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app import engine  # noqa: E402
from app.ai import local_model as lm  # noqa: E402
from app.schemas import Workflow  # noqa: E402

SEED = 42
EXP = ROOT / "experiments"
random.seed(SEED); np.random.seed(SEED)


def load(name):
    return [json.loads(l) for l in (EXP / "data" / name).read_text().splitlines() if l.strip()]


syn = load("synthetic.jsonl")
data = {s: [r for r in syn if r["split"] == s] for s in ("train", "val", "test")}
data["manual"] = load("manual_test.jsonl")
X = {k: [r["prompt"] for r in v] for k, v in data.items()}
Y = {k: [r["intent"] for r in v] for k, v in data.items()}


# ---------- Baselines ----------
class Majority:
    def fit(self, x, y): self.c = max(set(y), key=y.count); return self
    def predict(self, x): return [self.c] * len(x)


class Keywords:
    """Règles écrites à la main, sans apprentissage (baseline crédible)."""
    def fit(self, x, y): return self
    def predict(self, xs):
        out = []
        for t in xs:
            t = lm.normalize(t)
            tg, gm = "telegram" in t, any(k in t for k in ("mail", "courriel", "gmail", "EMAIL"))
            http = "URL" in t.split() or any(k in t for k in ("http", "api", "requete", "page"))
            llm = any(k in t for k in ("resum", "synth", "condens", "gemma", "ia "))
            cond = any(k in t for k in (" si ", "seulement", "quand le code", "condition", "statut", "uniquement si"))
            if http and cond:
                out.append("http_cond_telegram_gmail" if tg and gm else "http_cond_gmail" if gm else "http_cond_telegram")
            elif http:
                p = "http_llm_" if llm else "http_"
                out.append(p + ("gmail" if gm and not tg else "telegram") if (tg or gm) else "http")
            elif llm:
                out.append("llm_gmail" if gm else "llm_telegram" if tg else "llm")
            else:
                out.append("telegram_gmail" if tg and gm else "gmail" if gm else "telegram")
        return out


class Tfidf:
    def __init__(self, kind, C=None, k=None):
        self.kind, self.C, self.k = kind, C, k
        an = dict(analyzer="char_wb", ngram_range=(2, 5)) if kind.startswith("char") else dict(analyzer="word", ngram_range=(1, 2))
        self.vec = TfidfVectorizer(preprocessor=lm.normalize, lowercase=False, sublinear_tf=True, **an)
        self.clf = (KNeighborsClassifier(n_neighbors=k, metric="cosine") if k
                    else LogisticRegression(C=C, max_iter=5000, random_state=SEED))
    def fit(self, x, y): self.clf.fit(self.vec.fit_transform(x), y); return self
    def predict(self, x): return list(self.clf.predict(self.vec.transform(x)))


CANDIDATES = {"B0_majority": lambda: Majority(), "B1_keywords": lambda: Keywords()}
for C in (0.5, 2, 8, 32):
    CANDIDATES[f"M1_char_lr_C{C}"] = lambda C=C: Tfidf("char", C=C)
    CANDIDATES[f"M2_word_lr_C{C}"] = lambda C=C: Tfidf("word", C=C)
for k in (1, 3):
    CANDIDATES[f"M3_char_knn_k{k}"] = lambda k=k: Tfidf("char", k=k)


def blocks(intent): return {b.split(":")[0] for b in lm.INTENTS[intent]} | ({"telegram_send", "gmail_send"} & set(
    "".join(lm.INTENTS[intent]).replace(">", " ").replace("cond:", " ").split()))


def block_f1(yt, yp):
    tp = fp = fn = 0
    for a, b in zip(yt, yp):
        A, B = blocks(a), blocks(b); tp += len(A & B); fp += len(B - A); fn += len(A - B)
    return 2 * tp / (2 * tp + fp + fn)


def wf_checks(prompts, preds):
    valid = runs = 0
    for p, i in zip(prompts, preds):
        wf = Workflow.model_validate(lm.build_workflow(i, p))
        valid += not engine.validate(wf); runs += engine.run(wf, dry_run=True).status == "success"
    return valid / len(prompts), runs / len(prompts)


def boot_ci(yt, yp, n=2000):
    r = np.random.default_rng(SEED); c = np.array([a == b for a, b in zip(yt, yp)], float)
    s = [c[r.integers(0, len(c), len(c))].mean() for _ in range(n)]
    return float(np.percentile(s, 2.5)), float(np.percentile(s, 97.5))


def metrics(split, yp):
    yt = Y[split]
    lo, hi = boot_ci(yt, yp)
    return {"acc": accuracy_score(yt, yp), "acc_ci95": [lo, hi], "macro_f1": f1_score(yt, yp, average="macro", zero_division=0),
            "block_f1": block_f1(yt, yp)}


# ---------- 1) Sélection sur validation uniquement ----------
rows, fitted = [], {}
for name, make in CANDIDATES.items():
    m = make().fit(X["train"], Y["train"]); fitted[name] = m
    v = metrics("val", m.predict(X["val"]))
    rows.append({"exp_id": f"E1-{name}", "model": name, "split": "val", **{k: (round(x, 4) if isinstance(x, float) else x) for k, x in v.items()}})
best = max((r for r in rows if r["model"].startswith("M")), key=lambda r: (r["acc"], r["macro_f1"]))["model"]
print("meilleur sur validation :", best)

# ---------- 2) Évaluation finale (une seule fois) : test synthétique + test manuel ----------
final = {}
for name in ("B0_majority", "B1_keywords", best):
    for split in ("test", "manual"):
        yp = fitted[name].predict(X[split]); mtr = metrics(split, yp)
        mtr["wf_valid"], mtr["dryrun_ok"] = wf_checks(X[split], yp)
        final[f"{name}/{split}"] = mtr
        rows.append({"exp_id": f"E2-{name}-{split}", "model": name, "split": split,
                     **{k: (round(x, 4) if isinstance(x, float) else x) for k, x in mtr.items()}})
        if name == best and split == "manual":
            errors = [(p, t, q) for p, t, q in zip(X[split], Y[split], yp) if t != q]

with open(EXP / "experiments.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["exp_id", "model", "split", "acc", "acc_ci95", "macro_f1", "block_f1", "wf_valid", "dryrun_ok"])
    w.writeheader(); [w.writerow(r) for r in rows]

# ---------- 3) Export du modèle retenu (réentraîné sur train+val) ----------
m = CANDIDATES[best]().fit(X["train"] + X["val"], Y["train"] + Y["val"])
assert isinstance(m.clf, LogisticRegression) and m.kind == "char", "l'export pur Python ne couvre que M1"
vocab = {k: int(v) for k, v in m.vec.vocabulary_.items()}
model_json = {"model": best, "trained_on": "train+val", "seed": SEED, "ngram_range": [2, 5],
              "classes": list(m.clf.classes_), "vocabulary": vocab, "idf": [round(x, 6) for x in m.vec.idf_.tolist()],
              "coef": [[round(x, 6) for x in r] for r in m.clf.coef_.tolist()], "intercept": [round(x, 6) for x in m.clf.intercept_.tolist()]}
out = ROOT / "backend/app/ai/local_model.json"; out.write_text(json.dumps(model_json, ensure_ascii=False, separators=(",", ":")))
pure = lm.LocalModel(out)
agree = np.mean([pure.predict(p)[0] == q for p, q in zip(X["manual"] + X["test"], m.predict(X["manual"] + X["test"]))])
print("accord inférence pure Python / scikit-learn :", agree)

sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
(EXP / "data_manifest.json").write_text(json.dumps({
    "files": {p.name: {"sha256": sha(p), "rows": len(p.read_text().splitlines())} for p in (EXP / "data").glob("*.jsonl")},
    "splits": {k: len(v) for k, v in data.items()}, "classes": len(lm.INTENTS), "generator": "experiments/build_dataset.py (seed 42)",
    "provenance": "Données synthétiques et manuelles rédigées pour ce projet (aucune source externe).",
}, indent=2, ensure_ascii=False))
(EXP / "results.json").write_text(json.dumps({"best_on_val": best, "final": final, "pure_python_agreement": agree,
    "manual_errors": [{"prompt": p, "true": t, "pred": q} for p, t, q in errors],
    "env": {"python": platform.python_version(), "sklearn": sklearn.__version__, "numpy": np.__version__}}, indent=2, ensure_ascii=False))
for k, v in final.items(): print(k, {a: (round(b, 3) if isinstance(b, float) else [round(c, 3) for c in b]) for a, b in v.items()})
