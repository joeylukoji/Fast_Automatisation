# Stratégie d'apprentissage et protocole

## Paradigmes considérés
| Approche | Retenue ? | Raison |
|---|---|---|
| Supervisé (classification d'intention) | **Oui** | Cible claire, données annotables, coût minime |
| Génération par LLM préentraîné (Gemma 4) + validation/réparation | Hors entraînement | C'est le système principal ; pas de modèle accessible ici ⇒ évaluation reportée (H3) |
| Fine-tuning d'un transformeur (ex. CamemBERT) | Non | Pas de GPU, pas d'accès vérifié à un hub de modèles, 600 exemples gabaritiés ⇒ risque fort de sur-apprentissage du gabarit |
| Non / semi / auto-supervisé, renforcement | Non | Pas de données non annotées réelles ni de signal de récompense |

## Candidats
| ID | Modèle | Justification | Risque |
|---|---|---|---|
| B0 | Classe majoritaire | Plancher | — |
| B1 | Règles mots-clés écrites à la main | Baseline crédible, explicable | Rigide face aux synonymes |
| M1 | TF-IDF n-grammes de caractères 2–5 + régression logistique | Robuste aux flexions/fautes, rapide | Apprend le gabarit synthétique |
| M2 | TF-IDF mots 1–2 + régression logistique | Comparaison de représentation | Vocabulaire fermé |
| M3 | k-NN cosinus sur M1 | Non paramétrique | Sensible au gabarit |
| M4 | M1 + 5 indicateurs mots-clés (listes de B1) × poids | H2 : combiner robustesse et connaissances explicites | Sur-pondération des règles |

## Préparation des données
Normalisation unique (`local_model.normalize`) : minuscules, suppression des accents, URL → `URL`, e-mail → `EMAIL` (évite d'apprendre des domaines précis). Le TF-IDF est **ajusté sur l'entraînement seul** puis appliqué aux autres partitions. Pas d'augmentation au-delà de la génération ; classes équilibrées à l'entraînement.

## Protocole anti-fuite
- Séparation **par formulation** : aucune formulation de composant n'apparaît à la fois en train et en val/test (équivalent d'une séparation par groupe).
- Sélection sur **val synthétique + val manuelle** ; les deux tests ne servent qu'à l'évaluation finale.
- Le modèle exporté est réajusté sur train + val + manual_val avec les hyperparamètres choisis ; les scores rapportés viennent du modèle ajusté sur train seul.
