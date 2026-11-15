# Spec 09 — Mis subastas, mis pujas y victorias

**Estado:** pendiente de implementación.  
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
