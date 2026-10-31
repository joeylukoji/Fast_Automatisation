# Documentation d'architecture — Kernel (MVP hackathon, 4 h)

Kernel : on décrit un besoin en langage naturel, Gemma 4 génère un workflow visuel, l'utilisateur le modifie, le simule, puis l'exécute après validation explicite.

| Fichier | Contenu |
|---|---|
| [requirements.md](requirements.md) | Problème, acteurs, exigences, périmètre MVP, risques |
| [use-cases.md](use-cases.md) | Diagramme Use Case + fiches UC1–UC4 |
| [class-diagram.puml](class-diagram.puml) | Classes métier, services, DTO, adaptateurs |
| [sequence-diagram.puml](sequence-diagram.puml) | Parcours principal : prompt → génération → simulation → exécution |
| [data-model.md](data-model.md) | Entités, contraintes, validations, migrations |
| [architecture.md](architecture.md) | Comparaison, choix, modules, C4 |
| [architecture-diagram.mmd](architecture-diagram.mmd) | C4 Context + Container + Component (Mermaid) |
| [contracts.md](contracts.md) | API REST, schémas, erreurs, interfaces internes |
| [tasks.md](tasks.md) | Plan multi-agents, découpage par fonctionnalité, graphe de tâches |
| [TESTING.md](TESTING.md) | Tests, commandes, résultats vérifiés |
| [adr/](adr/) | Décisions d'architecture |

Ces documents décrivent **le code présent dans le dépôt** (état vérifié le 2026-10-31) et marquent explicitement ce qui reste à faire.
