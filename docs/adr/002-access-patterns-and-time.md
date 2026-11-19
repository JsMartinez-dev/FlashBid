# ADR 002: modelo de acceso inicial

## Estado

Aceptado para la base del spec 01.

## Decisión

`FlashBidTable` usa `PK` y `SK` de texto, TTL numérico `ttl` en segundos Unix y cuatro GSI definidos en `docs/data/01_patrones_acceso.md`. Los perfiles usan lecturas fuertes por clave. Catálogo, vendedor, vencimientos y pujas propias tienen índices separados; los GSI solo descubren claves, nunca validan una operación crítica.

Los tiempos de dominio usarán UTC, `expiresAt` en milisegundos Unix y una clave de vencimiento con ancho fijo. Redis será cache-aside y un índice reconstruible de vencimientos. No se usa `Scan` en rutas de usuario ni en procesos periódicos.

## Consecuencias

Los índices se crean desde el inicio para evitar una migración destructiva posterior. Las operaciones financieras y cierres posteriores releerán la tabla con consistencia fuerte y usarán condiciones/transacciones.
