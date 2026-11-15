# Spec 07 — Cierre automático, ganador y liquidación

**Estado:** pendiente de implementación.  
**Dependencias:** 06.  
**Trazabilidad:** secciones 3.3, 3.4, 5.1, 6.2, 12 de la [especificación fuente](../FlashBid_MVP1_Especificacion_Tecnica.md).

## Objetivo y alcance

Entregar cierre automático, ganador y liquidación como incremento verificable del MVP. Aplican las [reglas comunes](README.md) y las dependencias anteriores.

## Casos de uso

### CU-07-01 — Detectar vencimientos y cerrar

- **Actor:** Worker.
- **Precondiciones:** Subastas con pujas confirmadas.
- **Flujo principal:** Leer auctions:deadlines; verificar en DynamoDB estado y expiresAt<=now; ejecutar servicio de cierre.
- **Alternativas y errores:** Un score viejo no cierra una subasta prorrogada: actualizarlo con el vencimiento persistido.
- **Resultado y aceptación:** Convención temporal única documentada; cierre válido remueve miembro con cuidado ante carreras y persiste FINISHED.

### CU-07-02 — Liquidar una única vez

- **Actor:** Sistema.
- **Precondiciones:** Cierre válido.
- **Flujo principal:** Transferir reserva ganadora al disponible del vendedor y persistir ganador, puja, monto, finishedAt, settlementId y movimientos en una transacción.
- **Alternativas y errores:** Dos workers o carrera puja/cierre no duplican transferencia ni aceptan oferta tardía.
- **Resultado y aceptación:** No descontar nuevamente saldo disponible del comprador; transferencia 100% sin comisión e invariante global conservada; UI muestra Subasta ganada (simulación).

### CU-07-03 — Recuperar vencimientos tras fallos

- **Actor:** Worker.
- **Precondiciones:** DynamoDB conserva subastas ACTIVE_BIDDING.
- **Flujo principal:** Al arrancar y ante errores reconstruir Sorted Set con Query indexada y procesar pendientes.
- **Alternativas y errores:** Si ZADD falla tras puja confirmada no revertirla; sin Redis continuar validando ofertas en DynamoDB y recuperar cierre después.
- **Resultado y aceptación:** Reinicio de worker/Redis y fallo post-commit no pierden liquidaciones; sin Scan periódico.

## Criterio de cierre

Todos los casos anteriores cumplen su aceptación con pruebas reproducibles, contratos documentados y una demostración integrada. Registrar evidencias en el backlog. Las decisiones abiertas aplicables deben quedar resueltas en ADR antes de cerrar el spec.
