# Pipeline de recherche : régénère les données, réentraîne et réévalue le générateur local.
# Lancer depuis la racine du dépôt : docker compose --profile train run --rm trainer
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /repo
COPY backend/requirements.txt backend/requirements.txt
COPY experiments/requirements.txt experiments/requirements.txt
RUN pip install -r experiments/requirements.txt
# Le code est monté en volume (voir docker-compose.yml) pour que les résultats reviennent dans le dépôt.
CMD ["sh", "-c", "python experiments/build_dataset.py && python experiments/train.py"]
