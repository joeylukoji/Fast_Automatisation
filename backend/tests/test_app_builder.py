"""Générateur d'applications : fallback déterministe, limites de diff, CSS, catalogue, reset."""
import json

from fastapi.testclient import TestClient

from app import store
from app.apps import builder
from app.main import app

client = TestClient(app)
PROMPT = "Pharmacie à Lubumbashi appelée Pharma Plus"


PROFILE = {"shop": {"name": "Pharma Plus", "city": "Lubumbashi, RDC", "slogan": "Votre santé"},
           "accent": "#2E7D32",
           "products": [{"name": "Paracétamol", "unit": "boîte", "price_usd": 2.5},
                        {"name": "Sirop contre la toux", "unit": "flacon", "price_usd": 4.5}],
           "customer_fields": [{"key": "age", "label": "Âge"}],
           "labels": {"checkout": "Valider l'ordonnance", "inconnu": "ignoré"},
           "invoice_note": "Respectez la posologie."}


def _gemma(monkeypatch, *replies):
    """Remplace Gemma : chaque appel renvoie la réponse suivante (la dernière se répète)."""
    monkeypatch.setenv("KERNEL_LLM_BASE_URL", "http://gemma.invalid/v1")
    monkeypatch.setenv("KERNEL_LLM_MODEL", "gemma-test")
    calls = []

    def fake(messages):
        calls.append(messages)
        return json.dumps(replies[min(len(calls), len(replies)) - 1], ensure_ascii=False)
    monkeypatch.setattr(builder, "ask_gemma", fake)
    return calls


def test_initialement_rien_de_deploye():
    assert client.get("/api/apps").json() == {"deployed": False, "prompt": None, "apps": {}}


def test_build_fallback_deterministe():
    r = client.post("/api/apps/build", json={"prompt": PROMPT}).json()
    assert r["deployed"] is True and len(r["builds"]) == 4
    assert {b["app"] for b in r["builds"]} == set(builder.APPS)
    for b in r["builds"]:
        assert b["status"] == "applied" and b["source"] == "local"
        assert 0 < b["lines_changed"] <= 120 and b["max_lines"] == 120 and b["error"] is None
    apps = client.get("/api/apps").json()
    assert apps["deployed"] and apps["apps"]["caisse"]["shop"]["name"] == "Pharma Plus"
    assert apps["apps"]["ventes"]["invoice"]["header"] == "Pharma Plus — Lubumbashi, RDC"
    assert len(client.get("/api/apps/builds").json()) == 4


def test_gemma_indisponible_bascule_local(monkeypatch):
    monkeypatch.setenv("KERNEL_LLM_BASE_URL", "http://127.0.0.1:9/v1")
    monkeypatch.setenv("KERNEL_LLM_MODEL", "gemma-test")
    builds = builder.build_all(PROMPT)
    assert all(b["status"] == "applied" and b["source"] == "local" for b in builds)


def test_gemma_un_seul_appel_pour_les_4_apps(monkeypatch):
    calls = _gemma(monkeypatch, PROFILE)
    builds = {b["app"]: b for b in builder.build_all(PROMPT)}
    assert len(calls) == 1 and calls[0][0]["role"] == "user"  # pas de message system (500 chez Gemini)
    assert all(b["status"] == "applied" and b["source"] == "gemma" and b["lines_changed"] <= 120
               for b in builds.values())
    caisse = builds["caisse"]["spec"]
    assert caisse["shop"]["name"] == "Pharma Plus" and caisse["theme"]["accent"] == "#2E7D32"
    assert caisse["labels"]["checkout"] == "Valider l'ordonnance" and "inconnu" not in caisse["labels"]
    assert builds["clients"]["spec"]["customer_fields"] == [{"key": "age", "label": "Âge"}]
    assert builds["ventes"]["spec"]["invoice"]["header"] == "Pharma Plus — Lubumbashi, RDC"
    assert {p["name"] for p in client.get("/api/erp/products").json()} == {"Paracétamol", "Sirop contre la toux"}


def test_profil_invalide_nouvelle_tentative_puis_rejet(monkeypatch):
    bad = PROFILE | {"products": [{"name": "Gratuit", "unit": "u", "price_usd": 0}]}
    calls = _gemma(monkeypatch, bad)
    builds = {b["app"]: b for b in builder.build_all(PROMPT)}
    assert len(calls) == 2 and "price_usd" in calls[1][-1]["content"]
    assert builds["caisse"]["status"] == "rejected" and builds["caisse"]["spec"] == builder.base_spec("caisse")
    assert builds["clients"]["status"] == "applied"  # les autres apps gardent le profil


