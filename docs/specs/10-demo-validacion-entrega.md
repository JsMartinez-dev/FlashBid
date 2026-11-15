# Spec 10 — Demo reproducible, validación y documentación

**Estado:** pendiente de implementación.  
**Dependencias:** 09.  
**Trazabilidad:** secciones 11, 12, 13, 14, 15, 16 de la [especificación fuente](../FlashBid_MVP1_Especificacion_Tecnica.md).

## Objetivo y alcance

Entregar demo reproducible, validación y documentación como incremento verificable del MVP. Aplican las [reglas comunes](README.md) y las dependencias anteriores.

## Casos de uso

### CU-10-01 — Preparar y repetir una demo

- **Actor:** Desarrollador/docente.
- **Precondiciones:** Entorno local desplegado.
- **Flujo principal:** Ejecutar seed_demo.py idempotente para cuentas, créditos y publicaciones ficticias; ejecutar setup de extremo a extremo.
- **Alternativas y errores:** Repetir seed no reacredita ni duplica datos; definir reposición de publicaciones demo vencidas.
- **Resultado y aceptación:** Guion con dos navegadores cubre registro, publicación, pujas, liberación, cierre, cancelación y expiración sin ofertas.

### CU-10-02 — Verificar integridad y recuperación

- **Actor:** Desarrollador.
- **Precondiciones:** Specs funcionales integrados.
- **Flujo principal:** Ejecutar pruebas unitarias, integración local y concurrencia; guardar comandos y evidencias.
- **Alternativas y errores:** Incluir dos pujas, mismo requestId simultáneo, doble cierre, puja vs cierre, rollback, reinicios y fallos de Redis/WS.
- **Resultado y aceptación:** Pruebas conservan créditos, verifican límites UTC, TTL configurado, hit/miss/invalidation y reconstrucción; ninguna prueba exige limpieza TTL puntual.

### CU-10-03 — Entregar y operar el MVP

- **Actor:** Desarrollador/docente.
- **Precondiciones:** Demo y pruebas satisfactorias.
- **Flujo principal:** Entregar README, .env.example, guías de inicio/parada/limpieza voluntaria, API, datos, arquitectura, ADR y diagramas de pujar/cerrar/reconectar.
- **Alternativas y errores:** Documentar diferencias de emulación, recursos necesarios y límites conocidos; limpieza nunca implícita en arranque.
- **Resultado y aceptación:** Desde entorno limpio otra persona reproduce demo, pruebas y evidencia de Single Table Design/Cache-Aside; documentar qué se conservó de la plantilla.

## Criterio de cierre

Todos los casos anteriores cumplen su aceptación con pruebas reproducibles, contratos documentados y una demostración integrada. Registrar evidencias en el backlog. Las decisiones abiertas aplicables deben quedar resueltas en ADR antes de cerrar el spec.
