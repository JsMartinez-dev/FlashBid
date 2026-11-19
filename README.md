<p align="center">
  <img src="frontend/public/Logo%20FlashBid%20con%20Pujas%20Ascendentes.png" alt="Logo de FlashBid" width="380" />
</p>

# FlashBid

FlashBid es una aplicación académica de subastas en línea con créditos virtuales. Permite publicar artículos, explorar subastas, hacer pujas y seguir su evolución en tiempo real. La aplicación reserva los créditos del participante que lidera, libera la reserva cuando otro usuario lo supera y liquida la subasta al finalizar.

Cada usuario puede consultar su perfil, billetera, movimientos, publicaciones, pujas y subastas ganadas. DynamoDB almacena las operaciones; Redis se utiliza para la caché del detalle, los vencimientos y los eventos en tiempo real.

## Tecnologías

| Tecnología | Uso en FlashBid |
|---|---|
| <img src="https://cdn.simpleicons.org/react/61DAFB" width="20" alt="" /> **React** y <img src="https://cdn.simpleicons.org/typescript/3178C6" width="20" alt="" /> **TypeScript** | Interfaz web y lógica del cliente. |
| <img src="https://cdn.simpleicons.org/vite/646CFF" width="20" alt="" /> **Vite** | Servidor y compilación del frontend. |
| <img src="https://cdn.simpleicons.org/python/3776AB" width="20" alt="" /> **Python** y <img src="https://cdn.simpleicons.org/fastapi/009688" width="20" alt="" /> **FastAPI** | API de desarrollo local y servicio de autenticación. |
| <img src="https://cdn.simpleicons.org/amazondynamodb/4053D6" width="20" alt="" /> **Amazon DynamoDB** | Tabla única para usuarios, subastas, pujas y movimientos. En desarrollo se usa DynamoDB Local o LocalStack. |
| <img src="https://cdn.simpleicons.org/redis/FF4438" width="20" alt="" /> **Redis** | Caché, Pub/Sub y seguimiento de vencimientos. |
| <img src="https://cdn.simpleicons.org/awslambda/FF9900" width="20" alt="" /> **AWS Lambda** y <img src="https://cdn.simpleicons.org/amazonapigateway/FF4F8B" width="20" alt="" /> **API Gateway** | Adaptadores y rutas HTTP de la arquitectura serverless emulada. |
| <img src="https://cdn.simpleicons.org/amazonwebservices/FF9900" width="20" alt="" /> **AWS CDK** | Definición de infraestructura y despliegue. |
| <img src="https://cdn.simpleicons.org/localstack/151515" width="20" alt="" /> **LocalStack** | Emulación de servicios de AWS. |
| <img src="https://cdn.simpleicons.org/docker/2496ED" width="20" alt="" /> **Docker Compose** | Ejecución de los entornos de desarrollo. |

## Requisitos

- Docker Desktop con Docker Compose y el motor de Docker en ejecución.
- Puertos **5173** y **8000** disponibles para ambos entornos. DynamoDB Local usa además **8002** y **6380**; LocalStack usa **4566**, **6379** y **8001**.
- PowerShell para los ejemplos. No hace falta instalar Python o Node.js en el equipo para usar los Compose.
- Internet para descargar imágenes y dependencias durante la primera construcción.

Ejecuta los comandos desde la carpeta que contiene `docker-compose.yml` y `docker-compose.local.yml`.

## Opción 1: desarrollo con DynamoDB Local

Este entorno inicia React, una API FastAPI con recarga de código, DynamoDB Local, Redis y el worker de cierre. El WebSocket forma parte de FastAPI. No requiere desplegar CDK.

1. Si el entorno de LocalStack está activo, detenlo para liberar los puertos:

   ```powershell
   docker compose down
   ```

2. Construye e inicia los servicios:

   ```powershell
   docker compose -f docker-compose.local.yml up -d --build
   ```

3. Comprueba que la API terminó de iniciar:

   ```powershell
   docker compose -f docker-compose.local.yml logs -f backend
   ```

   La salida debe incluir `Local table ready: FlashBidTable` y `Application startup complete`. Presiona `Ctrl+C` para dejar de ver los logs; los contenedores seguirán ejecutándose.

