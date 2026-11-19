# Spec 07 — Cierre automático, ganador y liquidación

**Estado:** completado por indicación del usuario.
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

## Decisiones de experiencia confirmadas

- El detalle finalizado es visible para usuarios autenticados, sin exponer saldos privados. El periodo entre vencimiento y confirmación se muestra como `FINALIZING` (estado derivado, no persistido); después se muestra `FINISHED`.
- El ganador ve una felicitación; el vendedor ve el monto y el ganador; los demás ven el alias ganador. La sección «Mis subastas ganadas» muestra los productos ganados como simulación; no hay pedidos ni envíos.
- No existe cierre manual público. Una subasta con pujas no se puede cancelar; se mantiene la cancelación del vendedor antes de la primera puja.
- El worker consulta Redis cada dos segundos, reconcilia GSI3 al inicio y cada 30 segundos y relee la tabla antes de cerrar. DynamoDB y la transacción condicionada deciden el resultado.
- `GET /me/wins` devuelve victorias propias paginadas. Esta sección adelanta parte del spec 09; los demás historiales de ese spec siguen pendientes.
- El servidor usa su reloj inmediatamente antes de la transacción. DynamoDB no proporciona un reloj de servidor dentro de la condición; hay que validar carreras temporales y sincronización del reloj en integración.
