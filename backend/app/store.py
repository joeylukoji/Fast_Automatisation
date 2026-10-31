"""Persistance SQLite (bibliothèque standard) : workflows enregistrés et historique des exécutions.

KERNEL_DB_PATH : chemin du fichier (défaut data/kernel.db ; ":memory:" pour les tests).
"""
from __future__ import annotations

import json
import os
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path

from .schemas import RunResult, Workflow, WorkflowRecord

_LOCK = threading.Lock()
_CONN: sqlite3.Connection | None = None

SCHEMA = """
CREATE TABLE IF NOT EXISTS workflow (
  id TEXT PRIMARY KEY, name TEXT NOT NULL, definition TEXT NOT NULL,
  created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS run (
  id TEXT PRIMARY KEY, workflow_id TEXT REFERENCES workflow(id) ON DELETE SET NULL,
  dry_run INTEGER NOT NULL, status TEXT NOT NULL CHECK (status IN ('success','error')),
  result TEXT NOT NULL, started_at TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS run_by_workflow ON run(workflow_id, started_at);
CREATE TABLE IF NOT EXISTS customer (
  id TEXT PRIMARY KEY, name TEXT NOT NULL, email TEXT NOT NULL UNIQUE, phone TEXT,
  created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS product (
  id TEXT PRIMARY KEY, name TEXT NOT NULL, unit TEXT, price_usd REAL NOT NULL, created_at TEXT NOT NULL,
  active INTEGER NOT NULL DEFAULT 1);
CREATE TABLE IF NOT EXISTS sale (
  id TEXT PRIMARY KEY, invoice_number TEXT NOT NULL UNIQUE, customer_id TEXT NOT NULL REFERENCES customer(id),
  items TEXT NOT NULL, total_usd REAL NOT NULL, total_cdf REAL NOT NULL, rate REAL NOT NULL,
  created_at TEXT NOT NULL, invoice_status TEXT NOT NULL DEFAULT 'not_sent'
    CHECK (invoice_status IN ('sent','failed','not_sent')),
  run_ids TEXT NOT NULL DEFAULT '[]');
CREATE TABLE IF NOT EXISTS app_build (
  id TEXT PRIMARY KEY, app TEXT NOT NULL, prompt TEXT NOT NULL, spec TEXT NOT NULL, diff TEXT NOT NULL,
  lines_changed INTEGER NOT NULL, status TEXT NOT NULL CHECK (status IN ('applied','rejected')),
  source TEXT, error TEXT, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS app_state (key TEXT PRIMARY KEY, value TEXT NOT NULL);
"""

# Catalogue de départ (ERP), inséré si la table product est vide.
SEED_PRODUCTS = [
    ("Casier Primus 72cl", "casier", 18), ("Sac de riz 25 kg", "sac", 32), ("Bidon d'huile 5 L", "bidon", 9),
    ("Sac de sucre 10 kg", "sac", 12), ("Farine de maïs 25 kg", "sac", 22), ("Pack d'eau 1,5 L x6", "pack", 3.5),
]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def conn() -> sqlite3.Connection:
    global _CONN
    if _CONN is None:
        path = os.getenv("KERNEL_DB_PATH", "data/kernel.db")
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        _CONN = sqlite3.connect(path, check_same_thread=False)
        _CONN.row_factory = sqlite3.Row
        _CONN.execute("PRAGMA foreign_keys = ON")
        _CONN.executescript(SCHEMA)
        # Migration : bases antérieures sans colonne product.active.
        if "active" not in {r["name"] for r in _CONN.execute("PRAGMA table_info(product)")}:
            _CONN.execute("ALTER TABLE product ADD COLUMN active INTEGER NOT NULL DEFAULT 1")
        if not _CONN.execute("SELECT 1 FROM product LIMIT 1").fetchone():
            now = _now()
            _CONN.executemany("INSERT INTO product (id, name, unit, price_usd, created_at) VALUES (?,?,?,?,?)",
                              [(uuid.uuid4().hex[:12], n, u, p, now) for n, u, p in SEED_PRODUCTS])
            _CONN.commit()
    return _CONN


def reset(path: str | None = None) -> None:
    """Rouvre la base (tests)."""
    global _CONN
    if path is not None:
        os.environ["KERNEL_DB_PATH"] = path
    _CONN = None


def _record(row: sqlite3.Row) -> WorkflowRecord:
    return WorkflowRecord(id=row["id"], workflow=Workflow.model_validate_json(row["definition"]),
                          created_at=row["created_at"], updated_at=row["updated_at"])


