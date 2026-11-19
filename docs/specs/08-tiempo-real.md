# Spec 08 — Actualizaciones WebSocket y reconexión

**Estado:** completado por indicación del usuario.
**Dependencias:** 07.  
**Trazabilidad:** secciones 4, 8, 9, 12 de la [especificación fuente](../FlashBid_MVP1_Especificacion_Tecnica.md).

## Objetivo y alcance

Entregar actualizaciones websocket y reconexión como incremento verificable del MVP. Aplican las [reglas comunes](README.md) y las dependencias anteriores.

## Decisiones confirmadas por el usuario

- **Alcance visual:** la actualización en tiempo real se aplica al detalle de la subasta abierta; no se exige actualizar automáticamente todas las tarjetas del catálogo.
- **Reserva de pujas:** el importe del líder permanece en saldo reservado y no puede utilizarse en otras subastas. Cuando otro usuario lo supera, se libera la reserva anterior y se reserva la nueva. Las operaciones son responsabilidad transaccional del backend y DynamoDB; los eventos solo informan de los cambios.
- **Liquidación:** al finalizar y confirmarse el cierre, se actualizan la billetera del ganador y la del vendedor. La interfaz consulta el saldo propio y los movimientos después de los eventos relevantes y al reconectar; nunca se publican saldos privados en el canal de la subasta.
- **Desconexión:** mostrar un aviso de que se perdió la conexión en tiempo real y que se intenta reconectar. Conservar la última información y aclarar que puede estar desactualizada; el tiempo de la subasta continúa en el servidor. No afirmar que sigue activa sin volver a consultarlo.
- **Resincronización:** tras reconectar, obtener por HTTP el detalle, historial y datos propios pertinentes; las operaciones confirmadas no se revierten si falla un evento.

## Casos de uso

### CU-08-01 — Suscribirse a una subasta

- **Actor:** Usuario.
- **Precondiciones:** Sesión y adaptador WebSocket válidos.
- **Flujo principal:** Autorizar conexión/suscripción por canal y sincronizar snapshot HTTP con la suscripción.
- **Alternativas y errores:** Rechazar sesiones inválidas y limpiar conexiones cerradas; reconciliar la ventana entre lectura y conexión.
- **Resultado y aceptación:** Dos navegadores reciben cambios de la misma subasta sin exponer datos privados.

### CU-08-02 — Recibir pujas, cancelaciones y cierres

- **Actor:** Usuario/sistema.
- **Precondiciones:** Canal conectado.
- **Flujo principal:** Emitir auction.bid_accepted, auction.cancelled y auction.finished después del commit con auctionId y versión.
- **Alternativas y errores:** Ignorar duplicados o versiones anteriores; fallo de envío nunca revierte una operación confirmada.
- **Resultado y aceptación:** Eventos incluyen campos del contrato fuente; UI actualiza líder, vencimiento y estado final con cronómetro basado en tiempo del servidor.

### CU-08-03 — Reconectar y recuperar estado

- **Actor:** Usuario.
- **Precondiciones:** Conexión interrumpida.
- **Flujo principal:** Reintentar con backoff, recuperar HTTP y revalidar sesión, detalle, saldos e historial afectados.
- **Alternativas y errores:** Eventos perdidos o desordenados requieren resíncronización; no prometer entrega exactamente una vez.
- **Resultado y aceptación:** Tras desconexión durante puja o cierre, UI converge al estado persistido sin duplicar operaciones.

## Criterio de cierre

Todos los casos anteriores cumplen su aceptación con pruebas reproducibles, contratos documentados y una demostración integrada. Registrar evidencias en el backlog. Las decisiones abiertas aplicables deben quedar resueltas en ADR antes de cerrar el spec.

## Diseño de implementación

- `WS /ws/auctions/{auction_id}`: la primera trama JSON contiene `{ "token": "<JWT>" }`; no se coloca el token en la URL. Se valida sesión, origen y existencia de la subasta; `subscribed` confirma la suscripción.
- Los servicios de pujas, cancelación y cierre publican eventos públicos en el canal Redis `events:auction:{id}` después de confirmar en DynamoDB. El gateway reenvía únicamente los eventos de ese canal. Redis Pub/Sub no garantiza entrega; el cliente se resincroniza por HTTP tras suscribirse/reconectar y también periódicamente o al recuperar foco.
- Los eventos contienen `type`, `auctionId`, `version` y solo datos públicos. La billetera y victorias propias se consultan por HTTP, no se transmiten en eventos públicos.
- En Compose local FastAPI aloja el WebSocket en el puerto 8000; el Compose con LocalStack incluye un gateway FastAPI alternativo en 8001. El gateway es local y requiere validación de integración; no es una implementación de API Gateway WebSocket.
- El cliente envía el token como primera trama y debe reconectar tras obtener una nueva sesión. La conexión se cierra al expirar el token. La conexión no asegura que la subasta siga activa: el reloj y DynamoDB gobiernan su estado.
