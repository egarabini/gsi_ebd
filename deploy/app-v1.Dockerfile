# Imagem da v1. A imagem Reflex (deploy/Dockerfile) continua sendo a da v0.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app

WORKDIR /app

COPY requirements.txt ./
COPY v1/requirements.txt v1/requirements.txt
RUN pip install --no-cache-dir -r v1/requirements.txt

COPY gsi_ebd ./gsi_ebd
COPY rxconfig.py ./
COPY v1 ./v1
# Hash do conteudo no nome (logo-88.<hash>.webp). Trocar o arquivo troca a URL.
RUN python -m v1.landing_assets

EXPOSE 8000
CMD ["python", "-m", "uvicorn", "v1.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
