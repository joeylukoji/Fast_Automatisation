# Module ERP : contrat backend ↔ frontend

Objectif : des composants ERP réutilisables (blocs de workflow + API) et une mini-application
« bureau » dans l'onglet **Applications** (`#/apps`) pour tester. Cas principal : la caissière
enregistre un client (nom, email, téléphone) puis une vente ; une facture part automatiquement par email.

## Données (SQLite, `store.py`, mêmes conventions que `workflow`/`run`)

- `customer(id, name, email UNIQUE, phone, created_at)`
- `product(id, name, unit, price_usd REAL, created_at)` — catalogue de départ inséré si vide :
  Casier Primus 72cl (18), Sac de riz 25 kg (32), Bidon d'huile 5 L (9), Sac de sucre 10 kg (12),
  Farine de maïs 25 kg (22), Pack d'eau 1,5 L x6 (3.5)
- `sale(id, invoice_number, customer_id, items JSON, total_usd, total_cdf, rate, created_at, invoice_status, run_ids JSON)`
  - `invoice_number` = `FAC-2026-0001` (séquentiel)
  - `invoice_status` ∈ `sent` | `failed` | `not_sent`
- Taux : `KERNEL_ERP_USD_CDF` (défaut `2300`). `total_cdf` arrondi à la centaine.

## API (`/api/erp`, fichier `backend/app/erp.py` monté par un `APIRouter`)

| Méthode | Chemin | Corps / réponse |
|---|---|---|
| GET | `/api/erp/customers` | `[Customer]` avec `purchases` (nb) et `total_spent_usd` |
| POST | `/api/erp/customers` | `{name, email, phone?}` → `Customer` (409 si email existe) |
| GET | `/api/erp/products` | `[Product]` |
| GET | `/api/erp/sales` | `[Sale]` (plus récentes d'abord, `customer_name`, `customer_email`) |
| POST | `/api/erp/sales` | `{customer_id, items:[{product_id, qty}], send_invoice: bool=true}` → `{sale: Sale, runs: [RunResult]}` |
| GET | `/api/erp/sales/{id}/invoice` | facture HTML (`text/html`) |
| GET | `/api/erp/automation` | `{workflow_id \| null, workflow}` : workflow de facturation actif |
| POST | `/api/erp/automation/install` | enregistre le workflow par défaut dans `/api/workflows` → `WorkflowRecord` |

`Sale` = `{id, invoice_number, customer_id, customer_name, customer_email, items:[{product_id, name, qty, unit_price_usd, line_total_usd}], total_usd, total_cdf, rate, created_at, invoice_status, run_ids}`

### Déclenchement sur vente
`POST /api/erp/sales` crée la vente puis, si `send_invoice` :
1. exécute **en réel** (l'encaissement par la caissière vaut validation explicite) chaque workflow
   enregistré dont un nœud est de type `trigger_erp_sale` ;
2. s'il n'y en a aucun, exécute le workflow par défaut (non enregistré).
Résultat enregistré via `store.save_run`, `invoice_status` = `sent` si tous les runs réussissent.

Charge utile du déclencheur (`trigger_payload`) :
```json
{"sale_id": "...", "invoice_number": "FAC-2026-0001", "date": "2026-10-31",
 "customer": {"id": "...", "name": "...", "email": "...", "phone": "..."},
 "items": [{"name": "...", "qty": 2, "unit_price_usd": 18, "line_total_usd": 36}],
 "total_usd": 36, "total_cdf": 82800, "rate": 2300}
```

## Blocs réutilisables (`backend/app/nodes/erp.py`, enregistrés comme les blocs de `builtin.py`)

| type | rôle | params | sortie |
|---|---|---|---|
| `trigger_erp_sale` | déclencheur « Nouvelle vente (ERP) » | — | la charge utile ci-dessus |
| `erp_customer_lookup` | fiche client CRM | `email` | `{found, id, name, email, phone, purchases, total_spent_usd}` |
| `invoice_render` | génère la facture | `sale_id` | `{invoice_number, subject, html, text, total_usd, total_cdf, customer_email}` |
| `gmail_send` (existant) | + param facultatif `html` | `to, subject, body, html?` | email multipart texte + HTML |

`invoice_render` n'a pas d'effet de bord : il s'exécute aussi en dry-run.

Workflow par défaut « Facture automatique après vente » :
`vente (trigger_erp_sale) → facture (invoice_render, sale_id={{vente.sale_id}}) → email (gmail_send, to={{vente.customer.email}}, subject={{facture.subject}}, body={{facture.text}}, html={{facture.html}})`

En-tête de facture : « Kernel Market — Kinshasa, RDC ».
