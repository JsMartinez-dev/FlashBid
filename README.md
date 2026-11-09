# Currículo — Bases de Datos NoSQL

## 🎯 Asignatura y objetivo general

**Asignatura:** Bases de Datos NoSQL — Énfasis en DynamoDB y Redis

**Objetivo general:** Brindar a los estudiantes una comprensión sólida y práctica de las bases de datos NoSQL, enfocándose en **DynamoDB como sistema de registro (source of truth)** y **Redis como sistema de acceso rápido y datos temporales**, desarrollando criterio arquitectónico para sistemas modernos y escalables.

> *En NoSQL no se diseñan tablas, se diseñan patrones de acceso.*

---

## 🧠 Módulo 1 – Fundamentos NoSQL

Establece las bases conceptuales antes de tocar cualquier tecnología.

### Contenidos
- Bases de datos relacionales y sus limitaciones
- Escalabilidad vertical vs. horizontal
- Consistencia eventual vs. consistencia fuerte
- Comparativa SQL vs. NoSQL: ventajas, desventajas y cuándo usar cada una
- Teorema CAP (enfoque aplicado)

### Ejemplos cotidianos
- WhatsApp, Netflix, juegos online, carrito de compras

### Ejemplos prácticos
- Login y manejo de sesiones → **Redis**
- Perfil de usuario persistente → **DynamoDB**

---

## 🗂️ Módulo 2 – Tipos de bases de datos NoSQL

Visión panorámica del ecosistema, sin profundizar en implementaciones específicas.

| Tipo | Ejemplo | Uso principal |
|---|---|---|
| Key–Value distribuido | DynamoDB | Persistencia altamente escalable |
| Key–Value in-memory | Redis | Latencia ultrabaja, datos temporales |
| Columnar | Cassandra | Grandes volúmenes de datos |
| Documental | MongoDB | Flexibilidad de esquema |
| Grafos | Neo4j | Relaciones complejas |

**Énfasis:**
- Cada tipo resuelve **problemas distintos** — no compiten entre sí
- DynamoDB y Redis **no son intercambiables**: ambos son key-value pero con propósitos completamente diferentes

---

## ⚡ Módulo 3 – DynamoDB

Núcleo del curso (~60–70% del tiempo total).

### Contenidos esenciales
- Tabla, ítem y atributos; tipos de datos
- Partition key y sort key
- Gestión de tablas: crear, describir, consultar
- Operaciones CRUD: `PutItem`, `GetItem`, `UpdateItem`, `DeleteItem`
- Consultas: `GetItem`, `Query`, `Scan` — cuándo usar cada una
- Índices secundarios: GSI y LSI
- Consistencia fuerte vs. eventual
- Modos de capacidad: On-Demand vs. Provisioned
- TTL (Time to Live)
- Transacciones: cuándo usarlas y cuándo evitarlas
- Streams *(opcional)*

### Errores comunes a desterrar
- "Una tabla por entidad" (mentalidad relacional)
- "Hagamos JOIN con Lambda"
- "Usar `Scan` con filtros en lugar de diseñar con claves"

### Ejercicios prácticos
Diseñar **antes** de escribir código:
- Estudiantes y notas
- Usuarios y órdenes
- Chat
- Likes / followers

> *Si tu diseño es malo, DynamoDB te castiga.*

---

## 🧱 Módulo 4 – Modelado de datos NoSQL

El módulo más importante. Los estudiantes aprenden a pensar como arquitectos.

### Conceptos
- Diseño orientado a consultas (Access Patterns)
- Single Table Design
- Desnormalización controlada
- Trade-off entre lecturas y escrituras
- Hot partitions y cómo evitarlas

### Taller principal
Diseñar **una sola tabla** que soporte:
- Usuarios
- Órdenes
- Órdenes por usuario
- Últimas N órdenes

> *DynamoDB se usa aquí como herramienta para enseñar arquitectura, no solo base de datos.*

---

## ⚡ Módulo 5 – Redis y su integración con DynamoDB

Redis se presenta como **complemento** de DynamoDB, no como sistema de registro. Este módulo cubre Redis de forma independiente y luego consolida su integración con DynamoDB.

### Redis (Remote Dictionary Server)
- ¿Qué es Redis y por qué importa en este stack?
- Estructuras de datos y comandos básicos: `String`, `Hash`, `List`, `Set`, `Sorted Set`
- Uso de Redis desde Python (`redis-py`)

