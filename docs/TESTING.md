# Tests et validation

## 1. Commandes
```bash
cd backend && pip install -r requirements.txt && python -m pytest -q
```

## 2. Résultat vérifié (2026-10-31)
`15 passed` (dont CRUD workflows, historique, validation, repli Gemma → local)

| Test | Couvre | Résultat |
|---|---|---|
| test_cycle_detected | contrainte 7 | ✅ |
| test_missing_param_and_unknown_type | contraintes 2–3 | ✅ |
| test_condition_branches_real_run | aiguillage true/false, skipped | ✅ |
| test_dry_run_simulates_side_effects | ENF1, UC3 | ✅ |
| test_generator_repairs_invalid_output | EF3 | ✅ |
| test_generator_gives_up_after_repairs | EF3 (échec) | ✅ |
| test_api_nodes_and_approval_gate | `/api/nodes`, garde 400 | ✅ |
| test_generate_without_llm_config_returns_503 | 503 | ✅ |
| test_generate_mock_mode | mode démo | ✅ |

## 3. Parcours de bout en bout (vérifié le 2026-10-31)
Backend `KERNEL_LLM_MOCK=1 uvicorn app.main:app` + `npm run dev`, piloté par Playwright (Chromium) :
prompt → « Générer » → 3 blocs affichés → « Simuler » → journal « Simulation — réussie », blocs LLM et Telegram `simulé`, aucune erreur JS. Capture : [demo-screenshot.png](demo-screenshot.png).
Limite : en mode mock, le workflow généré est toujours le même (il ne dépend pas du prompt).

Mode `KERNEL_LLM_LOCAL=1` : prompt conditionnel → 5 blocs avec branches oui/non, simulation réussie ([demo-local-model.png](demo-local-model.png)).

## 3ter. Stack Docker (vérifiée le 2026-10-31)
`docker compose up` : backend et frontend `healthy` ; via nginx :8080 → santé, génération locale (`llm_gmail`, 0,71), enregistrement d'un workflow conservé après `docker compose restart backend`, route SPA 200, `pytest` dans le conteneur (15 réussis), parcours navigateur complet sans erreur JS, mobile sans débordement horizontal. Image `ollama` (profil `gemma`) **non testée** ici.

## 3bis. Non exécuté / non vérifié
- Envoi réel Telegram/Gmail et appel à Gemma 4 réel : **non exécutés** (identifiants/modèle absents).

## 4. Évaluation du générateur local : voir [experiments/evaluation_report.md](../experiments/evaluation_report.md)

## 5. Protocole d'évaluation de Gemma 4 (à faire)
- **Entrée** : jeu de prompts annotés (`experiments/prompts.jsonl`, séparation dev/test).
- **Métriques** : validité du schéma (% sans erreur `validate`), exécutabilité (% dry-run `success`), correction sémantique (annotation humaine des blocs attendus), nb moyen de tentatives.
- **Variable** : `generator.MAX_REPAIRS` ∈ {0, 1, 2} ; baseline = 0 (sortie brute).
- **Reproductibilité** : modèle, température et version du prompt système consignés pour chaque run.
