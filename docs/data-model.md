# Modèle de données

## État actuel (MVP)
Pas de base de données. Le **workflow est un document JSON** échangé entre frontend, LLM et backend (`schemas.py` = source de vérité). Les résultats d'exécution sont conservés dans `RUNS: dict[str, RunResult]` en mémoire (perdus au redémarrage). Choix justifié en [ADR-0003](adr/0003-pas-de-base-de-donnees-mvp.md).

## Entités
| Entité | Clé | Champs | Relations |
|---|---|---|---|
| Workflow | (document) | name, nodes[], edges[] | 1 → 1..* Node, 1 → 0..* Edge |
| Node | `id` (unique dans le workflow) | type, params | référencé par Edge |
| Edge | (source, target, branch) | branch ∈ {true,false,null} | FK logiques source/target → Node.id |
| RunResult | `run_id` (uuid) | dry_run, status, validation_errors | 1 → 0..* StepResult |
| StepResult | (run_id, node_id) | status, simulated, output, error, duration_ms | node_id → Node.id |

## Contraintes d'intégrité (vérifiées par `engine.validate`)
1. Au moins un bloc ; identifiants de blocs uniques.
2. `type` présent dans le registre.
3. Paramètres `required` du JSON Schema du bloc non vides.
4. `source` et `target` d'un lien existent.
5. Lien issu d'un bloc `branching` (condition) → `branch` obligatoire ; sinon `branch` interdit.
6. Un déclencheur n'a pas de lien entrant ; au moins un déclencheur.
7. Graphe acyclique (tri topologique).
8. Gabarits `{{bloc.champ}}` résolus à l'exécution (strict en réel, tolérant en simulation).

## Évolution (post-MVP) — SQLite
```sql
CREATE TABLE workflow (id TEXT PRIMARY KEY, name TEXT NOT NULL, definition JSON NOT NULL,
                       created_at TIMESTAMP NOT NULL, updated_at TIMESTAMP NOT NULL);
CREATE TABLE run (id TEXT PRIMARY KEY, workflow_id TEXT REFERENCES workflow(id) ON DELETE SET NULL,
                  dry_run BOOLEAN NOT NULL, status TEXT CHECK (status IN ('success','error')) NOT NULL,
                  validation_errors JSON NOT NULL DEFAULT '[]', started_at TIMESTAMP NOT NULL);
CREATE TABLE step (run_id TEXT REFERENCES run(id) ON DELETE CASCADE, node_id TEXT NOT NULL,
                   status TEXT CHECK (status IN ('success','error','skipped')) NOT NULL,
                   simulated BOOLEAN NOT NULL, output JSON, error TEXT, duration_ms INTEGER NOT NULL,
                   PRIMARY KEY (run_id, node_id));
```
Migration unique `0001_init.sql`. Le workflow reste stocké en JSON (le schéma évolue avec le registre de blocs).
