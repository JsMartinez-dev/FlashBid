# 01 Patrones de acceso — FlashBid MVP 1

## Convenciones

- Una tabla `FlashBidTable`, claves string `PK` y `SK`. `uid` viene del token validado; `aid`, `bidId` y `requestId` son identificadores. Los prefijos son literales; lo que sigue a `#` se sustituye por el valor.
- `t`, `createdAt` y `acceptedAt` en claves ordenables: UTC ISO 8601 con milisegundos y formato fijo. `expiresAt` se propone en milisegundos Unix para HTTP/Redis y `expiresAtMs` en la clave GSI3 con ancho fijo de 13 dígitos. `ttl=floor(expiresAt/1000)` en segundos Unix. Esta convención concreta debe registrarse en ADR y aplicarse uniformemente.
- Importes: enteros positivos; disponible y reservado nunca negativos. `version` aumenta en cada mutación de subasta/billetera. Cada comando captura el reloj del servidor y verifica el vencimiento; el cliente no decide tiempos ni ganador.
- Las claves indicadas en una Query expresan condiciones, no un ítem literal. `—` significa que no aplica GSI. Los GSI son eventualmente consistentes; ninguna validación financiera depende de ellos.
- Accesos privados siempre restringidos al uid autenticado. Las respuestas públicas omiten emails, saldos ajenos, tokens y requestId. Credenciales y sesiones corresponden al proveedor de identidad, no a la tabla de negocio.

## Tabla principal de accesos DynamoDB

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

## Datos que se almacenan

Los campos listados complementan PK/SK. Un producto ficticio vive dentro de META; no requiere otra entidad. Las imágenes son URLs, no binarios. Los atributos opcionales se omiten hasta que existan.

| Entidad | Clave | Información mínima persistida | Retención / actualización |
|---|---|---|---|
| Usuario | USER#uid / PROFILE | uid, email, displayName, createdAt | Sin TTL; email no se usa como identidad autorizada |
| Billetera | USER#uid / WALLET | availableCredits, reservedCredits, version, initializedAt | Sin TTL; inicialización única |
| Movimiento | USER#uid / MOVEMENT#t#id | type, amount, availableDelta, reservedDelta, auctionId opcional, relatedUserId opcional, operationId, createdAt | Inmutable, sin TTL; tipos INITIAL_CREDIT, RESERVE, RELEASE, PURCHASE, SALE |
| Subasta | AUCTION#aid / META | auctionId, sellerId, sellerAlias, title, description, category, imageUrl, initialPrice, status, version, createdAt, expiresAt; tras oferta: leaderId, leaderAlias, highestBid, highestBidId; tras cierre: winnerUserId, winningBidId, winningAmount, finishedAt, settlementId; cancelledAt cuando aplique; claves GSI | TTL solo mientras ACTIVE_NO_BIDS; eliminar ttl al pujar o cancelar; conservar finalizadas/canceladas |
| Puja | AUCTION#aid / BID#t#bidId | bidId, userId, publicAlias, amount, requestId, acceptedAt, GSI4PK, GSI4SK | Inmutable, sin TTL; cada oferta aceptada es un ítem |
| Idempotencia | USER#uid / REQUEST#requestId | auctionId, payloadHash, bidId, acceptedAt, result seguro, ttl | Put junto con puja; propuesta: ventana de 7 días, documentar antes de implementar |
| Victoria | USER#uid / WON#t#aid | auctionId, winningBidId, winningAmount, finishedAt, settlementId, sellerId, title, imageUrl | Put en liquidación; sin TTL; copia mínima para consulta propia |

`operationId` enlaza movimientos de una misma transacción (bidId o settlementId). Los deltas permiten auditar: reserva (-m,+m), liberación (+m,-m), compra (0,-m), venta (+m,0), inicial (+10000,0). El saldo de WALLET es autoritativo; no reconstruirlo sumando todo el historial en cada pantalla. Los alias/título copiados son snapshots; editar perfiles/productos no pertenece al alcance actual.

## Índices propuestos y mantenimiento

Se proponen **cuatro GSI**, separando consultas con orden distinto. Es una decisión de diseño de este documento para llevar a ADR/CDK, no una decisión previamente aprobada ni infraestructura ya desplegada. Se usa WON en tabla principal para evitar un quinto índice. Las claves GSI son dispersas: únicamente existen en los tipos indicados.

| Índice | Tipo indexado | Atributos y valores | Proyección propuesta | Cuándo agregar, actualizar o retirar |
|---|---|---|---|---|
| GSI1 | META activa | GSI1PK=AUCTIONS#ACTIVE; GSI1SK=createdAt#aid | KEYS_ONLY | Publicar: agregar. Pujar: conservar. Cancelar/finalizar: quitar. Sin pujas vencida: excluir lógicamente hasta limpieza TTL |
| GSI2 | Toda META | GSI2PK=SELLER#uid; GSI2SK=createdAt#aid | KEYS_ONLY | Publicar: agregar; conservar hasta eliminación del ítem |
| GSI3 | META con pujas activa | GSI3PK=AUCTIONS#ACTIVE_BIDDING; GSI3SK=expiresAtMs#aid | KEYS_ONLY | Primera puja: agregar; siguiente: actualizar vencimiento; cierre: quitar |
| GSI4 | BID | GSI4PK=BIDDER#uid; GSI4SK=acceptedAt#bidId | INCLUDE: amount, acceptedAt, bidId | Agregar dentro del Put de puja; inmutable |

