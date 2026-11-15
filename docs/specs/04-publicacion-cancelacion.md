# Spec 04 — Publicación y cancelación de subastas

**Estado:** pendiente de implementación.  
**Dependencias:** 03.  
**Trazabilidad:** secciones 2, 3.1, 3.4, 5, 7, 9 de la [especificación fuente](../FlashBid_MVP1_Especificacion_Tecnica.md).

## Objetivo y alcance

Entregar publicación y cancelación de subastas como incremento verificable del MVP. Aplican las [reglas comunes](README.md) y las dependencias anteriores.

## Casos de uso

### CU-04-01 — Publicar un producto ficticio

- **Actor:** Vendedor.
- **Precondiciones:** Sesión válida.
- **Flujo principal:** Completar título, descripción, categoría, precio inicial y URL pública de imagen; POST /auctions crea ACTIVE_NO_BIDS.
- **Alternativas y errores:** Validar campos, entero positivo y URL según convención documentada; imagen inaccesible usa placeholder.
- **Resultado y aceptación:** Persistir sellerId autenticado, versión, createdAt, expiresAt=createdAt+120s y ttl numérico equivalente en segundos Unix; mostrar publicación en React.

### CU-04-02 — Cancelar antes de la primera puja

- **Actor:** Vendedor.
- **Precondiciones:** Subasta propia activa sin pujas y sin vencer.
- **Flujo principal:** Solicitar DELETE /auctions/{id}; cambiar condicionalmente a CANCELLED e invalidar caché.
- **Alternativas y errores:** Rechazar ajenos, subasta vencida o con pujas; carrera con primera puja solo permite una transición válida.
- **Resultado y aceptación:** No borrar auditoría de cancelación; UI ofrece acción solo cuando procede y backend vuelve a verificar.

## Criterio de cierre

Todos los casos anteriores cumplen su aceptación con pruebas reproducibles, contratos documentados y una demostración integrada. Registrar evidencias en el backlog. Las decisiones abiertas aplicables deben quedar resueltas en ADR antes de cerrar el spec.
