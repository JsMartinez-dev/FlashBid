# Flujos de endpoints para demostración

Estos recorridos muestran autenticación, persistencia y privacidad. Están basados en los controladores y DTO actuales; no se ejecutaron durante su preparación. Conviene probarlos antes de la presentación con datos de demostración.

## 1. Registro de un cliente

**Valor:** creación de una cuenta y aceptación obligatoria de términos.

`POST /api/v1/auth/registro`

```json
{
  "email": "demo.cliente@ejemplo.com",
  "password": "UnaClaveSegura123!",
  "rol": "CLIENTE",
  "aceptaTerminos": true,
  "versionTerminos": "1.0"
}
```

**Resultado esperado:** `201 Created`, con el ID, correo y rol del usuario. Guarda el `id` para la consulta de perfil público. Usa un correo nuevo para evitar un conflicto por registro previo.

Como prueba adicional, repite con `aceptaTerminos: false` para mostrar que se rechaza.

## 2. Inicio de sesión y acceso protegido

**Valor:** autenticación y uso de una sesión para acceder a datos privados.

`POST /api/v1/auth/login`

```json
{
  "email": "demo.cliente@ejemplo.com",
  "password": "UnaClaveSegura123!"
}
```

**Resultado esperado:** `200 OK`, con `sessionToken` y `rol`.

Copia el token y llama a `GET /api/v1/perfil/me` con la cabecera:

```http
Authorization: Bearer <sessionToken>
```

**Resultado esperado:** el perfil de la cuenta autenticada. Intenta también la consulta sin token para mostrar que el recurso está protegido.

## 3. Actualizar y consultar datos personales

**Valor:** persistencia, validación y asociación de los datos con la cuenta autenticada.

Con el token, envía `PATCH /api/v1/perfil/me`:

```json
{
  "nombre": "Cliente de demostración",
  "telefono": "3001234567"
}
```

Luego consulta de nuevo `GET /api/v1/perfil/me`.

**Resultado esperado:** la consulta posterior muestra el nombre y teléfono actualizados. Como contraste, intenta un teléfono inválido y vuelve a consultar el perfil para comprobar que el dato anterior se conservó.

## 4. Ubicación y privacidad del perfil

**Valor:** separación entre zona aproximada y dirección exacta.

Con la sesión activa, envía `PUT /api/v1/perfil/me/ubicacion`:

```json
{
  "zonaAproximada": "Centro, Santa Marta",
  "direccionExacta": "Dirección ficticia de demostración"
}
```

Después compara:

1. `GET /api/v1/perfil/me`: el propietario puede consultar su ubicación.
2. `GET /api/v1/perfil/{usuarioId}/publico`: sustituye `{usuarioId}` por el ID del registro.

**Resultado esperado:** la respuesta pública contiene el identificador y la zona aproximada, sin dirección exacta. Usa una cuenta cuyo perfil permita la consulta pública.

## 5. Cierre de sesión

**Valor:** invalidación de una sesión y protección posterior de los recursos.

1. Envía `POST /api/v1/auth/logout` con `Authorization: Bearer <sessionToken>`.
2. Repite `GET /api/v1/perfil/me` usando el mismo token.

**Resultado esperado:** el cierre devuelve `204 No Content` y el intento posterior de acceso es rechazado por falta de una sesión válida.

Los cinco recorridos pueden ejecutarse en ese orden con una sola cuenta. La eliminación de cuenta queda fuera de esta demostración porque la auditoría detectó problemas pendientes de expiración y concurrencia.
