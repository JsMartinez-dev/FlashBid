# FlashBid

Marketplace académico de subastas virtuales. DynamoDB es la fuente de verdad, Redis acelera lecturas y el entorno local usa LocalStack, CDK, FastAPI y React.

## Estado actual

Los specs 01 a 04 están implementados y en validación integrada:

- Entorno Docker reproducible para LocalStack, Redis, CDK, el adaptador FastAPI de identidad y React.
- Tabla única `FlashBidTable`, TTL y los GSI previstos para catálogo, vendedor, vencimientos y pujas propias.
- Registro, inicio y cierre de sesión con JWT local; perfil persistido en DynamoDB y `GET /me` protegido.
- Pantalla React con salud, registro, inicio de sesión, perfil y cierre de sesión.
- Health check integrado para DynamoDB y Redis.

- Billetera inicial de 10.000 créditos e historial paginado de movimientos.
- Publicación de productos ficticios de 120 segundos y cancelación condicionada antes de la primera puja.

El adaptador local de identidad sustituye Cognito durante los primeros incrementos. La razón y el contrato están en [ADR 001](docs/adr/001-local-identity-and-emulation.md). WebSocket se implementará en el spec 08.

## Requisitos

- Docker Engine con Docker Compose.
- `uv` para pruebas locales.
- Node.js 22 o superior solo si se ejecuta el frontend fuera de Docker.

## Inicio local

1. Copia `.env.example` a `.env` y cambia `JWT_SECRET` por un secreto largo y único si compartes el entorno.
2. Ejecuta `./scripts/setup-local.sh`.
3. Abre `http://localhost:5173`.

El script espera los healthchecks, ejecuta `cdklocal bootstrap` y `deploy`, genera `frontend/.env.local` con el endpoint dinámico de API Gateway y luego inicia FastAPI y React. Se puede repetir sin duplicar recursos.

Dentro del contenedor de desarrollo también funcionan los comandos directos `cdklocal synth` y `cdklocal deploy`; comparten el mismo proyecto `uv` que la ejecución local.

Servicios locales:

- React: `http://localhost:5173`
- Identidad FastAPI y documentación OpenAPI: `http://localhost:8000/docs`
- LocalStack: `http://localhost:4566`
- Redis: `localhost:6379`

Para detener el entorno usa `docker compose down`. Para borrar voluntariamente sus datos locales usa `docker compose down -v` y elimina `emulador-data/`.

## Desarrollo y verificación

```bash
uv sync --all-groups
uv run pytest -q
cd frontend && npm install && npm run build
cd app && npx aws-cdk synth
```

Las pruebas unitarias no requieren Docker: usan Moto para DynamoDB y fakeredis para Redis. El gestor de paquetes Python del proyecto es `uv`; los archivos `app/requirements.txt` y `app/layers/dependencias/requirements.txt` permanecen para el empaquetado de Lambdas.

## Seguridad y contratos

Las rutas protegidas reciben `Authorization: Bearer <token>`. El backend valida firma, emisor, audiencia y expiración; no acepta un `userId` indicado por el cliente. El secreto JWT se pasa al despliegue como parámetro CloudFormation `NoEcho`, no se guarda en la plantilla. Los errores no revelan hash de contraseña, saldos ni tokens.

Las decisiones de claves, TTL, índices, consultas y restricciones contra `Scan` están en [patrones de acceso](docs/data/01_patrones_acceso.md) y [ADR 002](docs/adr/002-access-patterns-and-time.md).

