"""Personnalisation des specs d'applications par Gemma, sous contrôle strict du backend.

Gemma ne touche jamais au code : il renvoie une spec complète (mêmes clés que la base), validée
puis comparée à la base ; au-delà de MAX_LINES lignes de diff, la proposition est refusée.
"""
from __future__ import annotations

import copy
import difflib
import json
import re
from pathlib import Path

from .. import store
from ..ai import llm
from ..ai.generator import _extract_json
from ..ai.llm import LLMUnavailable

APPS = ("caisse", "clients", "ventes", "automatisation")
MAX_LINES = 120
SPECS_DIR = Path(__file__).parent / "specs"
_COLOR = re.compile(r"^#[0-9A-Fa-f]{6}$")
_KEY = re.compile(r"^[a-z_]+$")
_CSS_FORBIDDEN = ("@import", "url(", "<", "expression", "javascript:")


def base_spec(app: str) -> dict:
    return json.loads((SPECS_DIR / f"{app}.json").read_text(encoding="utf-8"))


def _dump(spec: dict) -> list[str]:
    return json.dumps(spec, indent=2, ensure_ascii=False).splitlines()


def diff(base: dict, spec: dict) -> tuple[str, int]:
    """(diff unifié base → proposé, nombre de lignes +/- hors en-têtes)."""
    lines = list(difflib.unified_diff(_dump(base), _dump(spec), "base", "proposé", lineterm=""))
    n = sum(1 for ln in lines if ln[:1] in "+-" and not ln.startswith(("+++", "---")))
    return "\n".join(lines), n


def _is_str_dict(v: object) -> bool:
    return isinstance(v, dict) and all(isinstance(x, str) for x in v.values())


def _valid_product(p: object) -> bool:
    price = p.get("price_usd") if isinstance(p, dict) else None
    return (isinstance(p, dict) and isinstance(p.get("name"), str) and bool(p["name"].strip())
            and isinstance(p.get("unit", ""), str)
            and isinstance(price, (int, float)) and not isinstance(price, bool) and price > 0)


def validate(base: dict, spec: object) -> list[str]:
    """Erreurs de la spec proposée (liste vide = valide)."""
    if not isinstance(spec, dict):
        return ["La spec doit être un objet JSON."]
    errors: list[str] = []
    if set(spec) != set(base):
        extra, missing = sorted(set(spec) - set(base)), sorted(set(base) - set(spec))
        errors.append(f"Clés de premier niveau modifiées (ajoutées : {extra}, manquantes : {missing}).")
    if spec.get("app") != base["app"]:
        errors.append(f"Le champ app doit rester {base['app']!r}.")
    if "title" in spec and not (isinstance(spec["title"], str) and spec["title"].strip()):
        errors.append("title doit être un texte non vide.")
    for key in ("shop", "labels", "invoice", "theme"):
        if key in spec and not _is_str_dict(spec[key]):
            errors.append(f"{key} doit être un objet de textes.")
    if _is_str_dict(spec.get("theme")):
        errors += [f"theme.{k} : couleur #RRGGBB attendue." for k, v in spec["theme"].items() if not _COLOR.match(v)]
    if "products" in spec:
        prods = spec["products"]
        if not isinstance(prods, list) or not 1 <= len(prods) <= 12:
            errors.append("products : liste de 1 à 12 produits attendue.")
        else:
            errors += [f"products[{i}] : name, unit (texte) et price_usd > 0 requis."
                       for i, p in enumerate(prods) if not _valid_product(p)]
    if "customer_fields" in spec:
        fields = spec["customer_fields"]
        if not isinstance(fields, list) or len(fields) > 6:
            errors.append("customer_fields : liste de 6 champs maximum.")
        else:
            errors += [f"customer_fields[{i}] : key en [a-z_]+ et label texte requis." for i, f in enumerate(fields)
                       if not (isinstance(f, dict) and isinstance(f.get("key"), str) and _KEY.match(f["key"])
                               and isinstance(f.get("label"), str))]
    if "css" in spec:
        css = spec["css"]
        if not isinstance(css, list) or len(css) > 40 or not all(isinstance(x, str) for x in css):
            errors.append("css : liste de 40 lignes (textes) maximum.")
        else:
            for i, line in enumerate(css):
                if not line.strip().startswith(".app-root"):
                    errors.append(f"css[{i}] : chaque ligne doit commencer par .app-root.")
                if bad := [t for t in _CSS_FORBIDDEN if t in line.lower()]:
                    errors.append(f"css[{i}] : contenu interdit {bad}.")
    return errors


