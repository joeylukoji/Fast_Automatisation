# Recherche & entraînement — générateur local de workflows

Modèle léger, hors-ligne, qui transforme un prompt en workflow Kernel valide. Il sert de **secours quand Gemma 4 n'est pas disponible** (`KERNEL_LLM_LOCAL=1`) et de **baseline** pour l'évaluation future de Gemma 4.

```bash
pip install -r experiments/requirements.txt
python experiments/build_dataset.py   # régénère data/synthetic.jsonl (déterministe)
python experiments/train.py           # sélection, évaluation, export backend/app/ai/local_model.json
```

| Document | Contenu |
|---|---|
| [problem_definition.md](problem_definition.md) | Question, cible, métriques, hypothèses |
| [data_sources.md](data_sources.md) · [data_manifest.json](data_manifest.json) | Provenance, licence, empreintes |
| [eda_report.md](eda_report.md) | Audit des données |
| [model_selection.md](model_selection.md) | Paradigmes, candidats, baselines, préparation, protocole |
| [training_config.yaml](training_config.yaml) | Configuration |
| [experiments.csv](experiments.csv) · [results.json](results.json) | Registre d'expériences (généré) |
| [evaluation_report.md](evaluation_report.md) | Résultats, erreurs, expériences E1–E3 |
| [model_card.md](model_card.md) | Usage, limites |
| [reproducibility.md](reproducibility.md) | Versions, commandes, contrôles |
