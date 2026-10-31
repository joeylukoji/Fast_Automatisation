# Générateur d'applications : contrat backend ↔ frontend

But (démo) : au départ, aucune application n'existe dans l'onglet Applications. L'utilisateur décrit
son business ; Gemma personnalise chaque application en modifiant **seulement des détails** de sa
couche de personnalisation (≤ 120 lignes de diff par application). Les applications deviennent
visibles après la génération.

Gemma ne modifie jamais le code React/Python : il modifie une *spec* par application (JSON + CSS
limité à l'application), validée par le backend. Le code des apps lit cette spec.

## Specs de base : `backend/app/apps/specs/<app>.json`

Apps : `caisse`, `clients`, `ventes`, `automatisation`. Toutes partagent cette forme (champs
non pertinents pour une app peuvent être absents) :

```json
{
  "app": "caisse",
  "title": "Caisse",
  "shop": {"name": "Kernel Market", "city": "Kinshasa, RDC", "slogan": "Votre dépôt de quartier"},
  "theme": {"accent": "#9A3412", "background": "#FDFCF8"},
  "labels": {"checkout": "Encaisser", "...": "..."},
  "products": [{"name": "Casier Primus 72cl", "unit": "casier", "price_usd": 18}],
  "customer_fields": [{"key": "quartier", "label": "Quartier"}],
  "invoice": {"header": "Kernel Market — Kinshasa, RDC", "note": "Merci pour votre achat !", "footer": "..."},
  "css": [".app-root .os-pos-total { font-size: 22px; }"]
}
```

- `products` : uniquement dans `caisse` (6 produits actuels du seed). `customer_fields` : dans `clients`.
  `invoice` : dans `ventes`. `css` est une **liste de lignes** (une règle par ligne) pour que le diff compte les lignes.
- Les libellés (`labels`) couvrent les textes visibles de chaque app (titres, boutons, colonnes).

## Contrôles du backend (`backend/app/apps/builder.py`)

- Diff = `difflib.unified_diff` des JSON formatés (`indent=2`, `ensure_ascii=False`) base → proposé ;
  `lines_changed` = lignes `+`/`-` hors en-têtes. **> 120 → refus** ; une nouvelle tentative avec le
  message d'erreur à Gemma ; si encore refusé ou invalide → spec de base (statut `rejected`).
- Validation : mêmes clés de premier niveau que la base (pas d'ajout/suppression de clé), `app` inchangé,
  types respectés, couleurs `#RRGGBB`, ≤ 12 produits avec `price_usd` > 0, ≤ 6 `customer_fields`
  (`key` en `[a-z_]+`), chaque ligne CSS commence par `.app-root` et ne contient ni `@import`, ni `url(`,
  ni `<`, ni `expression`, ni `javascript:` ; ≤ 40 lignes CSS.
- **Un seul appel Gemma** (message `user`, sans `response_format`) renvoie un petit profil métier
  (`shop`, `accent`, `products`, `customer_fields`, `labels`, `invoice_note`) appliqué aux 4 specs ; chaque
  spec résultante passe la validation et la limite de 120 lignes (≈ 30-40 s au total ; demander les 4 specs
  complètes dépassait 2 min par app). Si le générateur n'est pas Gemma (local/mock),
  personnalisation déterministe minimale (titre/nom de boutique issus du prompt) pour que la démo marche hors ligne.

## Persistance (`store.py`)

`app_build(id, app, prompt, spec JSON, diff TEXT, lines_changed INT, status, source, created_at)`,
`status` ∈ `applied` | `rejected`. L'état « déployé » = dernière build de chaque app depuis le dernier reset
(table `app_state(key, value)` ou équivalent). À l'application de la build `caisse`, le catalogue
`product` est synchronisé avec `spec.products` (par nom ; les ventes passées gardent leurs lignes).
`invoice_render` utilise `shop`/`invoice` de la spec `ventes` déployée (sinon valeurs par défaut).

## API (`/api/apps`, `backend/app/apps/router.py`)

| Méthode | Chemin | Corps → réponse |
|---|---|---|
| GET | `/api/apps` | `{deployed: bool, prompt, apps: {<app>: spec}}` (specs déployées, sinon `apps: {}`) |
| POST | `/api/apps/build` | `{prompt}` → `{deployed: true, prompt, builds: [Build]}` (les 4 apps, séquentiel) |
| GET | `/api/apps/builds` | `[Build]` récentes |
| POST | `/api/apps/reset` | annule le déploiement (démo à refaire) → `{deployed: false}` |

`Build = {id, app, status, source, lines_changed, max_lines: 120, diff, spec, error|null, created_at}`

## Frontend

- `#/apps` sans déploiement → écran « Atelier » : zone de description (exemples RDC : pharmacie à
  Lubumbashi, quincaillerie à Goma, boutique de pagnes à Kinshasa), bouton « Générer mes applications ».
- Pendant/après la génération : journal par app (statut, source, compteur `xx / 120 lignes`, diff coloré +/−),
  puis bouton « Ouvrir le bureau » qui révèle le bureau existant.
- Les apps lisent leur spec : `title`, `shop`, `theme.accent` (variable CSS sur la fenêtre), `labels`,
  `customer_fields` (champs supplémentaires du formulaire client, envoyés dans `extra` si le backend le gère,
  sinon affichage seulement), et injectent `css` dans un `<style>` ; la racine de chaque app a la classe `app-root`.
- Barre des tâches : « Réinitialiser la démo » (POST reset → retour à l'Atelier) et « Régénérer ».
