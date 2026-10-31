# API Kernel (FastAPI). Image unique pour le service et pour les tests (`pytest`).
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 \
    KERNEL_DB_PATH=/data/kernel.db
WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY pytest.ini .
COPY app ./app
COPY tests ./tests

# Utilisateur non root ; /data reçoit la base SQLite (volume).
RUN useradd --create-home --uid 10001 kernel && mkdir -p /data && chown kernel /data
USER kernel

EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=5 \
  CMD python -c "import urllib.request,sys; sys.exit(urllib.request.urlopen('http://127.0.0.1:8000/api/health').status != 200)"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