### Patrones de caché
| Patrón | Descripción |
|---|---|
| Cache-Aside (Lazy Loading) | La app verifica caché; si miss, lee DynamoDB y guarda en Redis |
| Write-Through | Escribe en DynamoDB y Redis simultáneamente |
| Write-Behind (Write-Back) | Escribe en Redis primero; DynamoDB se actualiza en segundo plano |
| Read-Through | Redis actúa como proxy transparente hacia DynamoDB |

### Otros casos de uso de Redis
- Session store
- Rate limiting
- Contadores en tiempo real
- Pub/Sub *(introducción)*
- Locks simples

### Ejemplos
- Likes en tiempo real, rankings, conteo de vistas

### DynamoDB + Redis trabajando juntos

Flujo típico:
1. **Redis** → verificar caché (¿hit?)
2. **DynamoDB** → fuente de verdad si miss
3. **Redis** → almacenar resultado para próximas consultas

Decisiones de diseño:
- ¿Qué va en caché y qué no? (volatilidad, costo de lectura, TTL adecuado)
- Invalidación de caché: cuándo borrar o actualizar una clave
- Degraded mode: comportamiento de la app si Redis no está disponible

> *Redis no reemplaza a DynamoDB — lo complementa. DynamoDB es la fuente de verdad; Redis es la velocidad.*

---

## 🚀 Módulo 6 – Arquitectura Serverless del mundo real

### Arquitecturas estudiadas
- DynamoDB + Lambda
- DynamoDB + Redis + Lambda
- DynamoDB + Redis + Lambda + API Gateway
- Infraestructura como código con Python (CDK)

### Patrones
- Single Table Design en contexto serverless
- CQRS básico (separar lectura de escritura)
- Event-driven architecture con DynamoDB Streams

### Práctica sugerida
Implementación de un backend serverless de dominio real. Los estudiantes deben **justificar cada decisión de diseño**, no solo implementarla.

Dominios de ejemplo: e-commerce, chat, juegos, autenticación.

---

## 🏗️ Proyecto final

Cada grupo desarrolla una aplicación web de su elección que integre el stack completo del curso.

### Stack obligatorio
- **DynamoDB** — base de datos principal con Single Table Design
- **Redis** — caché con al menos un patrón justificado (Cache-Aside, Write-Through u otro)
- **Python** — lenguaje principal (Lambdas y CDK)
- **CDK** — infraestructura como código
- **API Gateway + Lambda** — arquitectura serverless
- **Docker Compose** — entorno local con emulador AWS (LocalStack o MiniStack)

### Arquitectura de contenedores

```
«host» Máquina del desarrollador
│
├── Terminal ──────────────────────────────────────────────┐
│                                                           │
│   «network» docker-compose-net                            │
│   ┌───────────────────────────────────────────────────┐  │
│   │                                                   │  │
│   │  «container» cdk-dev    «container» emulador      │  │
│   │  ┌────────────────┐     ┌──────────────────────┐  │  │
│   │  │ Python 3.11    │────▶│ LocalStack/MiniStack │  │  │
│   │  │ AWS CDK        │deploy│ API Gateway :4566   │  │  │
│   │  │ boto3,redis-py │     │ Lambda               │  │  │
│   │  │ Lambda handlers│──┐  │ DynamoDB             │  │  │
│   │  └────────────────┘  │  └──────────────────────┘  │  │
│   │                      │                             │  │
│   │                      │  «container» redis          │  │
│   │                      │  ┌──────────────────────┐  │  │
│   │                      └─▶│ redis:7-alpine :6379 │  │  │
│   │                         └──────────────────────┘  │  │
│   └───────────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────────────┘
```

### Estructura del proyecto base

```
proyecto-final/
├── docker-compose.yml      # Orquestación de los 3 contenedores
├── Dockerfile              # Imagen del contenedor cdk-dev
├── .env.example            # Variables de entorno de ejemplo
├── README.md
│
├── app/
│   ├── cdk.json            # Configuración CDK
│   ├── requirements.txt    # Dependencias Python
│   ├── infra/
│   │   ├── app.py          # Punto de entrada CDK
│   │   └── stack.py        # Stack: tabla + lambdas + API GW
│   └── lambdas/
│       ├── items/
│       │   ├── handler.py  # CRUD con patrón Cache-Aside
│       │   └── cache.py    # Abstracción de Redis
│       └── health/
│           └── handler.py  # Health check del servicio
│
└── tests/
    ├── conftest.py         # Fixtures compartidos
    ├── test_items.py       # Tests unitarios de la lambda
    └── test_cache.py       # Tests unitarios del caché
```

