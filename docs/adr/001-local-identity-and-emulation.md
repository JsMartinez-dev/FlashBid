# ADR 001: identidad local y límites de emulación

## Estado

Aceptado para los specs 01 y 02.

## Contexto

FlashBid necesita una identidad verificable en local, perfiles persistentes y un contrato que las Lambdas puedan validar. LocalStack Community 4.14 no garantiza un flujo completo de Cognito ni API Gateway WebSocket sin características comerciales.

## Decisión

Se conserva LocalStack para Lambda, API Gateway REST y DynamoDB, y Redis como auxiliar. Un contenedor FastAPI actúa como adaptador de identidad local: registra e inicia sesión, emite JWT HS256 de una hora y persiste el perfil y la identidad local de forma transaccional en DynamoDB. Las Lambdas validan firma, emisor, audiencia y vencimiento, y solo usan `sub` como `uid` autorizado.

La identidad por correo se guarda en `IDENTITY#<email> / PROFILE` para imponer unicidad local. El perfil público está en `USER#<uid> / PROFILE`; las respuestas no exponen el hash de contraseña. El adaptador se puede sustituir por Cognito sin cambiar `GET /me` ni el formato Bearer.

WebSocket se aplaza al spec 08. La compatibilidad se registra como no verificada para LocalStack Community 4.14; el contrato se implementará mediante un adaptador autorizado cuando corresponda.

## Consecuencias

No hay dependencia de AWS real para los specs 01 y 02. El secreto JWT debe definirse fuera del repositorio para entornos compartidos. Este proveedor es exclusivamente local y no es una decisión de producción.
