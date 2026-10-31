# Audit des données (calculé le 2026-10-31)

| Partition | N | Classes | Min/Max par classe | Longueur médiane (mots) | Min–max |
|---|---|---|---|---|---|
| train | 560 | 14 | 40 / 40 | 13 | 3–29 |
| val | 54 | 14 | 1 / 6 | 15 | 6–31 |
| test | 54 | 14 | 1 / 6 | 25 | 10–36 |
| manual_val | 28 | 14 | 2 / 2 | 8 | 2–11 |
| manual (test) | 42 | 14 | 3 / 3 | 9 | 2–14 |

- **Valeurs manquantes** : aucune (champs `prompt`, `intent` présents partout).
- **Doublons** : 0 entre partitions (pas de fuite par copie) ; 39 doublons exacts à l'intérieur des partitions synthétiques (tirages identiques), conservés car sans effet sur l'évaluation croisée.
- **Déséquilibre** : train équilibré ; val/test synthétiques déséquilibrés car une seule formulation par composant ⇒ peu de phrases distinctes pour les intentions courtes.
- **Décalage de distribution** : les prompts manuels sont ~2× plus courts que le test synthétique et plus télégraphiques (« Telegram + email à … ») : c'est l'écart que le test manuel doit mesurer.
- **Cohérence des annotations** : synthétique correcte par construction ; manuel relu une fois, un seul annotateur (pas d'accord inter-annotateurs mesurable).
