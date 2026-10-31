# Fiche modèle — générateur local de workflows

- **Fichier** : `backend/app/ai/local_model.json` (229 Ko) ; code : `backend/app/ai/local_model.py` (inférence pure Python).
- **Type** : TF-IDF n-grammes de caractères 2–5 + 5 indicateurs mots-clés, régression logistique multinomiale (scikit-learn 1.9.1), 14 classes ; constructeur déterministe de workflow.
- **Activation** : `KERNEL_LLM_LOCAL=1` (prioritaire sur `KERNEL_LLM_MOCK`).
- **Contrat** : entrée `prompt: str` → `Workflow` JSON (schéma `backend/app/schemas.py`), via `POST /api/generate` (`attempts = 1`). Aucune erreur levée pour un prompt non vide ; prompt vide → 400 (API).
- **Performances mesurées** : exactitude 0.929 [0.83, 1.00] sur 42 prompts manuels ; voir evaluation_report.md.
- **Usage prévu** : démo hors-ligne, secours si Gemma 4 indisponible, baseline de recherche.
- **Hors usage** : toute demande hors des 14 structures (le modèle choisira quand même l'une d'elles — il n'a pas de rejet) ; production.
- **Limites** : textes des messages génériques ; condition limitée à `statut == code` ; un seul annotateur ; données non issues d'utilisateurs réels ; en simulation la condition part sur « false » car la requête HTTP n'est pas exécutée.
- **Contrôles** : l'utilisateur relit le graphe ; la simulation et l'approbation explicite restent obligatoires avant toute exécution réelle.
