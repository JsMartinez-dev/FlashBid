# Spec 08 — Actualizaciones WebSocket y reconexión

**Estado:** pendiente de implementación.  
**Dependencias:** 07.  
**Trazabilidad:** secciones 4, 8, 9, 12 de la [especificación fuente](../FlashBid_MVP1_Especificacion_Tecnica.md).

## Objetivo y alcance

Entregar actualizaciones websocket y reconexión como incremento verificable del MVP. Aplican las [reglas comunes](README.md) y las dependencias anteriores.

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
