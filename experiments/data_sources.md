# Sources de données

Aucun jeu public d'association « prompt français → workflow au format Kernel » n'existe à notre connaissance : le format est propre au projet. **Aucune donnée externe n'a été utilisée** ; aucune donnée personnelle (les adresses et identifiants sont fictifs).

| Fichier | Provenance | Volume | Annotation | Licence | Limites |
|---|---|---|---|---|---|
| `data/synthetic.jsonl` | Généré par `build_dataset.py` (graine 42) à partir de 6 formulations par composant de phrase | 668 (560/54/54) | Automatique (l'intention est connue à la génération) | Celle du dépôt | Phrases gabaritées, vocabulaire limité, val/test déséquilibrés (1–6 par classe) |
| `data/manual_val.jsonl` | Rédigé à la main pour ce projet | 28 (2/classe) | Manuelle, un seul annotateur | Celle du dépôt | Petit, même auteur que le reste |
| `data/manual_test.jsonl` | Rédigé à la main, avant tout entraînement | 42 (3/classe) | Manuelle, un seul annotateur | Celle du dépôt | Petit (IC larges), même auteur ⇒ biais de style possible |

Biais connus : toutes les données viennent du même rédacteur (l'assistant) ; elles ne représentent pas de vrais utilisateurs. Empreintes SHA-256 : [data_manifest.json](data_manifest.json).
