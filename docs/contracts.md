# Contrats

Base : `/api`, JSON UTF-8. Erreurs HTTP au format FastAPI : `{"detail": "<message en français>"}`. Les erreurs **métier** (workflow invalide) ne sont pas des erreurs HTTP : elles sont dans le corps (`errors`, `validation_errors`).

| Route | Méthode | Entrée | Succès | Erreurs |
|---|---|---|---|---|
| `/api/health` | GET | — | `200 {"status":"ok", …}` | — |
| `/api/nodes` | GET | — | `200 [NodeCatalogEntry]` | — |
| `/api/generate` | POST | `GenerateRequest` | `200 GenerateResponse` | `400` prompt vide · `503` LLM indisponible |
| `/api/run` | POST | `RunRequest` | `200 RunResult` | `400` exécution réelle sans `approved` · `422` JSON non conforme |
| `/api/runs/{run_id}` | GET | — | `200 RunResult` | `404` |

## Schémas
```jsonc
// Workflow
{ "name": "Météo pluie", 
  "nodes": [ {"id":"t","type":"trigger_manual","params":{}},
             {"id":"c","type":"condition","params":{"left":"{{t.city}}","op":"equals","right":"Paris"}},
             {"id":"m","type":"telegram_send","params":{"chat_id":"123","text":"Il pleut à {{t.city}}"}} ],
  "edges": [ {"source":"t","target":"c"}, {"source":"c","target":"m","branch":"true"} ] }

// GenerateRequest   { "prompt": "string non vide" }
// GenerateResponse  { "workflow": Workflow | null, "errors": ["..."], "attempts": 1..3 }
// RunRequest        { "workflow": Workflow, "dry_run": true, "approved": false, "trigger_payload": {} }
// RunResult         { "run_id": "uuid", "dry_run": true, "status": "success|error",
//                     "steps": [StepResult], "validation_errors": ["..."] }
// StepResult        { "node_id": "c", "status": "success|error|skipped", "simulated": false,
//                     "output": {...} | null, "error": null, "duration_ms": 3 }
// NodeCatalogEntry  { "type": "...", "title": "...", "params_schema": {JSON Schema},
//                     "side_effect": bool, "is_trigger": bool, "branching": bool }
```
Les paramètres exacts de chaque bloc sont fournis dynamiquement par `GET /api/nodes` (le frontend ne doit pas les coder en dur).

## Règles
- Gabarits : `{{<node_id>.<champ>}}` référence la sortie d'un bloc précédent.
- Simulation : `dry_run=true` ⇒ aucun bloc `side_effect` exécuté (`simulated=true`).
- Exécution réelle : `dry_run=false` **et** `approved=true`.

## Interfaces internes (stables)
```python
# ai/llm.py — port LLM, injectable
def complete(messages: list[dict], json_mode: bool = False) -> str  # lève LLMUnavailable
# ai/generator.py
def generate(prompt: str, complete=llm.complete) -> tuple[Workflow | None, list[str], int]
# engine.py
def validate(wf: Workflow) -> list[str]
def run(wf: Workflow, dry_run=True, trigger_payload=None) -> RunResult
# nodes/registry.py — extension
register(NodeSpec(type, title, params_schema, run=lambda params, inputs, ctx: dict, side_effect, is_trigger, branching))
```
Toute modification de ces contrats doit être annoncée à l'orchestrateur et aux agents front/back/tests (tasks.md).
