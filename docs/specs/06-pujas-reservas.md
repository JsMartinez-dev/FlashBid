# Spec 06 — Pujas transaccionales, reservas e historial de ofertas

**Estado:** pendiente de implementación.  
**Dependencias:** 05.  
**Trazabilidad:** secciones 3.2, 3.3, 3.4, 5, 7, 9, 12 de la [especificación fuente](../FlashBid_MVP1_Especificacion_Tecnica.md).

## Objetivo y alcance

Entregar pujas transaccionales, reservas e historial de ofertas como incremento verificable del MVP. Aplican las [reglas comunes](README.md) y las dependencias anteriores.

## Casos de uso

### CU-06-01 — Realizar la primera puja

- **Actor:** Participante.
- **Precondiciones:** Subasta ajena vigente y saldo disponible.
- **Flujo principal:** Enviar amount y requestId; validar estado, versión, tiempo y saldo; reservar monto y crear puja, movimiento e idempotencia en una transacción.
- **Alternativas y errores:** Rechazar vendedor, importe inválido, saldo insuficiente o now>=expiresAt sin cambios parciales.
- **Resultado y aceptación:** Cambiar a ACTIVE_BIDDING, quitar ttl y fijar expiresAt=acceptedAt+20s; invalidar caché y actualizar deadline después del commit.

### CU-06-02 — Superar al líder

- **Actor:** Participante.
- **Precondiciones:** Subasta ACTIVE_BIDDING vigente.
- **Flujo principal:** Ofertar más que el líder; liberar reserva anterior, reservar monto nuevo y persistir líder, puja y movimientos atómicamente.
- **Alternativas y errores:** Rechazar empate y crédito reservado en otras subastas; resolver conflictos concurrentes con condiciones y reintentos limitados.
- **Resultado y aceptación:** Conservar suma de créditos, no sobregirar y renovar exactamente 20s; no modificar el mismo ítem dos veces en la transacción.

### CU-06-03 — Reintentar una puja sin duplicarla

- **Actor:** Participante.
- **Precondiciones:** requestId estable para la operación.
- **Flujo principal:** Consultar/persistir identidad+requestId y hash del cuerpo en la misma transacción; retornar resultado original cuando recuperable.
- **Alternativas y errores:** Reusar identificador con otro cuerpo devuelve conflicto; TTL de REQUEST independiente y con ventana documentada.
- **Resultado y aceptación:** Reenvíos simultáneos producen una sola puja y reserva, aun si se perdió la respuesta original.

### CU-06-04 — Consultar historial y gestionar errores de puja

- **Actor:** Usuario.
- **Precondiciones:** Detalle abierto.
- **Flujo principal:** Consultar GET /auctions/{id}/bids paginado y enviar pujas desde React; actualizar datos tras confirmación o conflicto.
- **Alternativas y errores:** Mostrar errores estructurados seguros de autenticación, permisos, vencimiento, saldo e importe.
- **Resultado y aceptación:** Query por AUCTION/BID descendente; cada oferta aceptada tiene registro inmutable y las rechazadas no alteran saldos.

## Criterio de cierre

Todos los casos anteriores cumplen su aceptación con pruebas reproducibles, contratos documentados y una demostración integrada. Registrar evidencias en el backlog. Las decisiones abiertas aplicables deben quedar resueltas en ADR antes de cerrar el spec.
