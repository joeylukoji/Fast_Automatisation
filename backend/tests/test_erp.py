from fastapi.testclient import TestClient

from app.connectors import gmail
from app.main import app

client = TestClient(app)


def _customer(email="marie@example.cd"):
    return client.post("/api/erp/customers", json={"name": "Marie K.", "email": email, "phone": "+243 81"}).json()


def _products():
    return {p["name"]: p for p in client.get("/api/erp/products").json()}


def _sale(cust, send=True):
    p = _products()
    items = [{"product_id": p["Casier Primus 72cl"]["id"], "qty": 2},
             {"product_id": p["Pack d'eau 1,5 L x6"]["id"], "qty": 1}]
    return client.post("/api/erp/sales", json={"customer_id": cust["id"], "items": items, "send_invoice": send}).json()


def test_customer_create_and_duplicate():
    c = _customer()
    assert c["purchases"] == 0 and c["total_spent_usd"] == 0
    assert client.post("/api/erp/customers", json={"name": "X", "email": "marie@example.cd"}).status_code == 409
    assert [x["id"] for x in client.get("/api/erp/customers").json()] == [c["id"]]


def test_sale_totals_and_invoice():
    assert len(_products()) == 6
    body = _sale(_customer(), send=False)
    sale = body["sale"]
    assert body["runs"] == [] and sale["invoice_status"] == "not_sent"
    assert sale["invoice_number"].startswith("FAC-") and sale["invoice_number"].endswith("-0001")
    assert sale["total_usd"] == 39.5 and sale["rate"] == 2300
    assert sale["total_cdf"] == 90900  # 39.5 * 2300 = 90 850 → centaine
    assert sale["items"][0]["line_total_usd"] == 36 and sale["customer_email"] == "marie@example.cd"
    html = client.get(f"/api/erp/sales/{sale['id']}/invoice")
    assert html.headers["content-type"].startswith("text/html")
    assert "Kernel Market — Kinshasa, RDC" in html.text and sale["invoice_number"] in html.text
    listed = client.get("/api/erp/customers").json()[0]
    assert listed["purchases"] == 1 and listed["total_spent_usd"] == 39.5


def test_erp_nodes_in_catalogue():
    types = {n["type"]: n for n in client.get("/api/nodes").json()}
    assert {"trigger_erp_sale", "erp_customer_lookup", "invoice_render"} <= types.keys()
    assert types["trigger_erp_sale"]["is_trigger"]
    assert "html" in types["gmail_send"]["params_schema"]["properties"]


def test_sale_sends_invoice_with_gmail(monkeypatch):
    sent = []
    monkeypatch.setattr(gmail, "send_email", lambda to, subject, body, html=None: sent.append(
        (to, subject, body, html)) or {"sent_to": to})
    body = _sale(_customer())
    assert body["sale"]["invoice_status"] == "sent" and len(body["runs"]) == 1
    assert body["sale"]["run_ids"] == [body["runs"][0]["run_id"]]
    to, subject, text, html = sent[0]
    assert to == "marie@example.cd" and body["sale"]["invoice_number"] in subject
    assert "Merci" in text and "<table" in html


def test_sale_without_gmail_fails_but_is_kept(monkeypatch):
    monkeypatch.delenv("KERNEL_GMAIL_USER", raising=False)
    monkeypatch.delenv("KERNEL_GMAIL_APP_PASSWORD", raising=False)
    resp = client.post("/api/erp/automation/install")
    assert resp.status_code == 201
    assert client.get("/api/erp/automation").json()["workflow_id"] == resp.json()["id"]
    body = _sale(_customer())
    assert body["sale"]["invoice_status"] == "failed" and body["runs"][0]["status"] == "error"
    assert len(client.get("/api/erp/sales").json()) == 1
    assert client.get("/api/runs", params={"workflow_id": resp.json()["id"]}).json()
