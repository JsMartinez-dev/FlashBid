FROM python:3.11-slim

RUN pip install --no-cache-dir uv
WORKDIR /workspace
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev
COPY app/modules ./modules
COPY auth_service ./auth_service
ENV PYTHONPATH=/workspace
CMD ["uv", "run", "uvicorn", "auth_service.main:app", "--host", "0.0.0.0", "--port", "8000"]
