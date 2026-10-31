"""Blocs ERP réutilisables : déclencheur « nouvelle vente », fiche client CRM, rendu de facture."""
from __future__ import annotations

from html import escape

from .. import store
from .builtin import _obj, _str
from .registry import NodeSpec, RunContext, register

SHOP = "Kernel Market — Kinshasa, RDC"
DEFAULT_INVOICE = {"name": "Kernel Market", "header": SHOP, "note": "Merci pour votre achat chez Kernel Market !",
                   "footer": ""}


def _branding() -> dict:
    """shop/invoice de la spec « ventes » déployée (générateur d'applications), sinon valeurs par défaut."""
    spec = store.deployed_spec("ventes") or {}
    shop, inv = spec.get("shop") or {}, spec.get("invoice") or {}
    return {"name": shop.get("name") or DEFAULT_INVOICE["name"],
            "header": inv.get("header") or DEFAULT_INVOICE["header"],
            "note": inv.get("note") or DEFAULT_INVOICE["note"], "footer": inv.get("footer") or ""}


def _usd(v: float) -> str:
    return f"{v:,.2f} $".replace(",", " ")


def _cdf(v: float) -> str:
    return f"{v:,.0f} FC".replace(",", " ")


def render_invoice(sale: dict) -> dict:
    """Facture HTML autonome (styles inline, compatible clients mail) + version texte."""
    num, date = sale["invoice_number"], sale["created_at"][:10]
    brand = _branding()
    footer = f'<div style="margin-top:6px;font-size:12px;">{escape(brand["footer"])}</div>' if brand["footer"] else ""
    name, email = sale["customer_name"], sale["customer_email"]
    td = "padding:8px 10px;border-bottom:1px solid #e5e7eb;font-size:14px;color:#111827;"
    rows = "".join(
        f'<tr><td style="{td}">{escape(i["name"])}</td><td style="{td}text-align:center;">{i["qty"]}</td>'
        f'<td style="{td}text-align:right;">{_usd(i["unit_price_usd"])}</td>'
        f'<td style="{td}text-align:right;">{_usd(i["line_total_usd"])}</td></tr>'
        for i in sale["items"]
    )
    phone = f"<div>{escape(sale['customer_phone'])}</div>" if sale.get("customer_phone") else ""
    total_usd, total_cdf, rate = _usd(sale["total_usd"]), _cdf(sale["total_cdf"]), f"{sale['rate']:g}"
    th = "padding:8px 10px;background:#111827;color:#ffffff;font-size:12px;text-transform:uppercase;"
    html = f"""<!doctype html>
<html lang="fr"><head><meta charset="utf-8"><title>Facture {escape(num)}</title></head>
<body style="margin:0;padding:24px;background:#f3f4f6;font-family:Arial,Helvetica,sans-serif;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:640px;margin:0 auto;background:#ffffff;border-radius:8px;">
<tr><td style="padding:24px 28px;border-bottom:3px solid #111827;">
  <div style="font-size:20px;font-weight:bold;color:#111827;">{escape(brand["header"])}</div>
  <div style="font-size:13px;color:#6b7280;margin-top:4px;">Facture n° <b>{escape(num)}</b> — {escape(date)}</div>
</td></tr>
<tr><td style="padding:20px 28px;font-size:14px;color:#111827;">
  <div style="color:#6b7280;font-size:12px;text-transform:uppercase;">Client</div>
  <div style="font-weight:bold;">{escape(name)}</div>
  <div>{escape(email)}</div>{phone}
</td></tr>
<tr><td style="padding:0 28px;">
  <table width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;">
    <tr><th style="{th}text-align:left;">Article</th><th style="{th}">Qté</th>
        <th style="{th}text-align:right;">Prix unitaire</th><th style="{th}text-align:right;">Total</th></tr>
    {rows}
  </table>
</td></tr>
<tr><td style="padding:16px 28px;text-align:right;font-size:14px;color:#111827;">
  <div style="font-size:18px;font-weight:bold;">Total : {total_usd}</div>
  <div style="color:#6b7280;">Soit {total_cdf} (taux 1 $ = {rate} FC)</div>
</td></tr>
<tr><td style="padding:20px 28px;border-top:1px solid #e5e7eb;font-size:13px;color:#6b7280;text-align:center;">
  {escape(brand["note"])}{footer}
</td></tr>
</table></body></html>"""
    lines = [f"{i['name']} x{i['qty']} @ {_usd(i['unit_price_usd'])} = {_usd(i['line_total_usd'])}"
             for i in sale["items"]]
    text = "\n".join([
        brand["header"], f"Facture n° {num} — {date}", f"Client : {name} <{email}>", "", *lines, "",
        f"Total : {_usd(sale['total_usd'])} (soit {_cdf(sale['total_cdf'])}, taux 1 $ = {sale['rate']:g} FC)",
        "", brand["note"], *([brand["footer"]] if brand["footer"] else []),
    ])
    return {"invoice_number": num, "subject": f"Votre facture {num} — {brand['name']}", "html": html,
            "text": text, "total_usd": sale["total_usd"], "total_cdf": sale["total_cdf"], "customer_email": email}


# --- Déclencheur : nouvelle vente -------------------------------------------
def _run_trigger(params: dict, inputs: dict, ctx: RunContext) -> dict:
    return dict(ctx.trigger_payload)


register(
    NodeSpec(
        type="trigger_erp_sale",
        label="Nouvelle vente (ERP)",
        description=("Démarre le workflow à chaque vente enregistrée en caisse. Sortie : {sale_id, invoice_number, date, "
                     "customer: {id, name, email, phone}, items: [{name, qty, unit_price_usd, line_total_usd}], "
                     "total_usd, total_cdf, rate} ; ex. {{vente.total_usd}}, {{vente.customer.email}}."),
        params_schema=_obj({}),
        run=_run_trigger,
        is_trigger=True,
    )
)


# --- Fiche client CRM -------------------------------------------------------
def _run_lookup(params: dict, inputs: dict, ctx: RunContext) -> dict:
    c = store.find_customer_by_email(str(params.get("email", "")))
    if not c:
        return {"found": False, "id": None, "name": None, "email": params.get("email"), "phone": None,
                "purchases": 0, "total_spent_usd": 0}
    return {"found": True, **{k: c[k] for k in ("id", "name", "email", "phone", "purchases", "total_spent_usd")}}


register(
    NodeSpec(
        type="erp_customer_lookup",
        label="ERP : fiche client",
        description="Cherche un client par e-mail : {found, id, name, email, phone, purchases, total_spent_usd}.",
        params_schema=_obj({"email": _str("E-mail du client")}, ["email"]),
        run=_run_lookup,
    )
)


# --- Facture ----------------------------------------------------------------
def _run_invoice(params: dict, inputs: dict, ctx: RunContext) -> dict:
    sale = store.get_sale(str(params.get("sale_id", "")))
    if sale is None:
        raise ValueError(f"Vente introuvable : {params.get('sale_id')!r}")
    return render_invoice(sale)


register(
    NodeSpec(
        type="invoice_render",
        label="ERP : générer la facture",
        description="Génère la facture d'une vente : {invoice_number, subject, html, text, total_usd, total_cdf, customer_email}.",
        params_schema=_obj({"sale_id": _str("ID de la vente")}, ["sale_id"]),
        run=_run_invoice,
    )
)
