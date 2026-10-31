# Reproductibilité

- **Environnement mesuré** : Python 3.13.18, scikit-learn 1.9.1, scipy 1.18.1 (voir `requirements.txt`), Linux, 4 CPU, sans GPU.
- **Graine** : 42 (génération des données, régression logistique, bootstrap).
- **Données** : `data_manifest.json` (SHA-256 et nombres de lignes) ; `build_dataset.py` est déterministe.
- **Commandes** :
  ```bash
  pip install -r experiments/requirements.txt
  python experiments/build_dataset.py && sha256sum experiments/data/synthetic.jsonl
  python experiments/train.py
  cd backend && python -m pytest -q
  ```
- **Contrôles automatiques** : `train.py` vérifie l'accord 100 % entre l'inférence pure Python et scikit-learn ; le test `test_generate_local_model` vérifie l'intégration API.
- **Versionnement** : code, données, configuration, registre (`experiments.csv`, `results.json`) et modèle exporté sont dans Git. Pas d'outil de suivi (MLflow…) : registre CSV jugé suffisant pour 24 exécutions.
- **Durée** : ≈ 7 s pour l'ensemble de la grille.