def save_workflow(wf: Workflow, wf_id: str | None = None) -> WorkflowRecord:
    with _LOCK:
        c, now = conn(), _now()
        if wf_id and c.execute("SELECT 1 FROM workflow WHERE id=?", (wf_id,)).fetchone():
            c.execute("UPDATE workflow SET name=?, definition=?, updated_at=? WHERE id=?",
                      (wf.name, wf.model_dump_json(), now, wf_id))
        else:
            wf_id = wf_id or uuid.uuid4().hex[:12]
            c.execute("INSERT INTO workflow VALUES (?,?,?,?,?)", (wf_id, wf.name, wf.model_dump_json(), now, now))
        c.commit()
        return _record(c.execute("SELECT * FROM workflow WHERE id=?", (wf_id,)).fetchone())


def get_workflow(wf_id: str) -> WorkflowRecord | None:
    row = conn().execute("SELECT * FROM workflow WHERE id=?", (wf_id,)).fetchone()
    return _record(row) if row else None


def list_workflows() -> list[WorkflowRecord]:
    return [_record(r) for r in conn().execute("SELECT * FROM workflow ORDER BY updated_at DESC")]


def delete_workflow(wf_id: str) -> bool:
    with _LOCK:
        cur = conn().execute("DELETE FROM workflow WHERE id=?", (wf_id,))
        conn().commit()
        return cur.rowcount > 0


def save_run(result: RunResult, workflow_id: str | None) -> None:
    with _LOCK:
        if workflow_id and not get_workflow(workflow_id):
            workflow_id = None
        conn().execute("INSERT INTO run VALUES (?,?,?,?,?,?)", (
            result.run_id, workflow_id, int(result.dry_run), result.status, result.model_dump_json(), _now()))
        conn().commit()


def get_run(run_id: str) -> RunResult | None:
    row = conn().execute("SELECT result FROM run WHERE id=?", (run_id,)).fetchone()
    return RunResult.model_validate_json(row["result"]) if row else None


def list_runs(workflow_id: str | None = None, limit: int = 20) -> list[dict]:
    q, args = "SELECT id, workflow_id, dry_run, status, started_at FROM run", []
    if workflow_id:
        q, args = q + " WHERE workflow_id=?", [workflow_id]
    rows = conn().execute(q + " ORDER BY started_at DESC LIMIT ?", (*args, limit))
    return [dict(r) | {"dry_run": bool(r["dry_run"])} for r in rows]


# --- ERP : clients, produits, ventes ------------------------------------------
class DuplicateEmail(Exception):
    pass


_CUSTOMER_STATS = """SELECT c.*, COUNT(s.id) AS purchases, COALESCE(SUM(s.total_usd), 0) AS total_spent_usd
  FROM customer c LEFT JOIN sale s ON s.customer_id = c.id"""


def _customer(row: sqlite3.Row) -> dict:
    return dict(row) | {"total_spent_usd": round(row["total_spent_usd"], 2)}


def create_customer(name: str, email: str, phone: str | None = None) -> dict:
    with _LOCK:
        c, cid = conn(), uuid.uuid4().hex[:12]
        try:
            c.execute("INSERT INTO customer VALUES (?,?,?,?,?)", (cid, name, email.strip().lower(), phone, _now()))
        except sqlite3.IntegrityError as exc:
            raise DuplicateEmail(email) from exc
        c.commit()
    return get_customer(cid)  # type: ignore[return-value]


def get_customer(customer_id: str) -> dict | None:
    row = conn().execute(_CUSTOMER_STATS + " WHERE c.id=? GROUP BY c.id", (customer_id,)).fetchone()
    return _customer(row) if row else None


def find_customer_by_email(email: str) -> dict | None:
    row = conn().execute(_CUSTOMER_STATS + " WHERE c.email=? GROUP BY c.id", (email.strip().lower(),)).fetchone()
    return _customer(row) if row else None


def list_customers() -> list[dict]:
    return [_customer(r) for r in conn().execute(_CUSTOMER_STATS + " GROUP BY c.id ORDER BY c.created_at DESC")]


def list_products() -> list[dict]:
    """Catalogue actif uniquement (les produits retirés restent pour l'historique des ventes)."""
    return [dict(r) for r in conn().execute("SELECT * FROM product WHERE active=1 ORDER BY rowid")]


def sync_products(products: list[dict]) -> None:
    """Aligne le catalogue sur une spec : upsert par nom, désactivation des absents (pas de DELETE)."""
    with _LOCK:
        c, now = conn(), _now()
        names = [p["name"] for p in products]
        for p in products:
            row = c.execute("SELECT id FROM product WHERE name=? ORDER BY active DESC, rowid LIMIT 1",
                            (p["name"],)).fetchone()
            if row:
                c.execute("UPDATE product SET unit=?, price_usd=?, active=1 WHERE id=?",
                          (p.get("unit"), p["price_usd"], row["id"]))
            else:
                c.execute("INSERT INTO product (id, name, unit, price_usd, created_at) VALUES (?,?,?,?,?)",
                          (uuid.uuid4().hex[:12], p["name"], p.get("unit"), p["price_usd"], now))
        c.execute(f"UPDATE product SET active=0 WHERE name NOT IN ({','.join('?' * len(names))})", names)
        c.commit()


