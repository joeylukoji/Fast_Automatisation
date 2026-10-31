# Tests et validation

## 1. Commandes
```bash
cd backend && pip install -r requirements.txt && python -m pytest -q
```

## 2. Résultat vérifié (2026-10-31)
`9 passed in 0.88s`

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

## 3bis. Non exécuté / non vérifié
- Envoi réel Telegram/Gmail et appel à Gemma 4 réel : **non exécutés** (identifiants/modèle absents).

## 4. Protocole d'évaluation (composante scientifique, à faire)
- **Entrée** : jeu de prompts annotés (`experiments/prompts.jsonl`, séparation dev/test).
- **Métriques** : validité du schéma (% sans erreur `validate`), exécutabilité (% dry-run `success`), correction sémantique (annotation humaine des blocs attendus), nb moyen de tentatives.
- **Variable** : `generator.MAX_REPAIRS` ∈ {0, 1, 2} ; baseline = 0 (sortie brute).
- **Reproductibilité** : modèle, température et version du prompt système consignés pour chaque run.
