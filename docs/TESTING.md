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

## 3. Non exécuté / non vérifié
- Frontend (`npm run dev`, build) : **non exécuté** dans cette session.
- Parcours de bout en bout dans le navigateur : **non exécuté**.
- Envoi réel Telegram/Gmail et appel à Gemma 4 réel : **non exécutés** (identifiants/modèle absents).

## 4. Protocole d'évaluation (composante scientifique, à faire)
- **Entrée** : jeu de prompts annotés (`experiments/prompts.jsonl`, séparation dev/test).
- **Métriques** : validité du schéma (% sans erreur `validate`), exécutabilité (% dry-run `success`), correction sémantique (annotation humaine des blocs attendus), nb moyen de tentatives.
- **Variable** : `generator.MAX_REPAIRS` ∈ {0, 1, 2} ; baseline = 0 (sortie brute).
- **Reproductibilité** : modèle, température et version du prompt système consignés pour chaque run.
