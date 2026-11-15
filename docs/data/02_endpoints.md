# 02 Contratos HTTP relacionados

| Ruta o contrato | Patrones |
|---|---|
| GET /health | PA-32 |
| Registro, login y logout del proveedor elegido | PA-02, PA-24 |
| GET /me | PA-01, PA-03; inicialización PA-04 cuando corresponda al flujo de alta |
| GET /me/wallet/movements | PA-05 |
| POST /auctions | PA-06 |
| DELETE /auctions/{id} | PA-07, PA-26, PA-30 |
| GET /auctions | PA-08, PA-10 |
| GET /auctions/{id} | PA-09, PA-10, PA-25 |
| POST /auctions/{id}/bids | PA-11 a PA-15, PA-26, PA-27, PA-30 |
| GET /auctions/{id}/bids | PA-16 |
| Cierre interno autorizado del worker (no endpoint público libre) | PA-17 a PA-19, PA-26 a PA-28, PA-30 |
| GET /me/auctions | PA-20 |
| GET /me/bids (contrato propuesto a formalizar) | PA-21 |
| GET /me/wins | PA-22 |
| Conexión, suscripción y reconexión WebSocket | PA-23, PA-29 a PA-31 |
