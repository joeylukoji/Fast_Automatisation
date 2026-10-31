# Exigences et périmètre du MVP

## 1. Problème
Créer une automatisation (ex. « quand je lance, récupère la météo et envoie-la sur Telegram si il pleut ») demande aujourd'hui de connaître un outil type n8n/Zapier, ses blocs et sa syntaxe. Les LLM savent décrire une automatisation, mais leur sortie brute n'est ni fiable, ni vérifiable, ni sûre à exécuter.

## 2. Proposition de valeur
Décrire en français → obtenir un **workflow valide par construction** (validation + réparation automatique), **visible et modifiable**, **simulable sans effet de bord**, exécuté réellement **seulement après accord humain**.

## 3. Acteurs
| Acteur | Type | Rôle |
|---|---|---|
| Utilisateur | Principal | Décrit, édite, simule, approuve, exécute |
| LLM (Gemma 4) | Externe | Génère le JSON du workflow (serveur « chat completions » : Ollama, vLLM…) |
| Telegram Bot API | Externe | Envoi de messages |
| Gmail (SMTP) | Externe | Envoi d'e-mails |
| API HTTP tierces | Externe | Appelées par le bloc `http_request` |

## 4. Exigences fonctionnelles
| ID | Exigence |
|---|---|
| EF1 | Générer un workflow à partir d'un prompt en langage naturel |
| EF2 | Valider tout workflow (types de blocs, paramètres requis, liens, branches, déclencheur, cycles) |
| EF3 | Réparer automatiquement une sortie LLM invalide (≤ 2 tentatives) |
| EF4 | Afficher et éditer le workflow sous forme de graphe (ajout/suppression/paramètres) |
| EF5 | Simuler l'exécution (dry-run) : blocs à effet de bord non exécutés |
| EF6 | Exécuter réellement, uniquement avec `approved: true` |
| EF7 | Afficher le journal d'exécution par bloc (statut, sortie, erreur, durée) |

## 5. Exigences non fonctionnelles
| ID | Exigence | Mesure |
|---|---|---|
| ENF1 | Sécurité : aucune action externe sans approbation | Test `test_api_nodes_and_approval_gate` |
| ENF2 | Démo hors-ligne possible | `KERNEL_LLM_MOCK=1` |
| ENF3 | Extensibilité : ajouter un bloc = 1 enregistrement dans le registre | `nodes/registry.py` |
| ENF4 | Lancement reproductible en < 5 min | README |
| ENF5 | Secrets uniquement via variables d'environnement | `KERNEL_*` |

## 6. Contraintes
4 h, équipe réduite, Python 3.11+/FastAPI, React/Vite/React Flow, modèle Gemma 4 servi localement ou via API (nom exact du modèle **à vérifier** chez le fournisseur).

## 7. Sélection du MVP
| # | Fonctionnalité | Valeur | Démo | Faisabilité 4 h | Risque | Statut |
|---|---|---|---|---|---|---|
| F1 | Génération NL → workflow validé/réparé | ★★★ | ★★★ | Moyenne | LLM indisponible → mode mock | **Indispensable** |
| F2 | Éditeur visuel du workflow | ★★★ | ★★★ | Moyenne | Conversion graphe ↔ schéma | **Indispensable** |
| F3 | Simulation (dry-run) + journal | ★★☆ | ★★★ | Haute | Faible | **Indispensable** |
| F4 | Exécution réelle avec approbation (Telegram, Gmail, HTTP) | ★★★ | ★★☆ | Moyenne | Identifiants externes | **Indispensable** |

**Facultatif** : persistance des workflows (SQLite), historique des exécutions, harnais d'évaluation (`experiments/`).
**Exclu** : déclencheurs planifiés/webhooks, multi-utilisateur & authentification, OAuth Gmail, boucles, exécution asynchrone distribuée, marketplace de blocs.

## 8. Risques
| Risque | Impact | Parade |
|---|---|---|
| LLM non disponible le jour J | Démo bloquée | Mode mock (ENF2) + 503 explicite |
| LLM produit un JSON invalide | Workflow inutilisable | Validation + boucle de réparation (EF3) |
| Action réelle non voulue | Sécurité | Dry-run par défaut + garde `approved` |
| Identifiants Telegram/Gmail absents | Démo F4 partielle | Démo F4 en simulation, mention honnête |

## 9. Hypothèses à valider
- H1 : Gemma 4 suit un schéma JSON décrit dans le prompt système avec ≥ 1 réparation. → à mesurer (voir TESTING.md §4).
- H2 : 6 types de blocs suffisent pour une démo convaincante.
- H3 : un mot de passe d'application Gmail (SMTP) est acceptable pour un hackathon (pas pour un produit).
