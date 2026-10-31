"""API du générateur d'applications (/api/apps)."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .. import store
from . import builder

router = APIRouter(prefix="/api/apps", tags=["apps"])


class BuildIn(BaseModel):
    prompt: str


@router.get("")
def get_apps() -> dict:
    dep = store.get_deployment()
    return {"deployed": True, **dep} if dep else {"deployed": False, "prompt": None, "apps": {}}


@router.post("/build")
def build(body: BuildIn) -> dict:
    if not body.prompt.strip():
        raise HTTPException(400, "La description est vide.")
    prompt = body.prompt.strip()
    return {"deployed": True, "prompt": prompt, "builds": builder.build_all(prompt)}


@router.get("/builds")
def list_builds(limit: int = 20) -> list[dict]:
    return store.list_app_builds(min(max(limit, 1), 100))


@router.post("/reset")
def reset() -> dict:
    builder.reset()
    return {"deployed": False}
