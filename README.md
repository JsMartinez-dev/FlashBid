# Asignatura: Bases de Datos NoSQL  
**Enfoque principal: DynamoDB y Redis**

## 🎯 Objetivo general
Brindar a los estudiantes una comprensión sólida y práctica de las bases de datos NoSQL, enfocándose en **DynamoDB como sistema de registro (source of truth)** y **Redis como sistema de acceso rápido y datos temporales**, desarrollando criterio arquitectónico para sistemas modernos y escalables.

---

## 🧠 Módulo 1 – Fundamentos NoSQL (conceptual, pero clave)

Antes de tocar DynamoDB, este módulo establece las bases conceptuales necesarias.

### Contenidos
- Bases de datos relacionales y sus limitaciones.
- Escalabilidad vertical vs escalabilidad horizontal
- Consistencia eventual vs consistencia fuerte
- Comparativa entre bases de datos SQL y NoSQL.
- Ventajas y desventajas bases de datos SQL y NoSQL.
- Cuando usar bases de datos SQL y NoSQL.
- Teorema CAP (enfoque aplicado)

### Ejemplos cotidianos
- WhatsApp
- Netflix
- Juegos online
- Carrito de compras

### Ejemplos prácticos
- Login y manejo de sesiones → **Redis**
- Perfil de usuario persistente → **DynamoDB**

> 👉 *Idea clave:*  
> **En NoSQL no se diseñan tablas, se diseñan patrones de acceso.**

---

## 🗂️ Módulo 2 – Tipos de bases de datos NoSQL (visión general)

Visión panorámica para entender el ecosistema, sin profundizar en implementaciones específicas.

| Tipo | Ejemplo | Uso principal |
|----|----|----|
| Key–Value distribuido | DynamoDB | Persistencia altamente escalable |
| Key–Value in-memory | Redis | Latencia ultrabaja, datos temporales |
| Columnar | Cassandra | Grandes volúmenes de datos |
| Grafos | Neo4j | Relaciones complejas |

### Enfatizar
- No compiten directamente entre sí
- Cada tipo resuelve **problemas distintos**
- DynamoDB y Redis **no son intercambiables**

> Ambos son key–value, pero con propósitos completamente diferentes.

---

## ⚡ Módulo 3 – DynamoDB (núcleo del curso)

Este módulo representa aproximadamente el **60–70% del curso**.

### Contenidos esenciales
- Tabla, item y atributos
- Tipos de datos.
- Partition key y sort key
- Principales comandos:
  - Gestión de Tablas (Crear, Consultar y Describir tabla)
  - Operaciones con Ítems (CRUD)
    - Crear/Reemplazar y actualizar items.
    - Consultas items (Get Item, Query, Scan)
- Índices secundarios: GSI y LSI
- Consistencia fuerte vs eventual
- On-Demand vs Provisioned capacity
- TTL
- Transacciones: cuándo usarlas y cuándo evitarlas
- Streams (Opcional)

### Errores comunes
- “Una tabla por entidad”
- “Hagamos JOIN con Lambda”
- “Usar filtros en lugar de claves”

### Ejercicios prácticos
Modelado de:
- Estudiantes y notas
- Usuarios y órdenes
- Chat
- Likes / followers

Diseñar el modelo **antes de escribir código**.

> 👉 *Mensaje clave:*  
> **Si tu diseño es malo, DynamoDB te castiga.**

---

## 🧱 Módulo 4 – Modelado de datos NoSQL (el módulo más importante)

En este módulo los estudiantes aprenden a **pensar como arquitectos**.

### Conceptos
- Diseño orientado a consultas (Access Patterns)
- Single Table Design
- Desnormalización controlada
- Trade-off entre lecturas y escrituras
- Hot partitions y cómo evitarlas

### Taller
Diseñar **una sola tabla** que soporte:
- Usuarios
- Órdenes
- Órdenes por usuario
- Últimas órdenes

> DynamoDB se usa aquí como herramienta para enseñar **arquitectura**, no solo base de datos.

---

## ⚡ Módulo 5 – Redis (como cache)

Redis se presenta como **complemento**, no como sistema de registro.

### Redis (Remote Dictionary Server).
- Redis como servicio de cache.
- Estructuras de datos en Redis.
  - String
  - Hash
  - List
  - Set
  - Sorted Set
  - Usar redis desde python.

### Patrones de diseño para Cache
- Cache-Aside (Lazy Loading)
- Write-Through
- Write-Behind (Write-Back)
- Read-Through

### Casos de uso
- Cache
- Session store
- Rate limiting
- Counters
- Pub/Sub (introducción)
- Locks simples

### Ejemplos
- Likes en tiempo real
- Rankings
- Conteo de vistas

---

## 🔄 Módulo 6 – DynamoDB + Redis (trabajando juntos)

Este módulo consolida el aprendizaje y diferencia el curso.

### Patrones
- Cache-aside
- Write-through
- Coordinación de TTL
- Estrategias de invalidación

### Flujo típico
1. Redis → verificar cache  
2. DynamoDB → source of truth  
3. Redis → almacenar resultado  

---

## 🚀 Módulo 7 – Arquitectura Serverless del mundo real

### Arquitecturas vistas
- DynamoDB + Lambda
- DynamoDB + Redis + Lambda
- DynamoDB + Redis + Lambda + API Gateway (opcional)
- Infraestructura como código con Python (CDK)

### Patrones
- Single Table Design
- CQRS básico
- Event-driven architecture

### Práctica sugerida
Implementación de un backend serverless simple:
- E-commerce
- Chat
- Juegos
- Autenticación

---

## 🧪 Evaluación

- 🧠 Quiz conceptual
- 🧩 Taller de modelado NoSQL
- 🚀 Proyecto final:
  - Diseñar una arquitectura usando DynamoDB + Redis
  - Justificar cada decisión técnica

---

## 💡 Valor del enfoque

Los estudiantes:
- No memorizan comandos
- Aprenden a **pensar en sistemas**
- Entienden arquitecturas reales
- Llegan mejor preparados al mundo cloud

---

## 📚 Herramientas

- **DynamoDB Local**  
  Para ejecutar y probar DynamoDB de forma local sin costos.

- **AWS Free Tier**  
  Para prácticas reales en la nube con límites gratuitos.

- **Diagramas (Draw.io)**  
  Para modelar tablas NoSQL, arquitecturas y flujos de datos.

  - **LocalStack**  
  Emulador local de servicios AWS. Permite probar infraestructura definida con CDK incluyendo:
  - Lambda  
  - API Gateway  
  - DynamoDB  
  Ideal para desarrollo y pruebas de integración sin desplegar en AWS real.

- **AWS CDK + cdklocal**  
  Uso del AWS CDK apuntando a LocalStack para desplegar infraestructura de forma local y reproducible.

- **AWS SAM CLI (opcional)**  
  Permite ejecutar funciones Lambda y APIs de forma local a partir de plantillas sintetizadas desde CDK (`cdk synth`).  
  Útil para debugging y pruebas rápidas de endpoints.

- **Redis (Docker / Local)**  
  Redis se ejecuta localmente (por ejemplo con Docker) para simular:
  - Cache
  - Session store
  - Rate limiting
  - Counters  
  Se integra con DynamoDB como sistema de persistencia principal.

- **Docker / Docker Compose**  
  Orquestación del entorno local completo:
  - LocalStack  
  - Redis  
  - Servicios auxiliares  
  Facilita levantar y apagar el stack completo de desarrollo.
