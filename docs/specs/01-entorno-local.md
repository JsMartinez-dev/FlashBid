# Spec 01 — Entorno local y base integrada

**Estado:** completado por indicación del usuario.
**Dependencias:** Ninguna.  
**Trazabilidad:** secciones 1, 4, 5, 10, 11, 16 de la [especificación fuente](../FlashBid_MVP1_Especificacion_Tecnica.md).

## Objetivo y alcance

Entregar entorno local y base integrada como incremento verificable del MVP. Aplican las [reglas comunes](README.md) y las dependencias anteriores.

## Casos de uso

### CU-01-01 — Arrancar y desplegar el entorno

- **Actor:** Desarrollador.
- **Precondiciones:** Docker y Compose disponibles.
- **Flujo principal:** Ejecutar el setup, esperar healthchecks, desplegar CDK y obtener endpoints para React y worker.
- **Alternativas y errores:** Ante puertos ocupados o servicios caídos, informar el problema sin continuar con configuración incompleta.
- **Resultado y aceptación:** El arranque repetido no duplica recursos; /health y una lectura DynamoDB funcionan sin AWS real.

### CU-01-02 — Verificar identidad y WebSocket emulados

- **Actor:** Desarrollador.
- **Precondiciones:** Emulador levantado.
- **Flujo principal:** Probar Cognito y API Gateway WebSocket con la edición instalada; registrar resultados y adaptadores elegidos.
- **Alternativas y errores:** Si falta soporte, usar sustituto Docker documentado conservando contratos y autorización.
- **Resultado y aceptación:** Existe evidencia de compatibilidad o ADR de alternativa; Lambda, DynamoDB y Redis se conservan.

### CU-01-03 — Consultar salud desde React

- **Actor:** Usuario/desarrollador.
- **Precondiciones:** API desplegada.
- **Flujo principal:** Abrir la aplicación React y consultar /health mostrando carga, resultado y error.
- **Alternativas y errores:** Si falla Redis o DynamoDB, mostrar el estado real del componente.
- **Resultado y aceptación:** Frontend y backend quedan integrados desde esta entrega; módulos compartidos se empaquetan en las Lambdas.

### CU-01-04 — Preparar accesos de datos

- **Actor:** Desarrollador.
- **Precondiciones:** Patrones del MVP identificados.
- **Flujo principal:** Documentar PK/SK, TTL numérico, índices y consultas; definir contratos y separación handler/servicio/repositorio.
- **Alternativas y errores:** Los GSI no se usan para validar escrituras críticas; evitar Scan periódico.
- **Resultado y aceptación:** ADR cubre catálogo, vendedor, victorias, pujas propias y vencimientos; CDK evoluciona junto con cada funcionalidad.

## Criterio de cierre

Todos los casos anteriores cumplen su aceptación con pruebas reproducibles, contratos documentados y una demostración integrada. Registrar evidencias en el backlog. Las decisiones abiertas aplicables deben quedar resueltas en ADR antes de cerrar el spec.
