# Kernel

Plateforme d'automatisation : on décrit un besoin en langage naturel, Gemma 4 génère un workflow visuel que l'on peut modifier, simuler puis exécuter après validation.

## Lancer le projet

Backend (terminal 1) :

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export KERNEL_LLM_MOCK=1          # démo hors-ligne, sans modèle
uvicorn app.main:app --reload     # http://127.0.0.1:8000
```

Frontend (terminal 2) :

```bash
cd frontend
npm install
npm run dev                       # http://localhost:5173 (proxy /api vers le backend)
```

Tests : `cd backend && python -m pytest`.

## Brancher Gemma 4

Le client (`backend/app/ai/llm.py`) parle à n'importe quel serveur au format « chat completions » (Ollama, vLLM, llama.cpp, fournisseur cloud) :

```bash
export KERNEL_LLM_BASE_URL=http://localhost:11434/v1
export KERNEL_LLM_MODEL=<nom exact du modèle chez votre fournisseur>   # à vérifier
export KERNEL_LLM_API_KEY=...                                          # si nécessaire
```

## Générateur local (hors-ligne, sans Gemma)

```bash
export KERNEL_LLM_LOCAL=1   # classifieur entraîné : le workflow dépend du prompt (14 structures)
```

Exactitude mesurée : 0,93 sur 42 prompts rédigés à la main (IC 95 % 0,83–1,00). Détails, données et protocole : [`experiments/`](experiments/README.md).

## Connecteurs

- Telegram : `KERNEL_TELEGRAM_TOKEN` (token du bot).
- Gmail : `KERNEL_GMAIL_USER` et `KERNEL_GMAIL_APP_PASSWORD` (mot de passe d'application Google, SMTP). Raccourci de hackathon ; un vrai produit utiliserait OAuth 2.0.

## Architecture

- `backend/app/schemas.py` : format de workflow (source de vérité).
- `backend/app/nodes/` : registre de blocs. Un bloc = un schéma de paramètres + une fonction d'exécution ; le même schéma alimente le prompt de Gemma 4 et le formulaire de l'éditeur.
- `backend/app/engine.py` : validation (types, paramètres, cycles, branches) et exécution (tri topologique, gabarits `{{bloc.champ}}`, aiguillage des conditions).
- `backend/app/ai/generator.py` : prompt → JSON → validation → réparation (2 tentatives).
- `frontend/src/convert.js` : conversion schéma Kernel ↔ React Flow, disposition automatique avec dagre.

## Contrôle humain

- `POST /api/run` est en simulation par défaut : les blocs à effet de bord (HTTP, LLM, Telegram, Gmail) ne sont pas exécutés.
- Une exécution réelle est refusée par l'API sans `approved: true`, et l'interface demande une confirmation.

## Pour la partie recherche

Pipeline d'entraînement et d'évaluation du générateur local : [`experiments/`](experiments/README.md). L'évaluation de Gemma 4 reste à faire : jeu de prompts annotés, puis mesure de validité du schéma, d'exécutabilité et de correction sémantique, avec et sans validation/réparation (`generator.MAX_REPAIRS` = 0, 1, 2).
