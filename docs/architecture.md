# Architecture

## 1. Options comparées
| Critère | Monolithe simple | **Monolithe modulaire + ports légers** | Hexagonal strict | Microservices |
|---|---|---|---|---|
| Temps de dev (4 h) | ★★★ | ★★★ | ★★ | ★ |
| Intégration | ★★★ | ★★★ | ★★ | ★ |
| Testabilité | ★ | ★★★ | ★★★ | ★★ |
| Complexité opérationnelle | faible | faible | faible | élevée |
| Évolution | ★ | ★★★ | ★★★ | ★★★ |

**Choix : monolithe modulaire (FastAPI) + SPA React**, avec deux ports réellement utiles empruntés à l'hexagonal : l'injection de la fonction `complete` du LLM (testable sans réseau, mock de démo) et le **registre de blocs** (les connecteurs sont des adaptateurs). Pas de couches « repository / use-case » artificielles. Voir [ADR-0001](adr/0001-monolithe-modulaire.md).

## 2. Modules backend (`backend/app/`)
| Module | Responsabilité | Dépend de |
|---|---|---|
| `schemas.py` | Format de workflow et DTO (source de vérité) | pydantic |
| `nodes/registry.py` | `NodeSpec`, `register`, `catalogue` | — |
| `nodes/builtin.py` | 6 blocs : trigger_manual, http_request, llm, condition, telegram_send, gmail_send | registry, connectors, ai.llm |
| `engine.py` | Validation, tri topologique, gabarits, exécution, dry-run | schemas, registry |
| `ai/llm.py` | Client « chat completions » + mock | httpx |
| `ai/generator.py` | Prompt système depuis le catalogue, boucle génération/réparation | engine, registry, llm |
| `connectors/` | Telegram (Bot API), Gmail (SMTP) | env `KERNEL_*` |
| `main.py` | Routes HTTP, garde d'approbation, stockage des runs | tout le reste |

Graphe de dépendances acyclique : `main → {generator, engine, registry}` ; `generator → {engine, llm}` ; `engine → registry` ; `builtin → {connectors, llm}`.

## 3. Frontend (`frontend/src/`)
`App.jsx` (mise en page) · `store.js` (état) · `api.js` (client `/api`) · `convert.js` (Kernel ↔ React Flow, dagre) · composants `PromptBar`, `GraphEditor`, `KernelNode`, `NodePanel` (formulaire depuis JSON Schema), `RunLog`. Vite proxifie `/api` vers `:8000`.

## 4. Principe clé : un bloc = un schéma
Le JSON Schema de paramètres d'un bloc alimente **à la fois** le prompt de Gemma 4, la validation serveur et le formulaire de l'éditeur. Ajouter un bloc ne touche ni le moteur, ni l'API, ni l'UI. ([ADR-0002](adr/0002-registre-de-blocs.md))

## 5. Sécurité / contrôle humain
Dry-run par défaut ; exécution réelle refusée sans `approved: true` ; confirmation UI ; secrets en variables d'environnement. ([ADR-0004](adr/0004-dry-run-et-approbation.md))

## 6. Vues C4
Voir [architecture-diagram.mmd](architecture-diagram.mmd). Pas de diagramme de déploiement : 2 processus locaux, aucune infrastructure.

## 7. Limites connues
Runs en mémoire ; exécution synchrone (requête bloquante) ; pas d'authentification ; déclencheur manuel uniquement ; Gmail via mot de passe d'application.
