# Backlog — FlashBid MVP 1

Cada fila corresponde a un caso de uso detallado en `specs/`. Todos están **Pendientes**: la existencia de código base no acredita su aceptación. Estados sugeridos: Pendiente → En curso → En validación → Hecho. Marcar Hecho solo con criterios satisfechos y evidencia enlazada. El orden sigue dependencias; toda la lista pertenece al MVP.

Fuente: [especificación original](FlashBid_MVP1_Especificacion_Tecnica.md). [Índice y convenciones](specs/README.md).

## Spec 01 — Entorno local y base integrada

**Depende de:** Ninguna. [Ver especificación](specs/01-entorno-local.md).

| Caso | Caso de uso a implementar | Estado | Evidencia |
|---|---|---|---|
| [CU-01-01](specs/01-entorno-local.md) | Arrancar y desplegar el entorno | En validación | `scripts/setup-local.sh`, `docker compose config --quiet` |
| [CU-01-02](specs/01-entorno-local.md) | Verificar identidad y WebSocket emulados | En validación | `docs/adr/001-local-identity-and-emulation.md` |
| [CU-01-03](specs/01-entorno-local.md) | Consultar salud desde React | En validación | `frontend/src/main.tsx`, `/health` |
| [CU-01-04](specs/01-entorno-local.md) | Preparar accesos de datos | En validación | `docs/adr/002-access-patterns-and-time.md` |

## Spec 02 — Identidad, perfil y sesión

**Depende de:** 01. [Ver especificación](specs/02-identidad-sesion.md).

| Caso | Caso de uso a implementar | Estado | Evidencia |
|---|---|---|---|
| [CU-02-01](specs/02-identidad-sesion.md) | Registrar una cuenta | En validación | `auth_service/main.py`, `test_identity.py` |
| [CU-02-02](specs/02-identidad-sesion.md) | Iniciar y cerrar sesión | En validación | `auth_service/main.py`, `frontend/src/main.tsx` |
| [CU-02-03](specs/02-identidad-sesion.md) | Autorizar acceso por identidad | En validación | `lambdas/users/handler.py`, `test_identity.py` |

## Spec 03 — Billetera y crédito inicial

**Depende de:** 02. [Ver especificación](specs/03-billetera-inicial.md).

| Caso | Caso de uso a implementar | Estado | Evidencia |
|---|---|---|---|
| [CU-03-01](specs/03-billetera-inicial.md) | Recibir créditos iniciales una sola vez | En validación | `wallets/repository.py`, `test_wallets.py` |
| [CU-03-02](specs/03-billetera-inicial.md) | Consultar saldos y movimientos | En validación | `wallet/handler.py`, `test_wallets.py` |

## Spec 04 — Publicación y cancelación de subastas

**Depende de:** 03. [Ver especificación](specs/04-publicacion-cancelacion.md).

| Caso | Caso de uso a implementar | Estado | Evidencia |
|---|---|---|---|
| [CU-04-01](specs/04-publicacion-cancelacion.md) | Publicar un producto ficticio | En validación | `auctions/repository.py`, `test_auctions.py` |
| [CU-04-02](specs/04-publicacion-cancelacion.md) | Cancelar antes de la primera puja | En validación | `auctions/repository.py`, `test_auctions.py` |

## Spec 05 — Catálogo, detalle y expiración sin pujas

**Depende de:** 04. [Ver especificación](specs/05-catalogo-detalle-cache.md).

| Caso | Caso de uso a implementar | Estado | Evidencia |
|---|---|---|---|
| [CU-05-01](specs/05-catalogo-detalle-cache.md) | Explorar subastas activas | Pendiente | — |
| [CU-05-02](specs/05-catalogo-detalle-cache.md) | Consultar detalle con Cache-Aside | Pendiente | — |
| [CU-05-03](specs/05-catalogo-detalle-cache.md) | Ocultar publicación vencida sin ofertas | Pendiente | — |

## Spec 06 — Pujas transaccionales, reservas e historial de ofertas

**Depende de:** 05. [Ver especificación](specs/06-pujas-reservas.md).

| Caso | Caso de uso a implementar | Estado | Evidencia |
|---|---|---|---|
| [CU-06-01](specs/06-pujas-reservas.md) | Realizar la primera puja | Pendiente | — |
| [CU-06-02](specs/06-pujas-reservas.md) | Superar al líder | Pendiente | — |
| [CU-06-03](specs/06-pujas-reservas.md) | Reintentar una puja sin duplicarla | Pendiente | — |
| [CU-06-04](specs/06-pujas-reservas.md) | Consultar historial y gestionar errores de puja | Pendiente | — |

## Spec 07 — Cierre automático, ganador y liquidación

**Depende de:** 06. [Ver especificación](specs/07-cierre-liquidacion.md).

| Caso | Caso de uso a implementar | Estado | Evidencia |
|---|---|---|---|
| [CU-07-01](specs/07-cierre-liquidacion.md) | Detectar vencimientos y cerrar | Pendiente | — |
| [CU-07-02](specs/07-cierre-liquidacion.md) | Liquidar una única vez | Pendiente | — |
| [CU-07-03](specs/07-cierre-liquidacion.md) | Recuperar vencimientos tras fallos | Pendiente | — |

## Spec 08 — Actualizaciones WebSocket y reconexión

**Depende de:** 07. [Ver especificación](specs/08-tiempo-real.md).

| Caso | Caso de uso a implementar | Estado | Evidencia |
|---|---|---|---|
| [CU-08-01](specs/08-tiempo-real.md) | Suscribirse a una subasta | Pendiente | — |
| [CU-08-02](specs/08-tiempo-real.md) | Recibir pujas, cancelaciones y cierres | Pendiente | — |
| [CU-08-03](specs/08-tiempo-real.md) | Reconectar y recuperar estado | Pendiente | — |

## Spec 09 — Mis subastas, mis pujas y victorias

**Depende de:** 08. [Ver especificación](specs/09-actividad-personal.md).

| Caso | Caso de uso a implementar | Estado | Evidencia |
|---|---|---|---|
| [CU-09-01](specs/09-actividad-personal.md) | Consultar mis publicaciones | Pendiente | — |
| [CU-09-02](specs/09-actividad-personal.md) | Consultar mis pujas | Pendiente | — |
| [CU-09-03](specs/09-actividad-personal.md) | Consultar mis victorias | Pendiente | — |

## Spec 10 — Demo reproducible, validación y documentación

**Depende de:** 09. [Ver especificación](specs/10-demo-validacion-entrega.md).

| Caso | Caso de uso a implementar | Estado | Evidencia |
|---|---|---|---|
| [CU-10-01](specs/10-demo-validacion-entrega.md) | Preparar y repetir una demo | Pendiente | — |
| [CU-10-02](specs/10-demo-validacion-entrega.md) | Verificar integridad y recuperación | Pendiente | — |
| [CU-10-03](specs/10-demo-validacion-entrega.md) | Entregar y operar el MVP | Pendiente | — |

# Evidencia de implementación

## Specs 01 y 02

- Rama: `dev`.
- Comandos verificados: `uv run pytest -q`, `cd frontend && npm run build` y `cd app && npx aws-cdk synth`.
- Resultado: 35 pruebas unitarias aprobadas; frontend y síntesis CDK aprobados.
