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
"""


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
