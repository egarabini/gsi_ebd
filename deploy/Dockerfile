# Didasko — imagem da aplicacao Reflex
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    REFLEX_HOST=0.0.0.0 \
    REFLEX_PORT=3000

# dependencias de sistema (build + node para o frontend do Reflex)
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl gnupg ca-certificates unzip \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 1. dependencias Python (camada cacheavel)
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# 2. codigo da aplicacao
COPY . .

# 3. build do frontend Reflex (gera .web) durante a imagem, para o start ser rapido.
#    O projeto ja tem a estrutura pronta, entao nao usamos 'reflex init'
#    (que sobrescreveria rxconfig.py e gsi_ebd.py).
RUN reflex export --frontend-only --no-zip 2>/dev/null || true

EXPOSE 3000

# Em producao o Reflex roda em modo producao servindo frontend + backend.
CMD ["reflex", "run", "--env", "prod", "--host", "0.0.0.0", "--port", "3000"]
