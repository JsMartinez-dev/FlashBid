# Spec 03 — Billetera y crédito inicial

**Estado:** pendiente de implementación.  
**Dependencias:** 02.  
**Trazabilidad:** secciones 2, 3.3, 5, 7, 9, 16 de la [especificación fuente](../FlashBid_MVP1_Especificacion_Tecnica.md).

## Objetivo y alcance

Entregar billetera y crédito inicial como incremento verificable del MVP. Aplican las [reglas comunes](README.md) y las dependencias anteriores.

## Casos de uso

### CU-03-01 — Recibir créditos iniciales una sola vez

- **Actor:** Usuario/sistema.
- **Precondiciones:** Identidad verificada.
- **Flujo principal:** Crear billetera con 10.000 disponibles, cero reservados y movimiento inicial condicionado a inexistencia.
- **Alternativas y errores:** Callbacks, seed y solicitudes concurrentes repetidas no vuelven a acreditar.
- **Resultado y aceptación:** Una cuenta obtiene exactamente 10.000 créditos aun con reintentos concurrentes.

### CU-03-02 — Consultar saldos y movimientos

- **Actor:** Usuario.
- **Precondiciones:** Billetera creada.
- **Flujo principal:** Mostrar disponible, reservado y movimientos paginados mediante /me y /me/wallet/movements.
- **Alternativas y errores:** No permitir consultar la billetera de otra identidad; manejar páginas vacías y errores.
- **Resultado y aceptación:** React distingue saldos y tipos de movimiento; Query por USER y MOVEMENT, sin Scan; futuras reservas y transferencias se reflejan aquí.

## Criterio de cierre

Todos los casos anteriores cumplen su aceptación con pruebas reproducibles, contratos documentados y una demostración integrada. Registrar evidencias en el backlog. Las decisiones abiertas aplicables deben quedar resueltas en ADR antes de cerrar el spec.
