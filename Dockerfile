# Imagen base: Python 3.11 slim
FROM python:3.11-slim

# Instalar Node.js, npm, curl y git (necesarios para AWS CDK)
RUN apt-get update && apt-get install -y \
    curl \
    git \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

RUN curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get update \
    && apt-get install -y nodejs \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Instalar AWS CDK y cdklocal globalmente
# - aws-cdk:        CLI de AWS CDK
# - aws-cdk-local:  wrapper que redirige cdklocal → emulador local (puerto 4566)
RUN npm install -g aws-cdk aws-cdk-local

# Directorio de trabajo para el código de la aplicación
WORKDIR /app

RUN pip install --no-cache-dir uv
WORKDIR /workspace
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen
WORKDIR /app

# Variables de entorno: credenciales dummy para el emulador
# (el emulador acepta cualquier valor; no se usan credenciales reales)
ENV AWS_ACCESS_KEY_ID=test
ENV AWS_SECRET_ACCESS_KEY=test
ENV AWS_DEFAULT_REGION=us-east-1
ENV PATH=/workspace/.venv/bin:$PATH
ENV UV_PROJECT_ENVIRONMENT=/workspace/.venv

# El contenedor queda en bash para desarrollo interactivo
CMD ["bash"]
