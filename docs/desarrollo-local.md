# Desarrollo con DynamoDB Local

Este entorno es independiente del Compose serverless. Ejecuta FastAPI, DynamoDB Local, Redis y React sin CDK. Los datos no se copian automáticamente a LocalStack. La tabla y los índices se crean si no existen; no se elimina ni modifica una tabla existente.

## Inicio desde PowerShell

Desde `bd_no_sql`, detén el Compose serverless si ocupa los puertos 8000 o 5173:

```powershell
docker compose stop
docker compose -f docker-compose.local.yml up -d --build
docker compose -f docker-compose.local.yml ps
docker compose -f docker-compose.local.yml logs -f backend
```

Espera `Local table ready` y `Application startup complete`; Ctrl+C cierra el seguimiento de logs sin detener contenedores. La primera construcción puede descargar imágenes y paquetes. Este Compose crea su propio contenedor de DynamoDB, reutiliza la imagen `amazon/dynamodb-local:latest` y no usa automáticamente los datos de otro contenedor existente. Si hay conflictos de puerto 8002 o 6380, detén el contenedor anterior o configura `DYNAMODB_LOCAL_PORT` o `FLASHBID_REDIS_PORT`.

- Swagger API local: http://localhost:8000/docs
- Frontend: http://localhost:5173
- Salud de base y caché: http://localhost:8000/health
- DynamoDB desde el host: http://localhost:8002; Redis: puerto 6380.

En Swagger registra o inicia sesión, copia `session.accessToken`, pulsa **Authorize** e introduce el token sin `Bearer`. Prueba `/me`, movimientos, crear y cancelar subastas. Cancela antes de 120 segundos. El spec 05 añade catálogo y detalle autenticados; su validación fue informada por el usuario.

Los cambios Python montados se recargan por polling; Vite actualiza React. Tras cambios en dependencias Python, ejecuta `docker compose -f docker-compose.local.yml up -d --build backend`. Tras cambios en variables de Compose, ejecuta `docker compose -f docker-compose.local.yml up -d`.

Para detener sin borrar datos:

```powershell
docker compose -f docker-compose.local.yml down
```

Los volúmenes conservan datos entre reinicios normales. `down -v` elimina los volúmenes y sus datos. Para usar otra vez el entorno serverless detén el local antes de levantar el otro. El JWT usa la configuración `.env` si existe; cambia el secreto antes de compartirlo.

Las Lambdas y API Gateway no se ejecutan aquí: requieren validación separada en LocalStack. DynamoDB Local no reproduce exactamente TTL, consistencia, permisos y todos los comportamientos AWS; `expiresAt` sigue siendo la regla de vencimiento. Al cambiar el esquema, actualiza CDK e `init_db.py` y diseña la migración de tablas existentes.

## Worker de cierre

El Compose local incluye un servicio `worker`. Después de actualizar el Compose, ejecuta `docker compose -f docker-compose.local.yml up -d --build` y consulta sus logs con `docker compose -f docker-compose.local.yml logs -f worker`. El proceso reconcilia los vencimientos y procesa cierres automáticamente. Redis inaccesible puede retrasar la liquidación hasta su recuperación; no se habilitan pujas vencidas. La sección «Mis subastas ganadas» es simulada y no representa envíos.

## WebSocket del detalle

El backend local ofrece `ws://localhost:8000/ws/auctions/{id}`. Al abrir un detalle se autentica con la primera trama y se suscribe a eventos a través de Redis; si falla el canal, el cliente avisa y consulta el estado por HTTP. La implementación requiere probarse con dos sesiones y desconexiones. Para el Compose de LocalStack se configura un gateway local independiente en el puerto 8001; no sustituye la validación serverless pendiente.