### Flujo de trabajo

1. `docker compose up --build` — levantar los tres contenedores
2. `cdklocal bootstrap` — preparar el emulador *(solo la primera vez)*
3. Escribir la infraestructura (`stack.py`) y los handlers Python
4. `cdklocal deploy` — desplegar en el emulador
5. Probar el API con `curl` o Postman → `localhost:4566`
6. Verificar el caché con `redis-cli KEYS *`
7. Ejecutar los tests con `python -m pytest tests/ -v`

### Elegir emulador

Solo cambia la línea `image:` en `docker-compose.yml`. El nombre del servicio, el puerto 4566 y todas las variables de entorno son idénticos en ambas opciones.

```yaml
# Opción A — LocalStack
image: localstack/localstack

# Opción B — MiniStack (más ligero)
image: ministack/ministack
```

### Variables de entorno clave

| Variable | Valor | Descripción |
|---|---|---|
| `AWS_ENDPOINT_URL` | `http://emulador:4566` | Redirige boto3 al emulador local |
| `REDIS_HOST` | `redis` | Nombre del servicio Redis en la red |
| `REDIS_PORT` | `6379` | Puerto Redis |
| `AWS_DEFAULT_REGION` | `us-east-1` | Región simulada |
| `AWS_ACCESS_KEY_ID` | `test` | Credencial dummy para el emulador |
| `TABLE_NAME` | Asignado por CDK | Nombre real de la tabla DynamoDB |

### Entregables

1. **Documento de diseño** — access patterns identificados, modelo de tabla (Single Table Design), justificación del patrón de caché elegido
2. **Código fuente** — repositorio con `docker-compose.yml`, `Dockerfile`, stack CDK, Lambdas y tests unitarios
3. **Demo funcional** — API desplegada localmente, flujo completo desde el request hasta la respuesta con caché. Se recomienda desarrollar un frontend sencillo (tecnología libre) para hacer la demo más dinámica e ilustrar el flujo completo desde la interfaz hasta DynamoDB y Redis
4. **Sustentación** — defensa oral de las decisiones arquitectónicas

### Criterios de evaluación

| Criterio |
|---|
| Diseño NoSQL: access patterns y Single Table Design |
| Implementación funcional: Lambdas, CDK, API Gateway |
| Patrón de caché con Redis: justificado y funcional |
| Calidad del código y tests |
| Sustentación y defensa oral |

---

## 🧪 Evaluación

| Instrumento | Módulos que cubre |
|---|---|
| Quiz conceptual (NoSQL, CAP, tipos de BD) | 1, 2 |
| Taller de modelado DynamoDB | 3, 4 |
| Taller Redis + integración con DynamoDB | 5 |
| Proyecto final (entregables + sustentación) | 3–6 |

---

## 📚 Herramientas

| Herramienta | Uso |
|---|---|
| **Docker + Docker Compose** | Orquestación del entorno local completo |
| **LocalStack** | Emulador AWS: Lambda, API Gateway, DynamoDB |
| **MiniStack** | Alternativa ligera a LocalStack (misma interfaz, mismo puerto 4566) |
| **AWS CDK + cdklocal** | Infraestructura como código apuntando al emulador local |
| **redis-py** | Cliente Python para Redis |
| **boto3** | SDK de AWS para Python (DynamoDB, Lambda) |
| **moto** | Mock de servicios AWS para tests unitarios |
| **fakeredis** | Mock de Redis para tests unitarios |
| **pytest** | Framework de tests |
| **Proyecto base** | Repositorio de arranque con la arquitectura del proyecto final lista para extender |
| **Draw.io** | Modelado de tablas NoSQL, arquitecturas y flujos de datos |
| **DynamoDB Local** | Alternativa ligera para practicar DynamoDB de forma aislada |
| **AWS Free Tier** | Prácticas opcionales en la nube real |
```