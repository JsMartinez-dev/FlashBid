# Spec 05 — Catálogo, detalle y expiración sin pujas

**Estado:** completado por indicación del usuario.
**Dependencias:** 04.  
**Trazabilidad:** secciones 3.4, 5.1, 6.1, 7, 9 de la [especificación fuente](../FlashBid_MVP1_Especificacion_Tecnica.md).

## Objetivo y alcance

Entregar catálogo, detalle y expiración sin pujas como incremento verificable del MVP. Aplican las [reglas comunes](README.md) y las dependencias anteriores.

## Casos de uso

### CU-05-01 — Explorar subastas activas

- **Actor:** Usuario.
- **Precondiciones:** Publicaciones disponibles.
- **Flujo principal:** Consultar GET /auctions paginado y mostrar imagen, precio, líder y tiempo restante.
- **Alternativas y errores:** Excluir canceladas, finalizadas y vencidas incluso si el GSI o caché está atrasado.
- **Resultado y aceptación:** Consulta indexada con paginación documentada; lista vacía, carga y error visibles; no Scan.

### CU-05-02 — Consultar detalle con Cache-Aside

- **Actor:** Usuario.
- **Precondiciones:** Identificador de subasta.
- **Flujo principal:** GET /auctions/{id} consulta Redis, luego DynamoDB ante miss y almacena snapshot público.
- **Alternativas y errores:** Sin Redis leer DynamoDB; recurso ausente o invisible devuelve 404; evitar repoblar versión vieja tras invalidación.
- **Resultado y aceptación:** Verificar hit/miss, TTL corto configurable y protección contra snapshot obsoleto; pujas y liquidaciones nunca validan contra caché.

### CU-05-03 — Ocultar publicación vencida sin ofertas

- **Actor:** Sistema/usuario.
- **Precondiciones:** Subasta ACTIVE_NO_BIDS.
- **Flujo principal:** Comparar reloj UTC del servidor con expiresAt y ocultar desde now>=expiresAt; TTL limpia posteriormente.
- **Alternativas y errores:** La demora del borrado físico no permite consultar como activa ni pujar.
- **Resultado y aceptación:** Pruebas en el límite exacto de 120 s; ttl solo en registros previstos y no exigir borrado físico inmediato.

## Criterio de cierre

Todos los casos anteriores cumplen su aceptación con pruebas reproducibles, contratos documentados y una demostración integrada. Registrar evidencias en el backlog. Las decisiones abiertas aplicables deben quedar resueltas en ADR antes de cerrar el spec.

## Contrato de implementación

- `GET /auctions` y `GET /auctions/{id}` requieren `Authorization: Bearer <token>`.
- El catálogo acepta `limit` entre 1 y 50 (20 por defecto) y `cursor` opaco. Devuelve `{items, nextCursor, serverNow}`; una página vacía puede incluir `nextCursor`. `serverNow` y `expiresAt` son milisegundos Unix.
- El detalle devuelve los datos públicos y `serverNow`; una subasta inexistente, cancelada, finalizada o vencida devuelve 404.
- `AUCTION_CACHE_TTL` configura el TTL de las instantáneas Redis, por defecto 3 segundos. Generaciones evitan llenar la caché con una lectura iniciada antes de una invalidación exitosa. Si Redis falla después de una escritura, la instantánea anterior puede persistir hasta su TTL; las operaciones críticas nunca la usan.
- GSI1 es eventualmente consistente: se relee cada resultado de la tabla con lectura fuerte, aunque un registro nuevo puede tardar en aparecer.
- Las rutas de FastAPI y Lambda usan los mismos servicios. El usuario informó la validación del spec; las evidencias y el alcance exacto de esa validación no se adjuntaron.
