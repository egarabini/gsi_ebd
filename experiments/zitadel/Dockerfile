FROM python:3.12-slim
WORKDIR /app
COPY experiments/zitadel/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY experiments/identity_client /app/identity_client
USER 10001:10001
CMD ["uvicorn", "identity_client.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--no-access-log", "--no-proxy-headers"]