# Un seul appel à Gemma produit un petit profil métier, appliqué ensuite aux 4 specs : demander
# chaque spec complète prenait plus de 2 minutes par app (long raisonnement sur un gros JSON).
_PROFILE_FORMAT = (
    '{"shop":{"name":"","city":"Ville, RDC","slogan":""},"accent":"#RRGGBB",'
    '"products":[{"name":"","unit":"","price_usd":0}],'
    '"customer_fields":[{"key":"snake_case","label":""}],'
    '"labels":{"checkout":"","new_sale":"","send_invoice":"","new_customer":"","add_customer":""},'
    '"invoice_note":""}'
)


def _profile_prompt(prompt: str) -> str:
    # Pas de message « system » : Gemma via l'API Gemini répond 500.
    return (
        "Réponds DIRECTEMENT par un JSON, sans réflexion, sans texte autour. Tu adaptes les applications de "
        "gestion (caisse, clients, ventes) d'un commerce en RDC au business décrit. Format exact :\n"
        f"{_PROFILE_FORMAT}\n"
        "5 à 8 produits pertinents avec des prix réalistes en USD pour la RDC (12 max, price_usd > 0), 0 à 3 "
        "customer_fields (key en [a-z_]+, sans nom/email/téléphone, déjà présents), accent en #RRGGBB, "
        "textes courts en français.\n\nBusiness : " + prompt
    )


def ask_gemma(messages: list[dict]) -> str:
    """Appel direct à Gemma : pas de bascule vers le générateur local (qui renvoie un workflow)."""
    # Sans response_format : Gemma via l'API Gemini le rejette, ce qui coûterait un appel de plus.
    out = llm._remote(messages, json_mode=False)
    llm.LAST_SOURCE.set("gemma")
    return out


def apply_profile(base: dict, profile: dict) -> dict:
    """Spec de l'app = base + détails du profil (seules les clés déjà présentes sont touchées)."""
    spec = copy.deepcopy(base)
    shop = profile.get("shop") if isinstance(profile.get("shop"), dict) else {}
    if isinstance(spec.get("shop"), dict):
        spec["shop"] |= {k: v for k, v in shop.items() if k in spec["shop"]}
    if isinstance(spec.get("theme"), dict) and "accent" in profile:
        spec["theme"]["accent"] = profile["accent"]
    if "products" in spec and "products" in profile:
        spec["products"] = profile["products"]
    if "customer_fields" in spec and "customer_fields" in profile:
        spec["customer_fields"] = profile["customer_fields"]
    labels = profile.get("labels") if isinstance(profile.get("labels"), dict) else {}
    if isinstance(spec.get("labels"), dict):
        spec["labels"] |= {k: v for k, v in labels.items() if k in spec["labels"] and v}
    if isinstance(spec.get("invoice"), dict):
        name, city = shop.get("name"), shop.get("city")
        if name:
            spec["invoice"]["header"] = f"{name} — {city}" if city else name
        if profile.get("invoice_note"):
            spec["invoice"]["note"] = profile["invoice_note"]
    return spec


# --- Personnalisation déterministe (hors ligne) -------------------------------
_CITIES = ("Kinshasa", "Lubumbashi", "Goma", "Bukavu", "Kisangani", "Matadi", "Kananga", "Mbuji-Mayi",
           "Kolwezi", "Likasi", "Kindu", "Mbandaka", "Bunia", "Uvira", "Boma")
_KINDS = ("pharmacie", "quincaillerie", "boutique", "librairie", "boulangerie", "supermarché", "épicerie",
          "restaurant", "salon", "dépôt", "alimentation", "magasin", "papeterie")
_NAMED = re.compile(r"(?:appel[ée]+s?|nomm[ée]+s?)\s+[«\"']?\s*([A-ZÀ-Ý][\w'-]*(?:\s+[A-ZÀ-Ý][\w'-]*)*)")


