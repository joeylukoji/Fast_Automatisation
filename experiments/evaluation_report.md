# Rapport d'évaluation

Tous les nombres ci-dessous sont **mesurés** par `python experiments/train.py` (registre : `experiments.csv`, détail : `results.json`). IC 95 % par bootstrap (2 000 tirages) : avec 42–54 exemples, ils sont larges.

## Résultats finaux
| Modèle | Test synthétique : exactitude [IC 95 %] | F1 macro | Test manuel : exactitude [IC 95 %] | F1 macro | F1 blocs (manuel) | Workflows valides | Simulations OK |
|---|---|---|---|---|---|---|---|
| B0 majoritaire | 0.056 [0.00, 0.13] | 0.01 | 0.071 [0.00, 0.17] | 0.01 | 0.32 | 100 % | 100 % |
| B1 mots-clés | 0.574 [0.44, 0.70] | 0.55 | 0.857 [0.74, 0.95] | 0.85 | 0.94 | 100 % | 100 % |
| M1 char LR (C=2) | **0.778** [0.67, 0.89] | 0.82 | 0.714 [0.57, 0.83] | 0.70 | 0.89 | 100 % | 100 % |
| **M4 hybride (C=0.5, kw=1)** — retenu | 0.574 [0.44, 0.70] | 0.55 | **0.929** [0.83, 1.00] | 0.93 | 0.98 | 100 % | 100 % |

Validité 100 % pour tous : c'est une propriété du constructeur déterministe, pas du classifieur (une mauvaise intention donne un workflow valide mais faux). Latence mesurée de l'inférence pure Python : ≈ 0,2 ms par prompt (CPU). Accord inférence pure Python / scikit-learn : 100 % sur 96 prompts.

## Expériences
**E1 — Sélection (validation)**. Hypothèse H1. M1 obtient 0.963 sur val synthétique mais 0.71–0.75 sur val manuelle ; B1 obtient 1.0 / 0.964 ; M2 ≤ 0.67 ; M3 ≤ 0.69 / 0.50. Plusieurs M4 sont ex æquo à 1.0 / 1.0 ; l'égalité est tranchée par l'ordre de la grille (premier = C=0.5, kw=1).

**E2 — Évaluation de M1 vs baselines (1ʳᵉ exécution)**. M1 bat B1 sur le test synthétique (0.778 vs 0.574) mais perd sur le test manuel (0.714 vs 0.857, IC chevauchants). Conclusion autorisée : **H1 n'est pas confirmée sur des formulations libres** ; M1 apprend surtout le style des gabarits.

**E3 — Modèle hybride (H2)**. Méthode : M1 + indicateurs mots-clés de B1, grille C × poids, sélection sur validation. Résultat : 0.929 sur le test manuel vs 0.857 (B1) et 0.714 (M1). Sur le test synthétique, M4 = B1 (0.574) : les formulations de test (« bot telegram », « message électronique ») échappent aux mots-clés et M4 suit alors les règles. Conclusion autorisée : **gain probable mais non démontré** face à B1 (IC chevauchants, 42 exemples, 3 erreurs de différence) ; gain net face à M1.

## Erreurs restantes du modèle retenu (test manuel)
Voir `results.json → manual_errors` (liste exacte des prompts mal classés).

## Écarts de protocole (transparence)
0. B0 dépendait de l’ordre aléatoire des ensembles Python (14 classes à égalité) ; tie-break alphabétique ajouté, deux exécutions successives donnent désormais un `results.json` identique octet pour octet.
1. B1 contenait un bug (recherche de `url`/`email` en minuscules alors que la normalisation insère `URL`/`EMAIL`) découvert **après** une première exécution sur les tests ; corrigé, puis tout a été relancé. Le passage des indicateurs à `kw_flags` (texte entouré d'espaces) a fait passer B1 de 0.810 à 0.857 sur le test manuel.
2. Les erreurs de M1 sur le test manuel ont été vues avant de concevoir E3. Les listes de mots-clés n'ont **pas** été modifiées après coup et la sélection d'E3 n'utilise que la validation ; le test manuel reste néanmoins « vu » au sens strict. Un nouveau test rédigé par une autre personne serait nécessaire pour une estimation non biaisée.

## Non mesuré
Gemma 4 (H3), robustesse aux fautes d'orthographe, prompts hors des 14 intentions, vrais utilisateurs.
