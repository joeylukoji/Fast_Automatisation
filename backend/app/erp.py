"""API ERP (/api/erp) : clients, produits, ventes et facturation automatique par workflow."""
from __future__ import annotations

import os

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from . import engine, store
from .nodes.erp import render_invoice
from .schemas import RunResult, Workflow, WorkflowRecord

router = APIRouter(prefix="/api/erp", tags=["erp"])

DEFAULT_WORKFLOW = Workflow.model_validate({
    "name": "Facture automatique après vente",
    "nodes": [
        {"id": "vente", "type": "trigger_erp_sale", "params": {}},
        {"id": "facture", "type": "invoice_render", "params": {"sale_id": "{{vente.sale_id}}"}},
        {"id": "email", "type": "gmail_send", "params": {
            "to": "{{vente.customer.email}}", "subject": "{{facture.subject}}",
            "body": "{{facture.text}}", "html": "{{facture.html}}"}},
    ],
    "edges": [{"source": "vente", "target": "facture"}, {"source": "facture", "target": "email"}],
})


def _rate() -> float:
    return float(os.getenv("KERNEL_ERP_USD_CDF", "2300"))


class CustomerIn(BaseModel):
    name: str
    email: str
    phone: str | None = None


class SaleItemIn(BaseModel):
    product_id: str
    qty: int = Field(gt=0)


class SaleIn(BaseModel):
    customer_id: str
    items: list[SaleItemIn]
    send_invoice: bool = True


@router.get("/customers")
def list_customers() -> list[dict]:
    return store.list_customers()


@router.post("/customers", status_code=201)
def create_customer(body: CustomerIn) -> dict:
    if not body.name.strip() or "@" not in body.email:
        raise HTTPException(400, "Nom et e-mail valides requis.")
    try:
        return store.create_customer(body.name.strip(), body.email, body.phone)
    except store.DuplicateEmail as exc:
        raise HTTPException(409, "Un client avec cet e-mail existe déjà.") from exc


@router.get("/products")
def list_products() -> list[dict]:
    return store.list_products()


@router.get("/sales")
def list_sales() -> list[dict]:
    return store.list_sales()


def _erp_workflows() -> list[WorkflowRecord]:
    return [r for r in store.list_workflows() if any(n.type == "trigger_erp_sale" for n in r.workflow.nodes)]


def _payload(sale: dict) -> dict:
    return {
        "sale_id": sale["id"], "invoice_number": sale["invoice_number"], "date": sale["created_at"][:10],
        "customer": {"id": sale["customer_id"], "name": sale["customer_name"], "email": sale["customer_email"],
                     "phone": sale["customer_phone"]},
        "items": [{k: i[k] for k in ("name", "qty", "unit_price_usd", "line_total_usd")} for i in sale["items"]],
        "total_usd": sale["total_usd"], "total_cdf": sale["total_cdf"], "rate": sale["rate"],
    }


@router.post("/sales", status_code=201)
def create_sale(body: SaleIn) -> dict:
    if store.get_customer(body.customer_id) is None:
        raise HTTPException(404, "Client introuvable.")
    if not body.items:
        raise HTTPException(400, "La vente doit contenir au moins un article.")
    items = []
    for it in body.items:
        if (p := store.get_product(it.product_id)) is None or not p["active"]:
            raise HTTPException(404, f"Produit introuvable : {it.product_id}")
        items.append({"product_id": p["id"], "name": p["name"], "qty": it.qty, "unit_price_usd": p["price_usd"],
                      "line_total_usd": round(p["price_usd"] * it.qty, 2)})
    total_usd, rate = round(sum(i["line_total_usd"] for i in items), 2), _rate()
    total_cdf = float(int(total_usd * rate / 100 + 0.5) * 100)  # arrondi à la centaine (demi vers le haut)
    sale = store.create_sale(body.customer_id, items, total_usd, total_cdf, rate)

    runs: list[RunResult] = []
    if body.send_invoice:
        # L'encaissement par la caissière vaut validation explicite : exécution réelle.
        targets = [(r.workflow, r.id) for r in _erp_workflows()] or [(DEFAULT_WORKFLOW, None)]
        payload = _payload(sale)
        for wf, wf_id in targets:
            result = engine.run(wf, dry_run=False, trigger_payload=payload)
            store.save_run(result, wf_id)
            runs.append(result)
        status = "sent" if all(r.status == "success" for r in runs) else "failed"
        store.update_sale_invoice(sale["id"], status, [r.run_id for r in runs])
        sale = store.get_sale(sale["id"])
    return {"sale": sale, "runs": [r.model_dump() for r in runs]}


@router.get("/sales/{sale_id}/invoice", response_class=HTMLResponse)
def get_invoice(sale_id: str) -> HTMLResponse:
    if (sale := store.get_sale(sale_id)) is None:
        raise HTTPException(404, "Vente introuvable.")
    return HTMLResponse(render_invoice(sale)["html"])


@router.get("/automation")
def automation() -> dict:
    recs = _erp_workflows()
    return {"workflow_id": recs[0].id, "workflow": recs[0].workflow} if recs else \
        {"workflow_id": None, "workflow": DEFAULT_WORKFLOW}


@router.post("/automation/install", response_model=WorkflowRecord, status_code=201)
def install_automation() -> WorkflowRecord:
    return store.save_workflow(DEFAULT_WORKFLOW)
