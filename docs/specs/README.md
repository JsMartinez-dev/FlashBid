# Specs incrementales de FlashBid MVP 1

Descomposición de [la especificación técnica](../FlashBid_MVP1_Especificacion_Tecnica.md). El documento original se conserva como referencia de alcance. El orden expresa dependencias de entrega, no diez días de trabajo. [Backlog](../backlog.md).

## Reglas transversales

- Marketplace académico simulado: sin dinero real, pagos, envíos, chat, administración, rankings, filtros avanzados ni bots permanentes.
- React y Python integrados por entrega; Docker, CDK, API Gateway/Lambda, DynamoDB como fuente de verdad y Redis auxiliar. Solo emulación local.
- Identidad del token validado; autorización por propiedad; errores estructurados sin datos sensibles. Pantallas con carga, vacío, error y accesibilidad básica.
- Cada caso se entrega con backend, persistencia, UI cuando corresponda y pruebas de sus criterios. Las pruebas del spec 10 consolidan, no posponen, las de cada entrega.
- Estados: ACTIVE_NO_BIDS, ACTIVE_BIDDING, CANCELLED y FINISHED. Reloj autoritativo UTC; igualdad al vencimiento impide pujar.

## Secuencia

| Spec | Funcionalidad | Depende de | Casos |
|---|---|---|---|
| [01](01-entorno-local.md) | Entorno local y base integrada | Ninguna | 4 |
| [02](02-identidad-sesion.md) | Identidad, perfil y sesión | 01 | 3 |
| [03](03-billetera-inicial.md) | Billetera y crédito inicial | 02 | 2 |
| [04](04-publicacion-cancelacion.md) | Publicación y cancelación de subastas | 03 | 2 |
| [05](05-catalogo-detalle-cache.md) | Catálogo, detalle y expiración sin pujas | 04 | 3 |
| [06](06-pujas-reservas.md) | Pujas transaccionales, reservas e historial de ofertas | 05 | 4 |
| [07](07-cierre-liquidacion.md) | Cierre automático, ganador y liquidación | 06 | 3 |
| [08](08-tiempo-real.md) | Actualizaciones WebSocket y reconexión | 07 | 3 |
| [09](09-actividad-personal.md) | Mis subastas, mis pujas y victorias | 08 | 3 |
| [10](10-demo-validacion-entrega.md) | Demo reproducible, validación y documentación | 09 | 3 |

## Convenciones pendientes y límites del alcance

Estas propuestas se heredan como pendientes; no se convierten en decisiones aprobadas al dividir el documento:

| Tema | Resolver antes de cerrar | Orientación |
|---|---|---|
| Emulación y empaquetado | 01 | Probar edición instalada; documentar adaptadores y bundling. |
| Índices, proyecciones y paginación | 01 y cada acceso nuevo | ADR con Query, límites y costos; incluir mis pujas, omitido en la tabla HTTP original. |
| Primera oferta y autosuperación | 06 | Confirmado: primera puja entera superior al precio inicial; líder no puede pujar hasta ser superado. |
| Validación de URL, longitudes y límites por usuario | 04–06 | Definir límites concretos y códigos HTTP de errores; no inventar alcance adicional. |
| TTL de idempotencia | 06 | Confirmado: siete días desde la aceptación, independiente del TTL de subasta; borrado físico asíncrono. |
| Worker y unidades temporales | 07 | Definir invocación del cierre y unidad del Sorted Set; TTL DynamoDB en segundos Unix. |
| WebSocket | 08 | Documentar adaptador, autorización y sincronización; outbox garantizado queda fuera del MVP. |

## Cobertura de decisiones de la fuente

| Decisiones | Specs responsables |
|---|---|
| 1, 2, 18 | 02, 04, 06 y reglas comunes |
| 3, 4, 11, 19 | 03, 06, 07 |
| 5, 6, 10, 15, 26 y regla TTL | 04, 05, 06, 07 |
| 7, 20 | 08 |
| 8 | 01, 02 |
| 9, 13 | 04, 05 |
| 12 | 07 |
| 14 | 02–09 |
| 16, 22, 23, 24, 25 | 01 y evolución por spec |
| 17, 21, 27 | Pruebas por spec y consolidación 10 |