def test_profil_corrige_au_second_essai(monkeypatch):
    calls = _gemma(monkeypatch, PROFILE | {"accent": "vert"}, PROFILE)
    builds = builder.build_all(PROMPT)
    assert len(calls) == 2 and all(b["status"] == "applied" for b in builds)


def test_reponse_non_json_rejetee(monkeypatch):
    monkeypatch.setenv("KERNEL_LLM_BASE_URL", "http://gemma.invalid/v1")
    monkeypatch.setenv("KERNEL_LLM_MODEL", "gemma-test")
    monkeypatch.setattr(builder, "ask_gemma", lambda messages: "désolé")
    builds = builder.build_all(PROMPT)
    assert all(b["status"] == "rejected" and b["source"] == "gemma" and b["error"] for b in builds)


def test_rejet_css_interdit():
    base = builder.base_spec("caisse")
    for bad in (".app-root { background: url(http://x/y.png); }", "@import 'x.css';",
                ".app-root{}</style><script>", "body { color: red; }"):
        assert builder.validate(base, base | {"css": [bad]})
    assert builder.validate(base, base | {"theme": {"accent": "red", "background": "#FFFFFF"}})
    assert builder.validate(base, base | {"extra": 1})
    assert builder.validate(base, base) == []


def test_profil_ne_peut_pas_injecter_de_cles(monkeypatch):
    _gemma(monkeypatch, PROFILE | {"css": [".app-root { background: url(x) }"], "app": "pirate", "extra": 1})
    caisse = next(b for b in builder.build_all(PROMPT) if b["app"] == "caisse")
    assert caisse["status"] == "applied" and caisse["spec"]["app"] == "caisse"
    assert caisse["spec"]["css"] == builder.base_spec("caisse")["css"] and "extra" not in caisse["spec"]


def test_sync_produits_et_ventes_passees(monkeypatch):
    p = {x["name"]: x for x in client.get("/api/erp/products").json()}
    c = client.post("/api/erp/customers", json={"name": "Awa", "email": "awa@example.cd"}).json()
    sale = client.post("/api/erp/sales", json={"customer_id": c["id"], "send_invoice": False, "items": [
        {"product_id": p["Casier Primus 72cl"]["id"], "qty": 1}]}).json()["sale"]
    store.sync_products([{"name": "Paracétamol 500 mg (boîte)", "unit": "boîte", "price_usd": 2.5},
                         {"name": "Sac de riz 25 kg", "unit": "sac", "price_usd": 30}])
    now = {x["name"]: x for x in client.get("/api/erp/products").json()}
    assert set(now) == {"Paracétamol 500 mg (boîte)", "Sac de riz 25 kg"}
    assert now["Sac de riz 25 kg"]["id"] == p["Sac de riz 25 kg"]["id"] and now["Sac de riz 25 kg"]["price_usd"] == 30
    assert store.get_sale(sale["id"])["items"][0]["name"] == "Casier Primus 72cl"
    r = client.post("/api/erp/sales", json={"customer_id": c["id"], "items": [
        {"product_id": p["Casier Primus 72cl"]["id"], "qty": 1}]})
    assert r.status_code == 404  # produit retiré du catalogue


def test_facture_utilise_spec_ventes():
    client.post("/api/apps/build", json={"prompt": PROMPT})
    p = client.get("/api/erp/products").json()[0]
    c = client.post("/api/erp/customers", json={"name": "Awa", "email": "awa@example.cd"}).json()
    sale = client.post("/api/erp/sales", json={"customer_id": c["id"], "send_invoice": False,
                                               "items": [{"product_id": p["id"], "qty": 1}]}).json()["sale"]
    html = client.get(f"/api/erp/sales/{sale['id']}/invoice").text
    assert "Pharma Plus — Lubumbashi, RDC" in html and "Merci pour votre achat chez Pharma Plus" in html


def test_reset():
    client.post("/api/apps/build", json={"prompt": PROMPT})
    store.sync_products([{"name": "Seul produit", "unit": "u", "price_usd": 1}])
    assert client.post("/api/apps/reset").json() == {"deployed": False}
    assert client.get("/api/apps").json()["deployed"] is False
    assert len(client.get("/api/erp/products").json()) == 6
    assert len(client.get("/api/apps/builds").json()) == 4  # l'historique est conservé
