# ADR 003: crédito inicial y reglas de publicación

## Estado

Aceptado para los specs 03 y 04.

## Decisión

La primera lectura autenticada de `GET /me` garantiza una billetera mediante una transacción DynamoDB: crea `WALLET` con 10.000 créditos disponibles, cero reservados y un movimiento `INITIAL_CREDIT`. Ambas escrituras condicionan la inexistencia de la billetera. Un reintento que pierda la carrera recupera la billetera existente, sin acreditar de nuevo.

Los movimientos se consultan con `Query` sobre `USER#<uid>` y `begins_with(SK, 'MOVEMENT#')`, en orden descendente, con límite de 1 a 50 y cursor opaco. Nunca se realiza `Scan`.

Una publicación es `ACTIVE_NO_BIDS`, dura 120 segundos y persiste `expiresAt` en milisegundos Unix y `ttl` en segundos Unix. Los campos obligatorios son título de 3 a 120 caracteres, descripción de hasta 2.000, categoría de 2 a 50, URL HTTP(S) pública de hasta 2.048 y precio inicial entero positivo. La cancelación requiere vendedor propietario, estado sin pujas y reloj del servidor anterior al vencimiento; quita TTL e índice de catálogo, pero conserva auditoría.

## Consecuencias

El cliente solo oculta la acción de cancelación; el backend siempre vuelve a comprobar las condiciones. Una imagen inaccesible no bloquea la publicación: el frontend posterior usará un placeholder visual. Cache de detalle se incorporará en el spec 05; por ahora no hay instantánea de subasta que invalidar.
