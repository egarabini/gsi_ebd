# Didasko — imagem da aplicacao Reflex
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1
# NOTA: REFLEX_HOST/REFLEX_PORT nao existem — o host e a porta sao definidos no
# comando (--backend-host, --frontend-port, --backend-port, --single-port).

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

# --single-port faz frontend e backend responderem na MESMA porta (3000), que e
# o que o Traefik precisa para rotear o dominio para um unico alvo.
# ATENCAO: nao usar --host/--port (nao existem nesta versao do Reflex; o CLI
# responde "No such option '--host'"). As opcoes validas sao --backend-host,
# --frontend-port, --backend-port e --single-port.
CMD ["reflex", "run", "--env", "prod", "--single-port", "--backend-host", "0.0.0.0", "--frontend-port", "3000"]