4. Abre el [frontend](http://localhost:5173) o el [Swagger de la API local](http://localhost:8000/docs).

La tabla se crea automáticamente al iniciar el backend si todavía no existe. Para agregar las subastas visuales de prueba:

```powershell
docker compose -f docker-compose.local.yml exec -T backend /workspace/.venv/bin/python /workspace/scripts/cargar_subastas_visuales.py
```

El script crea subastas con 20 horas de vigencia inicial y no sobrescribe las existentes. Al recibir una puja se aplican las reglas de vencimiento del proyecto.

Para detener el entorno conservando sus volúmenes:

```powershell
docker compose -f docker-compose.local.yml down
```

## Opción 2: LocalStack, API Gateway y Lambdas

Este entorno ejecuta API Gateway, DynamoDB y Lambdas en LocalStack. Autenticación, worker y WebSocket permanecen como servicios Docker independientes; Redis se comparte con ellos.

1. Detén primero el entorno de DynamoDB Local si está activo:

   ```powershell
   docker compose -f docker-compose.local.yml down
   ```

2. Construye e inicia los contenedores:

   ```powershell
   docker compose up -d --build
   ```

3. Inicializa los recursos de CDK en LocalStack:

   ```powershell
   docker compose exec cdk-dev cdklocal bootstrap
   ```

   El bootstrap se necesita la primera vez y cuando LocalStack pierde su estado. El aviso de que `cdklocal` está descontinuado no impide continuar con la herramienta instalada en este proyecto.

4. Despliega la infraestructura y las Lambdas:

   ```powershell
   docker compose exec cdk-dev cdklocal deploy --app "python infra/app.py" --parameters "JwtSecret=flashbid-local-development-secret"
   ```

   Si CDK solicita aprobación, escribe `y`. El empaquetado puede tardar varios minutos. Los archivos temporales de CDK se guardan en el volumen Docker `cdk_build_data` para evitar bloqueos en carpetas compartidas con Windows. Si configuraste `JWT_SECRET` en el archivo `.env` de Compose, usa ese mismo valor como parámetro `JwtSecret`; autenticación, WebSocket y Lambdas deben compartir secreto, emisor y audiencia.

5. Copia la salida `FlashBid.ApiUrl`. Crea o actualiza `frontend/.env.local` con esa URL, por ejemplo:

   ```dotenv
   VITE_API_BASE_URL=https://ID.execute-api.localhost.localstack.cloud:4566/prod/
   VITE_AUTH_BASE_URL=http://localhost:8000
   ```

   Sustituye la URL de ejemplo por la salida real. Si el archivo contiene `FLASHBID_API_PROXY_TARGET` o una URL de un despliegue anterior, revisa o elimina esa configuración para evitar apuntar a una API antigua. No subas secretos al repositorio.

6. Reinicia el frontend para aplicar la configuración:

   ```powershell
   docker compose restart frontend
   ```

7. Abre el [frontend](http://localhost:5173). El servicio `seed-localstack` espera a que CDK cree la tabla y carga las subastas de muestra sin sobrescribir las existentes. Comprueba el resultado con:

   ```powershell
   docker compose logs --tail 30 seed-localstack
   ```

Para detener este entorno:

```powershell
docker compose down
```

El proyecto monta `emulador-data` para LocalStack y un volumen para Redis. La disponibilidad del estado de LocalStack al reiniciar depende de su configuración y edición; comprueba la tabla y repite bootstrap y deploy si el emulador perdió sus recursos.

## Probar los endpoints

En DynamoDB Local, [http://localhost:8000/docs](http://localhost:8000/docs) documenta toda la API de FastAPI.

En LocalStack, [http://localhost:8000/docs](http://localhost:8000/docs) documenta únicamente autenticación. Para probar también las Lambdas, abre [http://localhost:5173/api-docs.html](http://localhost:5173/api-docs.html), pega `FlashBid.ApiUrl` y pulsa **Aplicar URL**. Inicia sesión con `POST /auth/login`, copia `session.accessToken` y pégalo en **Authorize**. Swagger necesita internet para cargar sus recursos. El WebSocket no se prueba desde Swagger.

Las rutas protegidas reciben `Authorization: Bearer <token>`. En una puja nueva usa un UUID distinto como `requestId`; reutilízalo únicamente para reintentar la misma solicitud.

## Estructura y documentación

- [app/modules](app/modules): servicios y repositorios compartidos por los adaptadores.
- [local_dev](local_dev): API y WebSocket del entorno local.
- [app/lambdas](app/lambdas) y [app/infra](app/infra): handlers Lambda e infraestructura CDK.
- [worker](worker): cierre y liquidación de subastas.
- [frontend](frontend): interfaz React.
- [Documento de diseño](entregable/entregables.md): patrones de acceso, tabla única, Lambdas y caché.
- [Especificaciones](docs/specs/README.md) y [patrones de acceso](docs/data/01_patrones_acceso.md): alcance funcional y diseño de datos.

Para compilar el frontend fuera de Docker, con Node.js instalado:

```powershell
cd frontend
npm install
npm run build
```
