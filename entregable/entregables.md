# FlashBid — Documento de diseño

## Repositorio

[Repositorio de FlashBid en GitHub](https://github.com/JsMartinez-dev/FlashBid)

## Alcance y convenciones

FlashBid es un sistema académico de subastas con créditos virtuales. El entorno de desarrollo utiliza FastAPI, DynamoDB Local y Redis; la arquitectura serverless utiliza API Gateway, Lambda, DynamoDB emulado y Redis. La fuente de verdad para subastas y saldos es DynamoDB.

- `uid`: identificador del usuario autenticado; `aid`: identificador de subasta; `t`: fecha de creación o aceptación; `bidId`: identificador de puja.
- La API local usa como base `http://localhost:8000`. Las rutas de negocio requieren token Bearer salvo salud y autenticación.
- Las fechas de vencimiento de las subastas se expresan en milisegundos Unix; el atributo DynamoDB `ttl` se expresa en segundos Unix.
- Los GSI son eventualmente consistentes. Las decisiones de puja y cierre se comprueban en la tabla principal con condiciones transaccionales.

## 1. Patrones de acceso identificados

La siguiente tabla se copia de [01_patrones_acceso.md](../docs/data/01_patrones_acceso.md). Mantiene las propuestas y la numeración de ese documento; las precisiones posteriores sobre el código actual se señalan después de la tabla.

| # | Vista / proceso | Patrón de acceso (¿qué pregunta responde?) | Entidad | PK | SK | Índice | GSI PK | GSI SK | Frecuencia | Operación | Datos / regla | Casos de uso |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| PA-01 | Mi perfil | ¿Cuál es mi perfil? | Usuario | USER#uid | PROFILE | Tabla | — | — | Alta | GetItem fuerte | email, displayName, createdAt; nunca contraseña | CU-02-03 |
| PA-02 | Registro | ¿Existe el perfil y cómo lo creo sin duplicarlo? | Usuario | USER#uid | PROFILE | Tabla | — | — | Por registro | Put condicional | uid del proveedor; condición de inexistencia; reintento recupera perfil | CU-02-01 |
| PA-03 | Billetera | ¿Cuánto tengo disponible y reservado? | Billetera | USER#uid | WALLET | Tabla | — | — | Alta | GetItem fuerte | availableCredits, reservedCredits, version, initializedAt | CU-03-02 |
| PA-04 | Billetera | ¿Cómo acredito 10.000 créditos una sola vez? | Billetera + movimiento | USER#uid | WALLET y MOVEMENT#t#INITIAL | Tabla | — | — | Una vez por cuenta | TransactWriteItems | Put condicional de billetera y movimiento INITIAL_CREDIT; sin saldo previo sobrescrito | CU-03-01 |
| PA-05 | Billetera | ¿Cuáles son mis movimientos recientes? | Movimiento | USER#uid | begins_with MOVEMENT# | Tabla | — | — | Alta | Query descendente fuerte | tipo, importe, deltas disponible/reservado, auctionId, relatedUserId, operationId, fecha | CU-03-02 |
| PA-06 | Publicar | ¿Cómo guardo una subasta  nueva? | Subasta | AUCTION#aid | META | Tabla; alimenta GSI1/2 | Ver índices | Ver índices | Por publicación | PutItem condicional | sellerId, campos de producto, precio, estado, version, fechas, expiresAt, ttl e índices | CU-04-01 |
| PA-07 | Mis subastas | ¿Puedo cancelar esta publicación? | Subasta | AUCTION#aid | META | Tabla | — | — | Por cancelación | GetItem fuerte + Update condicionado | sellerId propio, ACTIVE_NO_BIDS, version y now<expiresAt; CANCELLED, cancelledAt; quitar GSI1 y ttl | CU-04-02 |
| PA-08 | Explorar | ¿Cuáles son las subastas activas más recientes? | Subasta | AUCTION#aid | META | GSI1 | AUCTIONS#ACTIVE | createdAt#aid | Alta | Query descendente + validación base | Tarjetas: título, imagen, precio, highestBid, leaderAlias, expiresAt, estado; excluir expiradas | CU-05-01 |
| PA-09 | Detalle | ¿Cuál es el estado público vigente de esta subasta? | Subasta | AUCTION#aid | META | Tabla | — | — | Muy alta | Cache-Aside / GetItem fuerte | Snapshot público, sellerAlias, líder, precio, estado, version, expiresAt y serverNow | CU-05-02 |
| PA-10 | Expiración | ¿Debo ocultarla aunque TTL no la haya borrado? | Subasta | AUCTION#aid | META | Tabla | — | — | Cada lectura/operación | Validación sobre registro leído | ACTIVE_NO_BIDS y now>=expiresAt: invisible; ttl solo limpieza asíncrona | CU-05-03 |
| PA-11 | Pujar | ¿Sigue abierta y cuál es la oferta que debo superar? | Subasta | AUCTION#aid | META | Tabla | — | — | Cada intento | GetItem fuerte | sellerId, leaderId, highestBid, initialPrice, status, expiresAt, version | CU-06-01, CU-06-02 |
| PA-12 | Pujar | ¿Qué saldos pueden reservarse y liberarse? | Billeteras | USER#nuevo y USER#anterior | WALLET | Tabla | — | — | Cada intento | GetItem fuerte / TransactGetItems | Disponible y reservado de participantes; condiciones de saldo/version en escritura posterior | CU-06-01, CU-06-02 |
| PA-13 | Pujar | ¿Cómo acepto la primera oferta de forma atómica? | Subasta + billetera + puja + movimiento + request | Varias; ver TX-02 | Varias; ver TX-02 | Tabla; GSI1/2/3/4 | Ver índices | Ver índices | Por primera puja | TransactWriteItems | Reservar monto, quitar ttl, ACTIVE_BIDDING, líder y expiresAt=now+20s; auditoría e idempotencia | CU-06-01 |
| PA-14 | Pujar | ¿Cómo reemplazo al líder sin perder créditos? | Subasta + billeteras + puja + movimientos + request | Varias; ver TX-03 | Varias; ver TX-03 | Tabla; GSI1/2/3/4 | Ver índices | Ver índices | Por puja aceptada | TransactWriteItems | Liberar anterior, reservar nuevo, cambiar líder/version/vencimiento, registrar ambas operaciones | CU-06-02 |
| PA-15 | Pujar | ¿Ya se procesó este requestId? | Idempotencia | USER#uid | REQUEST#requestId | Tabla | — | — | Cada reintento | GetItem fuerte; Put en transacción | payloadHash, auctionId, bidId, result, acceptedAt, ttl independiente; cuerpo distinto da conflicto | CU-06-03 |
| PA-16 | Detalle | ¿Qué ofertas fueron aceptadas en esta subasta? | Puja | AUCTION#aid | begins_with BID# | Tabla | — | — | Alta | Query descendente fuerte | bidId, alias público, amount, acceptedAt; no exponer requestId ni identidad privada | CU-06-04 |
| PA-17 | Worker | ¿Qué subastas con pujas deben recuperarse o vencer? | Subasta | AUCTION#aid | META | GSI3 | AUCTIONS#ACTIVE_BIDDING | expiresAtMs#aid | Periódica y al reiniciar | Query ascendente paginada | Consultar todas al reconstruir; rango hasta now para pendientes; releer base antes del cierre | CU-07-01, CU-07-03 |
| PA-18 | Worker | ¿Es válido cerrar este deadline? | Subasta | AUCTION#aid | META | Tabla | — | — | Por deadline | GetItem fuerte | ACTIVE_BIDDING, expiresAt<=now, version, líder e importe; si prorrogada reparar score | CU-07-01 |
| PA-19 | Liquidación | ¿Cómo registro ganador y transfiero solo una vez? | Subasta + billeteras + movimientos + victoria | Varias; ver TX-04 | Varias; ver TX-04 | Tabla; retira GSI1/3 | Ver índices | Ver índices | Una vez por cierre | TransactWriteItems | FINISHED, winnerUserId, winningBidId, winningAmount, settlementId, finishedAt; crédito al vendedor | CU-07-02 |
| PA-20 | Mis subastas | ¿Qué publicaciones son mías? | Subasta | AUCTION#aid | META | GSI2 | SELLER#uid | createdAt#aid | Media | Query descendente + validación base | Estado, título, imagen, precio, líder, vencimiento y resultado; canceladas retenidas | CU-09-01 |
| PA-21 | Mis pujas | ¿En qué subastas he ofertado y cuánto? | Puja | AUCTION#aid | BID#t#bidId | GSI4 | BIDDER#uid | acceptedAt#bidId | Media | Query descendente + BatchGetItem de META | Historial propio; ofertas repetidas son filas distintas; resultado actual se obtiene de META | CU-09-02 |
| PA-22 | Mis victorias | ¿Cuáles subastas gané y por qué monto? | Victoria | USER#uid | begins_with WON# | Tabla | — | — | Media | Query descendente fuerte | auctionId, winningBidId, winningAmount, finishedAt, sellerId y título/imagen de referencia | CU-09-03 |
| PA-23 | Reconexión | ¿Qué cambió mientras estuve desconectado? | Subasta + billetera + pujas | AUCTION#aid y USER#uid | META, WALLET y BID# | Tabla | — | — | Por reconexión | Reutiliza detalle, billetera e historial | Snapshot/version autoritativo, serverNow y estado final; HTTP recupera eventos perdidos | CU-08-03 |


### Lambda o proceso asociado a cada patrón

La tabla refleja los adaptadores definidos en el código y CDK. La identidad, el worker y el servidor WebSocket se ejecutan como servicios Docker; no son Lambdas en la configuración actual. Los patrones también pueden ejecutarse desde el adaptador FastAPI del entorno con DynamoDB Local.

| Patrón | Lambda o proceso responsable | Ruta o responsabilidad |
|---|---|---|
| PA-01 | `UsersHandler` | `GET /me`: lee el perfil autenticado. |
| PA-02 | Servicio `auth` (FastAPI) | `POST /auth/register`: crea la identidad y el perfil; no usa Lambda. |
| PA-03 | `UsersHandler` | `GET /me`: consulta la billetera junto con el perfil. |
| PA-04 | `UsersHandler` | `GET /me`: inicializa la billetera de manera idempotente si aún no existe. |
| PA-05 | `WalletHandler` | `GET /me/wallet/movements`: consulta los movimientos. |
| PA-06 | `AuctionsHandler` | `POST /auctions`: publica la subasta. |
| PA-07 | `AuctionsHandler` | `DELETE /auctions/{id}`: cancela una subasta propia si cumple las condiciones. |
| PA-08 | `AuctionsHandler` | `GET /auctions`: consulta el catálogo activo. |
| PA-09 | `AuctionsHandler` | `GET /auctions/{id}`: lee el detalle mediante Cache-Aside. |
| PA-10 | `AuctionsHandler` | `GET /auctions` y `GET /auctions/{id}`: valida la visibilidad y el vencimiento. |
| PA-11 | `BidsHandler` | `POST /auctions/{id}/bids`: comprueba el estado y precio de la subasta. |
| PA-12 | `BidsHandler` | La operación de puja valida y actualiza las billeteras implicadas. |
| PA-13 | `BidsHandler` | Registra la primera puja y la reserva en una transacción. |
| PA-14 | `BidsHandler` | Registra la puja que supera al líder y libera la reserva anterior. |
| PA-15 | `BidsHandler` | Comprueba y registra la idempotencia de la solicitud. |
| PA-16 | `BidsHandler` | `GET /auctions/{id}/bids`: consulta el historial de pujas. |
| PA-17 | Servicio `worker` | Reconcilia las subastas con pujas y sus vencimientos; no usa Lambda. |
| PA-18 | Servicio `worker` | Comprueba la subasta antes de cerrar el vencimiento. |
| PA-19 | Servicio `worker` | Ejecuta la liquidación, los movimientos y el registro de victoria. |
| PA-20 | `ActivityHandler` | `GET /me/auctions`: consulta las publicaciones propias. |
| PA-21 | `ActivityHandler` | `GET /me/bids`: consulta la participación más reciente por subasta. |
| PA-22 | `WalletHandler` | `GET /me/wins`: consulta las victorias del usuario. |
| PA-23 | Servicio `websocket`; `AuctionsHandler`, `BidsHandler` y `UsersHandler` | WebSocket comunica eventos; al reconectar se recuperan detalle, historial y billetera mediante HTTP. |

Los handlers están en [app/lambdas](../app/lambdas) y su asociación con API Gateway en [app/infra/stack.py](../app/infra/stack.py). La existencia de estos adaptadores no implica que un despliegue concreto haya sido validado.

### Endpoint local asociado a cada patrón

La dirección base es `http://localhost:8000`. `{auction_id}` representa el ID de la subasta. Los patrones de trabajo interno no tienen una ruta HTTP pública propia.

| Patrón | Endpoint local o proceso que lo cumple | Función |
|---|---|---|
| PA-01 | GET `/me` | Lee el perfil asociado al token. |
| PA-02 | POST `/auth/register` | Crea identidad y perfil; el correo se verifica con una clave de identidad. |
| PA-03 | GET `/me` | Consulta los saldos del usuario. |
| PA-04 | GET `/me` | Garantiza de forma idempotente la billetera inicial y su movimiento. |
| PA-05 | GET `/me/wallet/movements` | Lista movimientos propios con paginación. |
| PA-06 | POST `/auctions` | Publica una subasta. |
| PA-07 | DELETE `/auctions/{auction_id}` | Cancela solo si el solicitante es el vendedor y aún no hay pujas. |
| PA-08 | GET `/auctions` | Consulta el catálogo activo paginado. |
| PA-09 | GET `/auctions/{auction_id}` | Consulta el detalle; puede leer la instantánea desde Redis. |
| PA-10 | GET `/auctions` y GET `/auctions/{auction_id}` | Excluyen publicaciones sin pujas vencidas; el detalle de una con pujas vencida puede responder `FINALIZING`. |
| PA-11 | POST `/auctions/{auction_id}/bids` | Lee el estado de la subasta para validar la puja. |
| PA-12 | POST `/auctions/{auction_id}/bids` | Valida saldo y aplica condiciones en la transacción. |
| PA-13 | POST `/auctions/{auction_id}/bids` | Registra la primera puja y la reserva. |
| PA-14 | POST `/auctions/{auction_id}/bids` | Registra la nueva puja, reserva y liberación. |
| PA-15 | POST `/auctions/{auction_id}/bids` | Consulta y guarda el registro de idempotencia. |
| PA-16 | GET `/auctions/{auction_id}/bids` | Consulta las pujas aceptadas de la subasta. |
| PA-17 | Sin endpoint HTTP: worker interno | Reconcilia y consulta vencimientos de subastas con pujas. |
| PA-18 | Sin endpoint HTTP: worker interno | Comprueba el estado autoritativo antes de cerrar. |
| PA-19 | Sin endpoint HTTP: worker interno | Ejecuta la liquidación y registra la victoria. |
| PA-20 | GET `/me/auctions` | Consulta publicaciones del vendedor mediante GSI2. |
| PA-21 | GET `/me/bids` | Consulta una participación por subasta; GSI4 se usa para recuperar pujas anteriores. |
| PA-22 | GET `/me/wins` | Consulta victorias propias. |
| PA-23 | WS `/ws/auctions/{auction_id}` y GET de detalle, historial y datos propios | Tras reconexión, el cliente solicita datos actuales por HTTP. |

## 2. Modelo de tabla — Single Table Design

La tabla `FlashBidTable` usa una clave de partición `PK` y una clave de ordenamiento `SK`, ambas de tipo cadena. Los distintos tipos de registro comparten la misma tabla; el prefijo de las claves identifica cada entidad.

| Entidad | PK | SK | Información almacenada | Uso |
|---|---|---|---|---|
| Perfil | `USER#uid` | `PROFILE` | Identificador, correo, nombre y fecha de creación | Perfil autenticado y publicación de subastas. |
| Identidad local | `IDENTITY#email` | `PROFILE` | uid y hash de contraseña, entre otros datos de identidad | Inicio de sesión y unicidad del correo. El hash no se devuelve al cliente. |
| Billetera | `USER#uid` | `WALLET` | Créditos disponibles, reservados, versión e inicialización | Saldos y reservas; 10.000 créditos iniciales una sola vez. |
| Movimiento | `USER#uid` | `MOVEMENT#t#id` | Tipo, monto, cambios de saldo, fecha y operación relacionada | Auditoría de crédito inicial, reserva, liberación, compra y venta. |
| Subasta | `AUCTION#aid` | `META` | Vendedor, producto, imagen, precio, estado, versión, vencimiento, líder y resultado | Publicación, catálogo, detalle y cierre. El producto se almacena en el registro de subasta. |
| Puja | `AUCTION#aid` | `BID#t#bidId` | Participante, alias, monto, fecha, requestId y claves de índice | Historial inmutable de ofertas aceptadas. |
| Idempotencia | `USER#uid` | `REQUEST#requestId` | Hash del cuerpo, subasta, resultado serializado y TTL | Evita procesar dos veces la misma solicitud durante el período de retención. |
| Participación | `USER#uid` | `PARTICIPATION#aid` | ID y monto de la última puja, fecha y versión de subasta | Una fila por subasta en “Mis pujas”. |
| Control de migración | `USER#uid` | `MIGRATION#PARTICIPATIONS_V1` | Marcador de recuperación inicial de participaciones | Señala que se recorrió GSI4 para recuperar registros anteriores. |
| Victoria | `USER#uid` | `WON#t#aid` | Subasta, producto, monto, puja ganadora, fecha e identificador de liquidación | Vista “Mis subastas ganadas”. |

La tabla configura `ttl` para la limpieza de registros que lo contengan. Una publicación sin pujas usa TTL; al recibir la primera puja se retira de la subasta. El registro `REQUEST` tiene un TTL independiente de siete días. **TTL no es un cronómetro exacto**: el backend comprueba `expiresAt` y no espera el borrado físico para impedir una puja vencida.

### Índices secundarios globales

| Índice | GSI PK | GSI SK | Proyección | Patrón principal |
|---|---|---|---|---|
| GSI1 | `AUCTIONS#ACTIVE` | `createdAt#aid` | `KEYS_ONLY` | Localizar subastas para el catálogo. |
| GSI2 | `SELLER#uid` | `createdAt#aid` | `KEYS_ONLY` | Localizar publicaciones de un vendedor. |
| GSI3 | `AUCTIONS#ACTIVE_BIDDING` | `expiresAtMs#aid` | `KEYS_ONLY` | Reconstruir vencimientos de subastas con pujas para el worker. |
| GSI4 | `BIDDER#uid` | `acceptedAt#bidId` | `INCLUDE`: `amount`, `acceptedAt`, `bidId` | Localizar ofertas del participante y recuperar participaciones anteriores. |

### Transacciones mencionadas en los patrones

| Referencia | Operación | Registros modificados |
|---|---|---|
| TX-01 | Inicializar billetera | Billetera y movimiento de crédito inicial, con condiciones de inexistencia. |
| TX-02 | Primera puja | Subasta, billetera del participante, puja, participación, movimiento y solicitud idempotente. |
| TX-03 | Puja que supera al líder | Los registros de TX-02 más la billetera y el movimiento de liberación del líder anterior. |
| TX-04 | Cierre y liquidación | Subasta, billeteras del ganador y vendedor, movimientos de compra y venta, y registro de victoria. |
| TX-05 | Cancelación | Actualización condicionada del registro de subasta; es una escritura de un solo ítem. |

La primera oferta aceptada debe ser un entero positivo **superior** al precio inicial y el líder no puede superarse a sí mismo. Estas reglas confirmadas prevalecen sobre las propuestas anteriores del documento de patrones.

## 3. Patrón de caché elegido: Cache-Aside

Se eligió **Cache-Aside** para el detalle de las subastas porque permite acelerar lecturas repetidas sin convertir a Redis en la fuente de verdad. El backend administra la caché explícitamente:

1. Ante `GET /auctions/{auction_id}`, busca una instantánea pública en Redis.
2. Si existe y sigue siendo visible, la devuelve.
3. Si no existe o no sirve, lee la subasta en DynamoDB y, si corresponde, guarda una instantánea en Redis.
4. Después de una puja, cancelación o cierre confirmado, invalida la instantánea.

El TTL de la instantánea es configurable mediante `AUCTION_CACHE_TTL` y su valor por defecto es **3 segundos**. Una clave de generación y una comparación al escribir ayudan a evitar que una lectura iniciada antes de una invalidación exitosa reponga después una instantánea antigua. Si Redis no responde, se intenta leer DynamoDB; si falla una invalidación, puede mostrarse una instantánea desactualizada hasta que expire su TTL.


### Archivos de implementación

| Archivo | Responsabilidad |
|---|---|
| [app/modules/auctions/service.py](../app/modules/auctions/service.py) | `AuctionService.detail()` coordina la lectura Cache-Aside y verifica la visibilidad. |
| [app/modules/shared/auction_cache.py](../app/modules/shared/auction_cache.py) | Lectura, escritura, TTL, generación e invalidación de la instantánea en Redis. |
| [app/modules/auctions/repository.py](../app/modules/auctions/repository.py) | Lee y proyecta los registros de subasta desde DynamoDB. |
| [app/modules/bids/service.py](../app/modules/bids/service.py) y [app/modules/settlement/service.py](../app/modules/settlement/service.py) | Invalidan el detalle tras confirmar una puja o liquidación. |

El Sorted Set `auctions:deadlines` y Redis Pub/Sub son otros usos de Redis: ayudan al worker y a las notificaciones WebSocket, respectivamente. Son complementarios al patrón de caché del detalle.