def _deterministic(base: dict, prompt: str) -> dict:
    """Personnalisation minimale : nom de boutique (et ville) tirés du prompt."""
    spec, low = copy.deepcopy(base), prompt.lower()
    city = next((c for c in _CITIES if c.lower() in low), None)
    kind = next((k for k in _KINDS if k in low), None)
    if m := _NAMED.search(prompt):
        name = m.group(1).strip()
    elif kind:
        name = f"{kind.capitalize()} de {city}" if city else kind.capitalize()
    else:
        return spec
    shop = spec.get("shop")
    if isinstance(shop, dict):
        shop["name"] = name
        if city:
            shop["city"] = f"{city}, RDC"
    if "invoice" in spec:
        where = f"{city}, RDC" if city else (shop or {}).get("city", "")
        spec["invoice"]["header"] = f"{name} — {where}" if where else name
        spec["invoice"]["note"] = f"Merci pour votre achat chez {name} !"
    return spec


def _check(base: dict, cand: object) -> tuple[str, int, list[str]]:
    """(diff, lignes, erreurs) d'une proposition : validation puis limite de MAX_LINES."""
    errors = validate(base, cand)
    if errors:
        return "", 0, errors
    diff_text, n = diff(base, cand)  # type: ignore[arg-type]
    return diff_text, n, [f"Diff trop grand : {n} lignes modifiées (max {MAX_LINES})."] if n > MAX_LINES else []


def ask_profile(prompt: str) -> tuple[dict | None, str | None]:
    """Profil métier par Gemma, une nouvelle tentative avec les erreurs : (profil | None, erreur)."""
    messages = [{"role": "user", "content": _profile_prompt(prompt)}]
    error = None
    for _ in range(2):
        raw = ask_gemma(messages)
        try:
            profile = _extract_json(raw)
            errors = [] if isinstance(profile, dict) else ["Le profil doit être un objet JSON."]
        except json.JSONDecodeError as exc:
            profile, errors = None, [f"Réponse non JSON : {exc}"]
        if not errors:
            errors = [f"{app} : {e}" for app in APPS for e in _check(base_spec(app), apply_profile(base_spec(app), profile))[2]]
        if not errors:
            return profile, None
        error = " ".join(errors)
        messages += [{"role": "assistant", "content": raw},
                     {"role": "user", "content": "Profil refusé. Corrige et renvoie le JSON complet du profil. "
                      "Erreurs :\n- " + "\n- ".join(errors)}]
    return (profile if isinstance(profile, dict) else None), error


def build_app(app: str, prompt: str, profile: dict | None = None, source: str = "local",
              gemma_error: str | None = None) -> dict:
    """Construit, contrôle et enregistre la build d'une app (spec retenue : proposée ou base)."""
    base = base_spec(app)
    if source == "gemma" and profile is None:  # Gemma a répondu, mais rien d'exploitable
        diff_text, n, errors = "", 0, [gemma_error or "Profil Gemma inexploitable."]
    else:
        proposal = apply_profile(base, profile) if profile is not None else _deterministic(base, prompt)
        diff_text, n, errors = _check(base, proposal)
    if errors:
        status, spec, error = "rejected", base, " ".join(errors)  # diff/compte : proposition refusée
    else:
        status, spec, error = "applied", proposal, None
    if app == "caisse":
        store.sync_products(spec["products"])
    return store.save_app_build(app, prompt, spec, diff_text, n, status, source, error)


def build_all(prompt: str) -> list[dict]:
    profile, source, error = None, "local", None
    if llm.mode() == "gemma":
        try:
            profile, error = ask_profile(prompt)
            source = "gemma"
        except LLMUnavailable:
            pass  # personnalisation déterministe hors ligne
    builds = [build_app(app, prompt, profile, source, error) for app in APPS]
    store.set_deployment(prompt, {b["app"]: b["id"] for b in builds})
    return builds


def reset() -> None:
    """Annule le déploiement et rétablit le catalogue de base."""
    store.clear_deployment()
    store.sync_products(base_spec("caisse")["products"])