Con KEYS_ONLY se obtienen PK/SK y se hidratan por BatchGetItem con lectura fuerte, reordenando según el índice; reintentar UnprocessedKeys. Esto evita mostrar estado viejo proyectado, pero no elimina la demora en que un nuevo ítem aparece en un GSI. El worker repite reconciliación periódicamente por esa razón. GSI4 ya trae el importe; META completa el resultado vigente de cada subasta. Ningún GSI soporta lectura fuerte.

**Paginación propuesta:** 20 resultados por defecto, máximo 50, cursor opaco validado ligado a identidad/consulta. Query descendente para historiales y catálogo; ascendente para deadlines. Excluir vencidas/canceladas después de hidratar. Avanzar usando LastEvaluatedKey real, no el último resultado visible; una página vacía puede tener continuación. Limitar trabajo por petición y permitir continuar. Para recoger todos los deadlines, recorrer todas las páginas. No usar Scan en rutas de usuario ni reconciliación periódica.

**Costos y límites:** cada GSI agrega almacenamiento/escrituras. Las particiones constantes de catálogo/deadlines son una simplificación del MVP académico y pueden concentrar tráfico; medir antes de escalar y diseñar particionado si se necesita. Evitar listas ilimitadas de pujas en META. Limitar tamaños de textos/resultado idempotente y asegurar que los conjuntos transaccionales y los ítems caben en los límites del motor al implementar.

## Escrituras atómicas y consistencia

| Transacción | Ítems afectados una sola vez por clave | Condiciones obligatorias | Resultado |
|---|---|---|---|
| TX-01 Crédito inicial | Put WALLET + Put MOVEMENT inicial | WALLET inexistente; identidad validada | 10.000 disponibles, cero reservados; reintento lee resultado, nunca reemplaza saldo |
| TX-02 Primera puja | Update META + Update WALLET comprador + Put BID + Put MOVEMENT RESERVE + Put REQUEST | META ACTIVE_NO_BIDS, version esperada, expiresAt>now, sellerId distinto; saldo suficiente; REQUEST inexistente | Reserva, líder, retirada ttl, vencimiento +20s y GSI3; GSI4 incluido en BID |
| TX-03 Siguiente puja | Update META + Update WALLET anterior + Update WALLET nuevo + Put BID + Put RELEASE anterior + Put RESERVE nuevo + Put REQUEST | ACTIVE_BIDDING, version/leader/monto observados, expiresAt>now, monto mayor, nuevo saldo suficiente y reserva anterior suficiente; REQUEST inexistente | Libera anterior, reserva nuevo y renueva vencimiento; movimientos únicos por usuario y bidId |
| TX-04 Liquidación | Update META + Update WALLET ganador + Update WALLET vendedor + Put PURCHASE + Put SALE + Put WON | ACTIVE_BIDDING, version/líder/monto observados, expiresAt<=now y reserva suficiente | FINISHED, settlementId y ganador; restar reservado del comprador, sumar disponible al vendedor; retirar GSI1/3 |
| TX-05 Cancelación | Update META condicionado (un ítem, no exige transacción multiítem) | Propietario, ACTIVE_NO_BIDS, version esperada y expiresAt>now | CANCELLED; retirar GSI1 y ttl, guardar cancelledAt |

- Condiciones se incluyen en cada Update/Put: no agregar ConditionCheck sobre una clave que ya se modifica. No hay escrituras parciales si una condición falla.
- Propuesta heredada: primera oferta >= precio inicial y prohibir autosuperación del líder. TX-03 presupone esa prohibición; si se permite, rediseñar la actualización de una única billetera y sus movimientos antes de implementar.
- Las lecturas previas no bloquean: condiciones de versión/saldo/estado deciden. Ante conflicto, relectura y reintentos acotados; no aceptar ciegamente sobre snapshot antiguo.
- Tras fallo o timeout, consultar REQUEST o META fuerte para distinguir commit exitoso de rechazo. REQUEST guarda resultado de la puja, aunque la subasta luego cambie. Un identificador reutilizado con otro cuerpo se rechaza. Expirado el período de retención no se promete deduplicación eterna.
- settlementId y transición condicionada hacen inocuo el doble cierre. Un reintento devuelve el cierre persistido; no vuelve a mover créditos. La condición temporal debe evaluarse con reloj de servidor capturado inmediatamente antes del intento; reintentos renuevan ese reloj.
- Después del commit: invalidar caché, actualizar/remover deadline y emitir WebSocket. Fallar estos efectos no revierte créditos. La recuperación parte de DynamoDB, no de Redis.

## Validaciones necesarias al implementar

1. Resolver los cuatro GSI, proyecciones, límites de campos/paginación, unidad temporal, duración REQUEST y registro WS en ADR. Las propuestas de este archivo no modifican por sí solas los specs aprobados.
2. Cubrir creación única de billetera, primera oferta y auto-superación según convención acordada, reservas simultáneas en varias subastas y conservación global de créditos.
3. Probar pujas concurrentes, requestId repetido con mismo/distinto cuerpo, dos cierres y puja vs cierre; verificar rollback sin movimientos/pujas huérfanos ni duplicación de créditos.
4. Probar TTL configurado, invisibilidad exacta a los 120s y retiro de ttl en primera puja; no esperar borrado físico puntual. Retener auditoría y victoria tras cierre.
5. Probar todas las páginas e índices, hidratación/UnprocessedKeys, vacíos con cursor y aislamiento entre usuarios. Verificar que ningún flujo operativo usa Scan.
6. Probar cache hit/miss, invalidación contra fill lento, fallos post-commit, Redis/worker reiniciados y reconciliación repetida; demostrar ganador aun si se perdió el evento WS.
7. Registrar comandos y evidencia en el backlog. Este documento es diseño: no se han ejecutado pruebas del sistema por haber creado las tablas.
