# 03 Patrones auxiliares: Redis, identidad y WebSocket


Estos accesos no tienen PK/SK DynamoDB. No guardar sesiones ni conexiones como si fueran entidades financieras.

| # | Vista/proceso y pregunta | Almacén / clave | Operación y datos | Frecuencia | Casos de uso |
|---|---|---|---|---|---|
| PA-24 | ¿Cómo inicio/cierro sesión y verifico identidad? | Cognito emulado o adaptador local | Registro/login/logout, validar firma, issuer, audience y expiración según proveedor; definir cierre/revocación de sesión; secretos fuera de tabla | Por sesión y petición protegida | CU-02-01, CU-02-02, CU-02-03 |
| PA-25 | ¿Hay un detalle público reciente? | Redis STRING auction:aid:snapshot | GET; ante miss GetItem fuerte y SET con TTL propuesto 3s; guardar snapshot y version, validar expiresAt también en hit | Muy alta | CU-05-02, CU-05-03 |
| PA-26 | ¿Cómo invalido sin repoblar datos anteriores? | Redis snapshot + auction:aid:generation | Propuesta: capturar generación antes de leer DB; tras commit incrementar generación y borrar snapshot atómicamente; SET por CAS solo si no cambió; generación temporal con retención superior a operación en vuelo | Cada mutación | CU-04-02, CU-06-01, CU-06-02, CU-07-02 |
| PA-27 | ¿Qué deadlines vencieron? | Redis ZSET auctions:deadlines; miembro aid, score expiresAt ms | ZADD después de puja; ZRANGEBYSCORE hasta now; revalidar META; ZREM tras cierre; reparar score desde DB si prorrogada | Cada puja/ciclo worker | CU-07-01 |
| PA-28 | ¿Cómo recupero deadlines perdidos? | Redis ZSET + GSI3/tabla | Query paginada, hidratar META, ZADD pendientes; repetición periódica; workers duplicados protegidos por TX-04 | Inicio y periódica | CU-07-03 |
| PA-29 | ¿Quién está conectado y suscrito? | Registro temporal del adaptador WS | connectionId, uid verificado, suscripciones, expiración de sesión; conectar, autorizar, suscribir y limpiar al desconectar/expirar | Cada conexión | CU-08-01 |
| PA-30 | ¿A quién envío el cambio confirmado? | Canal lógico auction:aid | Eventos bid_accepted, cancelled, finished con auctionId/version y payload público; destinatarios de registro de suscripción | Cada commit relevante | CU-08-02 |
| PA-31 | ¿Cómo recupero una conexión perdida? | Adaptador WS + HTTP | Backoff, nueva autorización, resuscripción y snapshot HTTP; ignorar versiones antiguas; revalidar también al finalizar cronómetro/foco | Por interrupción | CU-08-03 |
| PA-32 | ¿Están listos los servicios y endpoints? | Healthchecks / configuración local | /health, conexión DynamoDB y Redis; CDK outputs; sin entidad de negocio nueva | Arranque y diagnóstico | CU-01-01, CU-01-02, CU-01-03 |
| PA-33 | ¿Existe ya el dato de demostración? | Proveedor identidad + claves deterministas de tabla | Resolver cuentas por fixture; GetItem fuerte y puts condicionados; usar TX-01; publicaciones por fixture/generación con política de reposición explícita | Por seed | CU-10-01 |

**Caché:** el mecanismo de generación es una propuesta a probar, no garantía de consistencia absoluta ante fallo Redis post-commit. Con Redis inaccesible se usa DynamoDB; TTL corto y resíncronización limitan snapshots viejos. No usar caché para decidir reservas, permisos de mutación ni liquidación. La expiración de generaciones no debe permitir una escritura tardía: fijar timeout máximo de lectura/llenado y abortar fills antiguos; limpiar caché al recuperar un proceso que perdió invalidaciones. El catálogo se consulta por índice en este MVP, sin añadir caché de listas.

**Deadlines:** un ZADD atrasado puede reintroducir score viejo; siempre releer META al procesar, reparar o retirar según estado vigente. No remover a ciegas trabajo de una subasta prorrogada; usar comparación del score observado o reparación posterior. La reconciliación periódica cubre índices eventualmente consistentes, reinicios y fallos post-commit.

**WebSocket:** concretar el registro según el spike del spec 01. En gateway local único puede residir en memoria y reconstruirse con reconexión; si se usa API Gateway o múltiples procesos, documentar almacenamiento compartido y accesos por conexión/subasta antes de cerrar spec 08. La tabla financiera no depende de esta elección. Sin entrega garantizada de eventos, HTTP y revalidación periódica/de foco/de cronómetro permiten converger aunque no se detecte una pérdida de mensaje.
