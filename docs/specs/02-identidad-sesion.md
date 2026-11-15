# Spec 02 — Identidad, perfil y sesión

**Estado:** pendiente de implementación.  
**Dependencias:** 01.  
**Trazabilidad:** secciones 2, 7, 9, 16 de la [especificación fuente](../FlashBid_MVP1_Especificacion_Tecnica.md).

## Objetivo y alcance

Entregar identidad, perfil y sesión como incremento verificable del MVP. Aplican las [reglas comunes](README.md) y las dependencias anteriores.

## Casos de uso

### CU-02-01 — Registrar una cuenta

- **Actor:** Visitante.
- **Precondiciones:** Proveedor de identidad configurado.
- **Flujo principal:** Enviar email y contraseña desde React; crear identidad y perfil asociado.
- **Alternativas y errores:** Datos inválidos o email existente producen error seguro; reintentar no duplica el perfil.
- **Resultado y aceptación:** La cuenta puede iniciar sesión y consultar su propio perfil.

### CU-02-02 — Iniciar y cerrar sesión

- **Actor:** Usuario.
- **Precondiciones:** Cuenta registrada.
- **Flujo principal:** Autenticarse, guardar sesión según el adaptador elegido y cerrar sesión desde React.
- **Alternativas y errores:** Credenciales inválidas o sesión vencida llevan a autenticación sin filtrar información sensible.
- **Resultado y aceptación:** Login/logout y expiración funcionan; las pantallas protegidas requieren sesión válida.

### CU-02-03 — Autorizar acceso por identidad

- **Actor:** Usuario.
- **Precondiciones:** Token disponible.
- **Flujo principal:** Validar token en backend y obtener uid para GET /me y operaciones protegidas.
- **Alternativas y errores:** Token ausente/inválido devuelve 401; acceso ajeno prohibido devuelve 403.
- **Resultado y aceptación:** Ignorar userId suministrado por cliente; un mismo usuario puede vender y pujar, sin rol administrador.

## Criterio de cierre

Todos los casos anteriores cumplen su aceptación con pruebas reproducibles, contratos documentados y una demostración integrada. Registrar evidencias en el backlog. Las decisiones abiertas aplicables deben quedar resueltas en ADR antes de cerrar el spec.
