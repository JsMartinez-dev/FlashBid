# Spec 09 — Mis subastas, mis pujas y victorias

**Estado:** implementado; validación integrada pendiente.  
**Dependencias:** 08.  
**Trazabilidad:** secciones 5.1, 7, 9 de la [especificación fuente](../FlashBid_MVP1_Especificacion_Tecnica.md).

## Objetivo y alcance

Entregar mis subastas, mis pujas y victorias como incremento verificable del MVP. Aplican las [reglas comunes](README.md) y las dependencias anteriores.

## Casos de uso

### CU-09-01 — Consultar mis publicaciones

- **Actor:** Usuario.
- **Precondiciones:** Sesión válida.
- **Flujo principal:** GET /me/auctions muestra propias en curso, finalizadas y canceladas con navegación al detalle.
- **Alternativas y errores:** Sin pujas vencidas no se anuncian activas ni se exige conservarlas después de TTL.
- **Resultado y aceptación:** Query por vendedor; paginación y estados vacíos; cancelación reutiliza reglas del spec 04.

### CU-09-02 — Consultar mis pujas

- **Actor:** Usuario.
- **Precondiciones:** Existen ofertas propias.
- **Flujo principal:** Mostrar historial propio paginado enlazado a las subastas y su resultado.
- **Alternativas y errores:** Proteger privacidad y soportar lista vacía o recurso ya invisible.
- **Resultado y aceptación:** Definir acceso indexado/desnormalizado y contrato adicional propuesto GET /me/bids en ADR; no recorrer todas las subastas con Scan.

### CU-09-03 — Consultar mis victorias

- **Actor:** Usuario.
- **Precondiciones:** Subasta liquidada a su favor.
- **Flujo principal:** GET /me/wins muestra subastas ganadas, monto y resultado simulado.
- **Alternativas y errores:** No mostrar victoria antes de liquidación confirmada; acceso solo a historial propio.
- **Resultado y aceptación:** Elegir GSI o ítems WON en ADR y mantenerlos consistentemente con liquidación; UI permite contrastar movimientos.

## Criterio de cierre

Todos los casos anteriores cumplen su aceptación con pruebas reproducibles, contratos documentados y una demostración integrada. Registrar evidencias en el backlog. Las decisiones abiertas aplicables deben quedar resueltas en ADR antes de cerrar el spec.

## Decisión y contrato de implementación

- Por decisión del usuario, «Mis pujas» muestra **una fila por subasta con la última oferta del usuario**, no una fila por cada oferta. El historial completo por subasta se conserva en `GET /auctions/{id}/bids`.
- `GET /me/auctions`, `GET /me/bids` y `GET /me/wins` requieren token Bearer y aceptan `limit` (1–50; 20 por defecto) y `cursor`. Devuelven `items` y `nextCursor`; el listado de subastas incluye `serverNow`.
- Mis subastas consulta GSI2 y relee los registros desde la tabla. Una publicación sin pujas vencida se presenta como vencida mientras exista; TTL puede eliminarla más tarde.
- Cada puja confirmada actualiza, en la transacción de aceptación, `USER#uid / PARTICIPATION#auctionId` con la última oferta y versión. Mis pujas consulta esos resúmenes con `Query` por usuario; el orden de páginas es por identificador de subasta, no por fecha. Los cambios de estado se comprueban contra META.
- En el primer acceso a Mis pujas se recuperan las ofertas antiguas consultando GSI4 paginado y se crea un resumen por subasta; escrituras condicionadas impiden que una migración antigua sobrescriba una puja más reciente. GSI4 es eventualmente consistente, por lo que los registros antiguos aún no visibles en ese índice al momento de la migración podrían requerir una reconciliación posterior.
- Mis victorias consulta los ítems WON escritos en la transacción de cierre; permanece disponible únicamente para el ganador. El despliegue en LocalStack y la prueba integrada siguen pendientes.
