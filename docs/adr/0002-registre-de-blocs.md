# ADR-0002 — Un bloc = un JSON Schema + une fonction
**Statut** : accepté. **Décision** : chaque bloc est déclaré par `NodeSpec` ; son schéma alimente le prompt du LLM, la validation et le formulaire UI. **Conséquences** : ajout d'un bloc sans toucher moteur/API/UI ; le LLM ne connaît que les blocs réellement exécutables. Risque : schémas limités (pas de types conditionnels complexes).
