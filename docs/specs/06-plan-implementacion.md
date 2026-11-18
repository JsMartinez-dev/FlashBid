# Plan de implementación — Spec 06: pujas y reservas

**Estado:** planificación; no implementado. Las propuestas señaladas requieren decisión o formalización antes de implementarse. Fuente: [spec 06](06-pujas-reservas.md), [backlog](../backlog.md) y [especificación técnica](../ficha_tecnica/FlashBid_MVP1_Especificacion_Tecnica.md).

## Objetivo

Aceptar una oferta autenticada sobre una subasta ajena, reservar créditos de forma atómica, liberar al líder anterior, registrar auditoría e idempotencia y consultar ofertas. Desarrollar con FastAPI, DynamoDB Local y Redis; mantener adaptadores Lambda/CDK para validación posterior. El cierre y transferencia son del spec 07; eventos WebSocket del 08.

## Casos y entregas

| Orden | Caso | Resultado |
|---|---|---|
| 1 | Contratos, modelo y reglas | Documentar decisiones pendientes, claves, atributos, errores y límites. |
| 2 | CU-06-01 Primera puja | Validar sesión, subasta ajena vigente, monto y saldo; reservar, registrar y cambiar estado atómicamente. |
| 3 | CU-06-02 Superar líder | Liberar reserva anterior, reservar nueva y registrar movimientos y puja en la misma transacción. |
| 4 | CU-06-03 Reintentos | Guardar requestId, hash y resultado con la puja; mismo cuerpo devuelve resultado; cuerpo distinto es conflicto. |
| 5 | CU-06-04 Historial y React | Consultar pujas paginadas, formulario, estados de carga/error y actualización de saldos/detalle. |
| 6 | Integración serverless | Adaptador Lambda, rutas y permisos CDK; comprobar con LocalStack por separado. |

## Endpoints previstos

| Método y ruta | Acceso | Contrato |
|---|---|---|
| POST /auctions/{id}/bids | Token Bearer | `{ "amount": 2000, "requestId": "uuid" }`; retorna puja y resultado confirmado. |
| GET /auctions/{id}/bids | Token Bearer | Query por partición de subasta, orden descendente, paginación; sin información privada. |

Los códigos exactos de error y la forma definitiva de respuesta se formalizan antes de implementar. Se propone 401 sin sesión válida, 403 vendedor, 404 recurso ausente, 409 conflicto/vencimiento/requestId incompatible y 422 importe o saldo inválido. El frontend mantiene el mismo requestId al reintentar la misma intención y crea otro para una nueva puja.

## Flujo de puja

1. Validar token y extraer identidad del servidor; validar entero positivo, requestId y cuerpo.
2. Buscar idempotencia por usuario y requestId con lectura fuerte. Comparar hash canónico que incluya auctionId y amount. Un resultado previo idéntico se devuelve sin volver a modificar saldos; un cuerpo distinto se rechaza.
3. Leer con consistencia fuerte subasta y billeteras necesarias. Verificar que esté activa, no vencida (`now < expiresAt`), no sea propia, monto supere al líder y saldo disponible cubra reserva completa.
4. Ejecutar `TransactWriteItems`: condición de estado, versión, vencimiento y saldo; actualizar subasta y billeteras; guardar puja inmutable, movimientos y resultado de idempotencia. Primera puja retira TTL de subasta y establece `ACTIVE_BIDDING`; todas fijan `expiresAt = acceptedAt + 20s`.
5. Después del commit, invalidar snapshot e intentar actualizar Sorted Set con vencimiento; un fallo Redis no revierte una puja aceptada. Preparar interfaz de reconciliación; el worker y reconstrucción duradera son del spec 07, por lo que no se promete cierre automático en el 06.
6. Devolver el resultado persistido; al reenviar por timeout o conflicto de requestId, leer nuevamente registro idempotente. Manejar carreras con reintentos acotados y reloj actualizado.

## Datos y transacciones

| Registro | Clave | Datos necesarios |
|---|---|---|
| Subasta | `AUCTION#aid / META` | Estado, versión, vendedor, importe y puja líder, líder, vencimiento, GSI3; retirar TTL en primera puja. |
| Puja | `AUCTION#aid / BID#timestamp#bidId` | Participante, alias público, monto, acceptedAt, requestId y claves GSI4. |
| Billetera | `USER#uid / WALLET` | Disponible, reservado, versión; nunca negativos. |
| Movimiento | `USER#uid / MOVEMENT#timestamp#id` | Reserva o liberación, monto, deltas, subasta y operación. |
| Idempotencia | `USER#uid / REQUEST#requestId` | Hash, auctionId, resultado, fecha y TTL independiente. |

La primera puja escribe subasta, billetera del comprador, movimiento de reserva, puja y request. Una puja que supera a otra añade billetera y movimiento de liberación del líder previo. Cada ítem se modifica una sola vez dentro de la transacción. La suma de créditos disponibles y reservados se conserva. El cierre/transferencia no se implementa aquí.

## Decisiones aún abiertas

- **Primera oferta:** propuesta igual o mayor al precio inicial; confirmar.
- **Auto-superación del líder:** propuesta rechazarla para evitar actualizar dos veces la misma billetera; confirmar.
- **Retención de requestId:** propuesta siete días desde aceptación; TTL es limpieza asíncrona y la deduplicación no se promete indefinidamente. Confirmar.
- **Paginación:** propuesta 20 por defecto y máximo 50; definir cursor, validez y respuesta para subasta invisible.
- **Condición temporal concurrente:** documentar reloj capturado inmediatamente antes de la transacción, límites del modelo (DynamoDB no aporta reloj de servidor en condiciones), reintentos y comportamiento frente al cierre.
- **Reconciliación:** acordar cómo se registran deadlines si Redis falla y quién los reconstruirá en spec 07; no confundir expiración con cierre ya implementado.

## Pruebas y aceptación futuras

- Primera puja en el precio mínimo acordado, vendedor prohibido, valores inválidos y límite exacto `now >= expiresAt`.
- Reserva sin saldo suficiente, segunda puja mayor, liberación de líder y conservación global de créditos.
- Dos ofertas simultáneas, doble requestId idéntico, requestId con cuerpo distinto y fallo transaccional sin cambios parciales.
- Retirada del TTL de subasta, renovación de 20 segundos, registro inmutable y paginación del historial.
- Redis no disponible tras commit: puja persiste, caché no participa de validación financiera y deadline se recupera al implementar reconciliación.
- Contratos FastAPI y Lambda, permisos, pruebas locales y luego integración LocalStack. Dos usuarios en React; ninguna promesa de cierre automático antes del spec 07.
