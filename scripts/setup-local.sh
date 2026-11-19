#!/usr/bin/env bash
set -euo pipefail

if [[ -f .env ]]; then
  set -a
  source .env
  set +a
fi

if ! command -v docker >/dev/null; then
  echo "Docker is required." >&2
  exit 1
fi

if ! docker compose version >/dev/null; then
  echo "Docker Compose is required." >&2
  exit 1
fi

docker compose up -d --build emulador redis cdk-dev

until docker compose exec -T cdk-dev curl -fsS http://emulador:4566/_localstack/health >/dev/null; do
  sleep 2
done

docker compose exec -T cdk-dev cdklocal bootstrap
docker compose exec -T cdk-dev cdklocal deploy --app "python infra/app.py" --require-approval never \
  --parameters JwtSecret="${JWT_SECRET:-flashbid-local-development-secret}"
api_url=$(docker compose exec -T cdk-dev aws cloudformation describe-stacks \
  --stack-name ProyectoFinalStack \
  --query "Stacks[0].Outputs[?OutputKey=='ApiUrl'].OutputValue" \
  --output text)
printf 'VITE_API_BASE_URL=%s\nVITE_AUTH_BASE_URL=http://localhost:8000\n' "$api_url" > frontend/.env.local
docker compose up -d --build auth frontend

echo "Frontend: http://localhost:5173"
echo "Identity API: http://localhost:8000/docs"