def get_product(product_id: str) -> dict | None:
    row = conn().execute("SELECT * FROM product WHERE id=?", (product_id,)).fetchone()
    return dict(row) if row else None


_SALE_SELECT = """SELECT s.*, c.name AS customer_name, c.email AS customer_email, c.phone AS customer_phone
  FROM sale s JOIN customer c ON c.id = s.customer_id"""


def _sale(row: sqlite3.Row) -> dict:
    return dict(row) | {"items": json.loads(row["items"]), "run_ids": json.loads(row["run_ids"])}


def create_sale(customer_id: str, items: list[dict], total_usd: float, total_cdf: float, rate: float) -> dict:
    """Enregistre une vente ; numéro de facture séquentiel par année (FAC-2026-0001)."""
    with _LOCK:
        c, now, sid = conn(), _now(), uuid.uuid4().hex[:12]
        prefix = f"FAC-{now[:4]}-"
        last = c.execute("SELECT invoice_number FROM sale WHERE invoice_number LIKE ? "
                         "ORDER BY invoice_number DESC LIMIT 1", (prefix + "%",)).fetchone()
        seq = int(last["invoice_number"].rsplit("-", 1)[1]) + 1 if last else 1
        c.execute("INSERT INTO sale VALUES (?,?,?,?,?,?,?,?,?,?)", (
            sid, f"{prefix}{seq:04d}", customer_id, json.dumps(items), total_usd, total_cdf, rate, now,
            "not_sent", "[]"))
        c.commit()
    return get_sale(sid)  # type: ignore[return-value]


def get_sale(sale_id: str) -> dict | None:
    row = conn().execute(_SALE_SELECT + " WHERE s.id=?", (sale_id,)).fetchone()
    return _sale(row) if row else None


def list_sales() -> list[dict]:
    return [_sale(r) for r in conn().execute(_SALE_SELECT + " ORDER BY s.created_at DESC, s.invoice_number DESC")]


def update_sale_invoice(sale_id: str, status: str, run_ids: list[str]) -> None:
    with _LOCK:
        conn().execute("UPDATE sale SET invoice_status=?, run_ids=? WHERE id=?", (status, json.dumps(run_ids), sale_id))
        conn().commit()


# --- Générateur d'applications : builds et état déployé ---------------------------
def _build(row: sqlite3.Row) -> dict:
    return dict(row) | {"spec": json.loads(row["spec"]), "max_lines": 120}


def save_app_build(app: str, prompt: str, spec: dict, diff: str, lines_changed: int, status: str,
                   source: str | None, error: str | None) -> dict:
    with _LOCK:
        c, bid = conn(), uuid.uuid4().hex[:12]
        c.execute("INSERT INTO app_build VALUES (?,?,?,?,?,?,?,?,?,?)", (
            bid, app, prompt, json.dumps(spec, ensure_ascii=False), diff, lines_changed, status, source, error,
            _now()))
        c.commit()
        # Relecture sous verrou : les builds sont enregistrées depuis plusieurs threads.
        return get_app_build(bid)  # type: ignore[return-value]


def get_app_build(build_id: str) -> dict | None:
    row = conn().execute("SELECT * FROM app_build WHERE id=?", (build_id,)).fetchone()
    return _build(row) if row else None


def list_app_builds(limit: int = 20) -> list[dict]:
    return [_build(r) for r in conn().execute(
        "SELECT * FROM app_build ORDER BY created_at DESC, rowid DESC LIMIT ?", (limit,))]


def set_deployment(prompt: str, build_ids: dict[str, str]) -> None:
    """État déployé : prompt + build retenue par app."""
    with _LOCK:
        conn().execute("INSERT OR REPLACE INTO app_state VALUES ('deployment', ?)",
                       (json.dumps({"prompt": prompt, "builds": build_ids}, ensure_ascii=False),))
        conn().commit()


def get_deployment() -> dict | None:
    """{prompt, apps: {app: spec}} ou None si rien n'est déployé."""
    row = conn().execute("SELECT value FROM app_state WHERE key='deployment'").fetchone()
    if not row:
        return None
    dep = json.loads(row["value"])
    apps = {a: b["spec"] for a, bid in dep["builds"].items() if (b := get_app_build(bid))}
    return {"prompt": dep["prompt"], "apps": apps}


def deployed_spec(app: str) -> dict | None:
    dep = get_deployment()
    return dep["apps"].get(app) if dep else None


def clear_deployment() -> None:
    with _LOCK:
        conn().execute("DELETE FROM app_state WHERE key='deployment'")
        conn().commit()
