# CLAUDE.md — Sistema de Gestión de Tickets
## Guía Maestra del Proyecto · Smart Security (v1.0)

> **Propósito de este documento:** Guía técnica completa para Claude Code. Cada sección contiene el contexto, decisiones de arquitectura, estándares y tareas necesarias para construir el sistema de manera eficiente, sin ambigüedades y con máxima reusabilidad multi-tenant.

---

## Tabla de Contenidos

1. [Contexto del Proyecto](#1-contexto-del-proyecto)
2. [Visión Multi-Tenant](#2-visión-multi-tenant)
3. [Requerimientos Funcionales](#3-requerimientos-funcionales)
4. [Requerimientos No Funcionales](#4-requerimientos-no-funcionales)
5. [Arquitectura del Sistema](#5-arquitectura-del-sistema)
6. [Stack Tecnológico](#6-stack-tecnológico)
7. [Modelo de Datos](#7-modelo-de-datos)
8. [API — Endpoints](#8-api--endpoints)
9. [Estándares de Programación](#9-estándares-de-programación)
10. [CI/CD Pipeline](#10-cicd-pipeline)
11. [Infraestructura y Despliegue](#11-infraestructura-y-despliegue)
12. [Plan de Trabajo — Tareas Detalladas](#12-plan-de-trabajo--tareas-detalladas)

---

## 1. Contexto del Proyecto

### Cliente inicial: Smart Security
Empresa colombiana de seguridad privada con ~15 usuarios administrativos. Actualmente gestiona todas las solicitudes internas por correo electrónico, lo que genera pérdida de información, falta de trazabilidad y dificultad para medir el desempeño de los equipos.

### Problema que resuelve
- Solicitudes perdidas o sin respuesta en el correo
- Sin asignación clara de responsables
- Sin visibilidad del estado de una solicitud
- Sin métricas de productividad ni cumplimiento
- Sin historial auditable de lo ocurrido en cada caso

### Solución
Plataforma web de gestión de tickets internos con:
- Creación y seguimiento de solicitudes
- Enrutamiento automático por área
- Notificaciones en tiempo real
- Tickets recurrentes automatizados por calendario
- Dashboard de métricas y reportes semanales
- Medición de comportamiento por usuario (abuso de urgencia)
- Integración con Microsoft 365 (Azure AD) para autenticación

---

## 2. Visión Multi-Tenant

### Principio fundamental
**El sistema debe ser construido desde el día 1 como una plataforma multi-tenant.** Smart Security es el primer cliente, pero la arquitectura debe permitir incorporar nuevas empresas con configuración mínima, sin tocar código.

### Qué significa multi-tenant en este contexto

Cada empresa (tenant) tiene:
- Su propio subdominio: `tickets.smartsecurity.com.co`, `tickets.otraempresa.com`
- Sus propios usuarios, áreas, categorías y configuraciones
- Datos completamente aislados de otros tenants
- Posibilidad de login propio (usuario/contraseña) o SSO (M365, Google)
- Su propio esquema de SLAs, prioridades y notificaciones
- Branding básico configurable (logo, nombre, color primario)

### Lo que NO cambia entre tenants
- Código de la aplicación
- Lógica de negocio core
- Infraestructura base
- Pipeline de CI/CD

### Patrón de aislamiento de datos
Se usará **Row-Level Security (RLS)** en PostgreSQL. Cada tabla principal incluye la columna `tenant_id`. Todas las queries deben filtrar por `tenant_id` de manera automática usando un middleware que lo inyecta desde el JWT del usuario autenticado.

```
Tenant A (Smart Security)     Tenant B (Otra Empresa)
tenant_id = "smart-security"  tenant_id = "otra-empresa"
Misma DB, mismas tablas       Misma DB, mismas tablas
Datos 100% aislados por RLS   Datos 100% aislados por RLS
```

### Configuración por tenant (tabla `tenant_config`)
Cada tenant puede configurar sin tocar código:
- Nombre de la empresa y logo
- Color primario de la UI
- Método de autenticación (local / Azure AD / Google)
- Categorías de tickets habilitadas
- Definición de SLAs por categoría
- Umbral de alerta de abuso de urgencia (% configurable)
- Días hábiles y festivos (para cálculo de SLA)
- Idioma de la interfaz

---

## 3. Requerimientos Funcionales

### RF-01 — Autenticación y Usuarios
- Login via Microsoft 365 (Azure AD / OAuth2 + OIDC) — Smart Security
- Login via usuario/contraseña para tenants sin M365
- Soporte futuro para Google Workspace SSO
- Usuarios "archivados": conservan historial, no aparecen en listas de etiquetado
- Roles: `admin`, `supervisor`, `agent`, `requester`
- Un usuario puede pertenecer a múltiples áreas
- El área principal define la bandeja de trabajo principal
- Gestión de usuarios delegada al rol `admin` del tenant

### RF-02 — Gestión de Tickets
- Crear ticket con: título, descripción, categoría, prioridad, área destino, adjuntos
- Prioridades: `low`, `medium`, `high`, `urgent`
- Estados: `open` → `in_progress` → `pending` → `escalated` → `resolved` → `closed`
- Reapertura de ticket por el solicitante con comentario obligatorio
- Cierre automático tras X días en estado `resolved` sin confirmación (configurable por tenant)
- Transferencia/escalamiento a otro agente o área
- Etiquetado de usuarios (@menciones) en comentarios — solo usuarios activos
- Adjuntos: imágenes y PDFs, máximo 10 MB por archivo
- Número de ticket único y secuencial por tenant: `#TK-0001`

### RF-03 — Comentarios e Historial
- Comentarios públicos (visibles para solicitante y agente)
- Notas internas (visibles solo para el equipo, no para el solicitante)
- Historial inmutable de todos los cambios de estado con timestamp y responsable
- Cada acción queda registrada: asignación, cambio de estado, escalamiento, cierre

### RF-04 — Enrutamiento Automático
- Al crear un ticket, se asigna automáticamente al área correspondiente según la categoría
- Si el área tiene un agente por defecto configurado, se asigna directamente
- Si no, queda en cola del área sin agente asignado (visible para supervisores)
- Reglas de enrutamiento configurables por tenant sin tocar código

### RF-05 — Tickets Recurrentes
- Crear plantillas de tickets con frecuencia: diaria, semanal, mensual, o día específico del mes
- Ejemplo: "Pago de nómina" — se crea automáticamente el día 28 de cada mes
- Si la fecha cae en fin de semana o festivo, crear el día hábil anterior (configurable)
- Las plantillas son gestionadas por el `admin` del tenant
- Los tickets generados automáticamente siguen el flujo normal

### RF-06 — Notificaciones
- Notificación en tiempo real dentro del aplicativo (WebSocket)
- Si el ticket no tiene actividad en X horas/días (según SLA), envío automático por correo
- Correo al solicitante cuando: ticket creado, estado cambia, ticket resuelto
- Correo al agente cuando: ticket asignado, comentario nuevo, ticket escalado
- Correo configurable por tenant (plantillas HTML personalizables)
- **Envío diferido fuera de horario laboral**: si la notificación se genera fuera del horario hábil del tenant, el correo se programa para enviarse al inicio del próximo día hábil. La notificación en la app se entrega de todas formas en tiempo real.

### RF-07 — SLAs (Acuerdos de Nivel de Servicio)
- Definir tiempo máximo de resolución por categoría y/o prioridad
- El SLA corre en horas/días hábiles (excluye fines de semana y festivos del tenant)
- Cuando un ticket supera el 80% del tiempo SLA → alerta visual en la UI
- Cuando supera el 100% → alerta crítica + notificación al supervisor
- Historial de cumplimiento de SLA por ticket y por agente

### RF-08 — Dashboard y Reportes
- Panel de control en tiempo real con:
  - Tickets abiertos, en proceso, resueltos hoy
  - Tiempo promedio de resolución
  - Tickets por área (gráfica de barras)
  - Distribución por estado (gráfica donut)
  - Tickets próximos a vencer SLA
  - Actividad reciente del equipo
- Reporte semanal automático enviado por correo (configurar destinatarios)
- Vista de métricas por agente: volumen, tiempo promedio, tasa de resolución
- **Reporte especial CEO**: métricas de abuso de urgencia por líder/área

### RF-09 — Medición de Abuso de Urgencia
- Calcular el porcentaje de tickets `urgent` vs total por usuario en un período
- Si supera el umbral configurado (ej. 50%), registrar alerta
- Solo la CEO (rol configurable) puede ver este reporte
- Mostrar tendencia: el porcentaje mejoró o empeoró vs período anterior
- No notificar al líder directamente — solo visible para quien tenga permiso

### RF-10 — Gestión Multi-Área de Usuarios
- Un usuario puede estar en múltiples áreas
- Tiene un área principal (`primary_area`)
- Recibe notificaciones de tickets de todas sus áreas
- Su bandeja de trabajo muestra tickets de todas sus áreas con etiqueta del área correspondiente
- Puede filtrar su bandeja por área

### RF-11 — Administración del Tenant
- Panel de administración solo para rol `admin`
- Gestión de usuarios: crear, editar, archivar, asignar áreas y roles
- Gestión de áreas: crear, editar, asignar responsable
- Gestión de categorías: crear, editar, configurar enrutamiento
- Configuración de SLAs por categoría
- Gestión de plantillas de tickets recurrentes
- Configuración de notificaciones y correos
- Configuración de branding (logo, nombre, color)

---

## 4. Requerimientos No Funcionales

### RNF-01 — Seguridad
- HTTPS obligatorio (certificado SSL via Let's Encrypt)
- JWT con refresh tokens (access token: 15 min, refresh: 7 días)
- CSRF protection en todos los endpoints que mutan datos
- Rate limiting en endpoints de autenticación (máx. 10 intentos/min por IP)
- Row-Level Security en PostgreSQL — todas las queries filtran por `tenant_id`
- Contraseñas hasheadas con bcrypt (cost factor 12)
- Archivos adjuntos almacenados fuera del webroot, acceso solo via URL firmada temporal
- Logs de auditoría para acciones sensibles (login, cambio de rol, archivado de usuario)

### RNF-02 — Rendimiento
- Tiempo de respuesta de API < 300ms en el percentil 95 bajo carga normal
- WebSockets para notificaciones en tiempo real (no polling)
- Paginación en todos los listados (máximo 50 registros por página)
- Índices en columnas de alta frecuencia: `tenant_id`, `status`, `assigned_to`, `created_at`
- Caché de configuraciones de tenant en Redis (TTL: 5 minutos)

### RNF-03 — Disponibilidad
- Target: 99.5% uptime mensual
- Health check endpoint: `GET /health`
- Reinicio automático de contenedores en caso de fallo (Docker restart policy)
- Backups automáticos de base de datos diarios (retención: 30 días)

### RNF-04 — Escalabilidad
- Arquitectura containerizada (Docker) lista para escalar horizontalmente
- Variables de entorno para toda configuración sensible (nunca hardcodeada)
- Sin estado en el servidor de aplicación (stateless) — el estado vive en DB y Redis

### RNF-05 — Mantenibilidad
- Cobertura de tests: mínimo 80% en lógica de negocio crítica
- Documentación de API generada automáticamente (OpenAPI/Swagger)
- Migraciones de base de datos versionadas y reversibles
- Logs estructurados en JSON con niveles: DEBUG, INFO, WARN, ERROR

---

## 5. Arquitectura del Sistema

### Diagrama General

```
┌─────────────────────────────────────────────────────────────┐
│                        INTERNET                              │
└──────────────────────────┬──────────────────────────────────┘
                           │ HTTPS
                    ┌──────▼──────┐
                    │   NGINX     │  Reverse Proxy + SSL
                    │  (Docker)   │  Termina SSL, enruta por
                    └──────┬──────┘  subdominio a cada tenant
                           │
          ┌────────────────┼────────────────┐
          │                │                │
   ┌──────▼──────┐  ┌──────▼──────┐  ┌─────▼──────┐
   │  Frontend   │  │   Backend   │  │  Workers   │
   │  Next.js    │  │  FastAPI    │  │  Celery    │
   │  (Docker)   │  │  (Docker)   │  │  (Docker)  │
   └─────────────┘  └──────┬──────┘  └─────┬──────┘
                           │               │
              ┌────────────┼───────────────┘
              │            │
       ┌──────▼───┐  ┌─────▼──────┐  ┌──────────────┐
       │PostgreSQL│  │   Redis    │  │   Storage    │
       │(Docker)  │  │  (Docker)  │  │ (VPS local / │
       └──────────┘  └────────────┘  │  S3-compat)  │
                                     └──────────────┘
```

### Descripción de cada capa

#### NGINX — Reverse Proxy
- Única puerta de entrada al sistema
- Termina SSL con certificados Let's Encrypt (Certbot automático)
- Enruta por subdominio: `tickets.smartsecurity.com.co` → backend del tenant
- Sirve archivos estáticos del frontend
- Rate limiting a nivel de proxy
- Compresión gzip

#### Frontend — Next.js (App Router)
- Single Page Application con Server Side Rendering para SEO y performance
- Comunicación con backend via REST API + WebSockets
- Manejo de estado global con Zustand
- Autenticación manejada por NextAuth.js (soporta Azure AD y credentials)
- UI construida con shadcn/ui + Tailwind CSS
- Internacionalización preparada (i18n) para futuros tenants en otros idiomas

#### Backend — FastAPI (Python)
- API REST stateless
- Autenticación: valida JWT, inyecta `tenant_id` y `user` en cada request via middleware
- Toda la lógica de negocio vive aquí
- WebSocket endpoint para notificaciones en tiempo real
- Generación automática de documentación OpenAPI en `/docs`
- Workers Celery para tareas asíncronas (correos, tickets recurrentes, reportes)

#### PostgreSQL — Base de Datos
- Única instancia con RLS habilitado
- Todas las tablas tienen columna `tenant_id`
- Migraciones gestionadas con Alembic
- Backups automáticos con pg_dump (cron diario)

#### Redis
- Cola de tareas para Celery (tickets recurrentes, envío de correos, reportes)
- Caché de configuraciones de tenant
- Almacenamiento de refresh tokens (con TTL)
- Canal de WebSocket pub/sub

#### Celery Workers
- Procesamiento asíncrono desacoplado del request/response
- Tareas principales:
  - `send_notification_email` — envío de correos
  - `create_recurring_ticket` — cron job para tickets recurrentes
  - `send_weekly_report` — reporte semanal automático
  - `check_sla_violations` — revisión periódica de SLAs vencidos
  - `auto_close_resolved_tickets` — cierre automático de tickets resueltos

#### Storage
- Almacenamiento de archivos adjuntos
- En VPS: volumen Docker local montado
- Migrable a MinIO (S3-compatible self-hosted) o AWS S3 sin cambiar código
- Acceso via URL firmada con expiración (nunca URL directa al archivo)

### Patrón de Arquitectura Backend

Se usará **arquitectura en capas** dentro del backend:

```
HTTP Request
     │
     ▼
┌─────────────┐
│   Router    │  Define endpoints, valida esquemas Pydantic
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   Service   │  Lógica de negocio, orquesta operaciones
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ Repository  │  Acceso a datos, queries SQL, RLS enforcement
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Database   │  PostgreSQL con RLS
└─────────────┘
```

- **Router**: Solo recibe, valida y delega. Sin lógica de negocio.
- **Service**: Toda la lógica vive aquí. No accede directamente a la DB.
- **Repository**: Toda query SQL vive aquí. Siempre filtra por `tenant_id`.
- Esta separación permite testear servicios con repositorios mock fácilmente.

---

## 6. Stack Tecnológico

### Backend
| Tecnología | Versión | Propósito |
|---|---|---|
| Python | 3.12 | Lenguaje base |
| FastAPI | 0.111+ | Framework API REST |
| SQLAlchemy | 2.0+ | ORM (async) |
| Alembic | 1.13+ | Migraciones de DB |
| Pydantic | 2.0+ | Validación y esquemas |
| Celery | 5.3+ | Tareas asíncronas |
| Redis (redis-py) | 5.0+ | Cola + caché |
| python-jose | 3.3+ | JWT |
| passlib + bcrypt | latest | Hash de contraseñas |
| httpx | 0.27+ | Cliente HTTP (para Azure AD) |
| pytest + pytest-asyncio | latest | Testing |

### Frontend
| Tecnología | Versión | Propósito |
|---|---|---|
| Next.js | 14+ (App Router) | Framework React |
| TypeScript | 5.0+ | Tipado estático |
| Tailwind CSS | 3.4+ | Estilos utility-first |
| shadcn/ui | latest | Componentes UI |
| Zustand | 4.5+ | Estado global |
| NextAuth.js | 4.24+ | Autenticación (Azure AD + credentials) |
| React Query (TanStack) | 5.0+ | Server state, caché, fetching |
| Socket.io-client | 4.7+ | WebSockets notificaciones |
| Recharts | 2.12+ | Gráficas del dashboard |
| React Hook Form + Zod | latest | Formularios y validación |
| date-fns | 3.0+ | Manejo de fechas |

### Infraestructura
| Tecnología | Propósito |
|---|---|
| Docker + Docker Compose | Containerización completa |
| NGINX | Reverse proxy + SSL |
| PostgreSQL 16 | Base de datos principal |
| Redis 7 | Caché + cola de tareas |
| Certbot | Certificados SSL automáticos |
| GitHub Actions | CI/CD pipeline |

---

## 7. Modelo de Datos

### Convenciones
- Todas las tablas tienen `id` UUID como PK (no autoincremental, más seguro y portable)
- Todas las tablas tienen `tenant_id UUID NOT NULL` con FK a `tenants`
- `created_at` y `updated_at` en todas las tablas (auto-gestionados)
- Soft delete: columna `deleted_at TIMESTAMP NULL` — nunca borrar físicamente
- Nombres de tablas en snake_case plural inglés

---

### Tabla: `tenants`
```sql
CREATE TABLE tenants (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slug            VARCHAR(100) UNIQUE NOT NULL,  -- 'smart-security'
    name            VARCHAR(255) NOT NULL,
    subdomain       VARCHAR(100) UNIQUE NOT NULL,  -- 'tickets.smartsecurity.com.co'
    is_active       BOOLEAN DEFAULT true,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);
```

### Tabla: `tenant_configs`
```sql
CREATE TABLE tenant_configs (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id                   UUID NOT NULL REFERENCES tenants(id),
    -- Branding
    logo_url                    TEXT,
    primary_color               VARCHAR(7) DEFAULT '#1565C0',
    -- Auth
    auth_method                 VARCHAR(20) DEFAULT 'local', -- 'local' | 'azure_ad' | 'google'
    azure_tenant_id             TEXT,
    azure_client_id             TEXT,
    azure_client_secret         TEXT,  -- Encriptado en la app
    -- Comportamiento
    auto_close_days             INTEGER DEFAULT 3,
    urgency_abuse_threshold     INTEGER DEFAULT 50, -- Porcentaje
    urgency_report_visible_to   UUID,  -- user_id que puede ver el reporte (CEO)
    -- Festivos y zona horaria
    timezone                    VARCHAR(50) DEFAULT 'America/Bogota',
    working_hours_start         TIME DEFAULT '08:00',
    working_hours_end           TIME DEFAULT '18:00',
    working_days                INTEGER[] DEFAULT '{1,2,3,4,5}', -- Lunes a viernes
    -- Notificaciones
    weekly_report_enabled       BOOLEAN DEFAULT true,
    weekly_report_day           INTEGER DEFAULT 1, -- Lunes
    weekly_report_recipients    TEXT[], -- Array de emails
    created_at                  TIMESTAMPTZ DEFAULT NOW(),
    updated_at                  TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(tenant_id)
);
```

### Tabla: `users`
```sql
CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id),
    email           VARCHAR(255) NOT NULL,
    full_name       VARCHAR(255) NOT NULL,
    password_hash   TEXT,               -- NULL si usa SSO
    azure_oid       TEXT,               -- Azure AD Object ID
    role            VARCHAR(20) NOT NULL DEFAULT 'requester',
                    -- 'admin' | 'supervisor' | 'agent' | 'requester'
    is_active       BOOLEAN DEFAULT true,
    is_archived     BOOLEAN DEFAULT false, -- Soft delete para ex-empleados
    avatar_url      TEXT,
    last_login_at   TIMESTAMPTZ,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW(),
    deleted_at      TIMESTAMPTZ,
    UNIQUE(tenant_id, email)
);
```

### Tabla: `areas`
```sql
CREATE TABLE areas (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id),
    name            VARCHAR(255) NOT NULL,
    description     TEXT,
    manager_id      UUID REFERENCES users(id), -- Responsable del área
    is_active       BOOLEAN DEFAULT true,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(tenant_id, name)
);
```

### Tabla: `user_areas` (relación N:N)
```sql
CREATE TABLE user_areas (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id),
    user_id         UUID NOT NULL REFERENCES users(id),
    area_id         UUID NOT NULL REFERENCES areas(id),
    is_primary      BOOLEAN DEFAULT false,  -- Área principal del usuario
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, area_id)
);
```

### Tabla: `categories`
```sql
CREATE TABLE categories (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id),
    name                VARCHAR(255) NOT NULL,
    description         TEXT,
    default_area_id     UUID REFERENCES areas(id), -- Enrutamiento automático
    default_agent_id    UUID REFERENCES users(id), -- Agente por defecto (opcional)
    requires_approval   BOOLEAN DEFAULT false,
    approver_role       VARCHAR(20),               -- Qué rol aprueba
    is_active           BOOLEAN DEFAULT true,
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(tenant_id, name)
);
```

### Tabla: `slas`
```sql
CREATE TABLE slas (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id),
    category_id         UUID REFERENCES categories(id),  -- NULL = aplica a todas
    priority            VARCHAR(20),  -- NULL = aplica a todas las prioridades
    response_hours      INTEGER NOT NULL,    -- Tiempo para primera respuesta
    resolution_hours    INTEGER NOT NULL,    -- Tiempo para resolver
    is_active           BOOLEAN DEFAULT true,
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW()
);
```

### Tabla: `tickets`
```sql
CREATE TABLE tickets (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id),
    ticket_number       VARCHAR(20) NOT NULL,   -- '#TK-0001' único por tenant
    title               VARCHAR(500) NOT NULL,
    description         TEXT NOT NULL,
    status              VARCHAR(20) NOT NULL DEFAULT 'open',
                        -- 'open'|'in_progress'|'pending'|'escalated'|'resolved'|'closed'
    priority            VARCHAR(20) NOT NULL DEFAULT 'medium',
                        -- 'low'|'medium'|'high'|'urgent'
    category_id         UUID REFERENCES categories(id),
    area_id             UUID REFERENCES areas(id),
    requester_id        UUID NOT NULL REFERENCES users(id),
    assigned_to         UUID REFERENCES users(id),
    -- SLA tracking
    sla_id              UUID REFERENCES slas(id),
    sla_due_at          TIMESTAMPTZ,
    sla_breached        BOOLEAN DEFAULT false,
    first_response_at   TIMESTAMPTZ,
    resolved_at         TIMESTAMPTZ,
    closed_at           TIMESTAMPTZ,
    -- Recurrencia
    recurring_template_id UUID,  -- FK a recurring_templates si fue auto-generado
    -- Metadata
    is_recurring_instance BOOLEAN DEFAULT false,
    reopen_count        INTEGER DEFAULT 0,
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW(),
    deleted_at          TIMESTAMPTZ,
    UNIQUE(tenant_id, ticket_number)
);
```

### Tabla: `ticket_comments`
```sql
CREATE TABLE ticket_comments (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id),
    ticket_id       UUID NOT NULL REFERENCES tickets(id),
    author_id       UUID NOT NULL REFERENCES users(id),
    body            TEXT NOT NULL,
    is_internal     BOOLEAN DEFAULT false,  -- Nota interna vs comentario público
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW(),
    deleted_at      TIMESTAMPTZ
);
```

### Tabla: `ticket_history`
```sql
CREATE TABLE ticket_history (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id),
    ticket_id       UUID NOT NULL REFERENCES tickets(id),
    actor_id        UUID REFERENCES users(id),  -- NULL = sistema
    action          VARCHAR(50) NOT NULL,
                    -- 'created'|'status_changed'|'assigned'|'priority_changed'
                    -- 'escalated'|'comment_added'|'resolved'|'closed'|'reopened'
    old_value       JSONB,
    new_value       JSONB,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
```

### Tabla: `ticket_attachments`
```sql
CREATE TABLE ticket_attachments (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id),
    ticket_id       UUID NOT NULL REFERENCES tickets(id),
    comment_id      UUID REFERENCES ticket_comments(id),  -- NULL si es del ticket
    filename        VARCHAR(255) NOT NULL,
    file_path       TEXT NOT NULL,       -- Ruta interna en el storage
    file_size       INTEGER NOT NULL,    -- Bytes
    mime_type       VARCHAR(100) NOT NULL,
    uploaded_by     UUID NOT NULL REFERENCES users(id),
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
```

### Tabla: `recurring_templates`
```sql
CREATE TABLE recurring_templates (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id),
    title               VARCHAR(500) NOT NULL,
    description         TEXT,
    category_id         UUID REFERENCES categories(id),
    area_id             UUID REFERENCES areas(id),
    priority            VARCHAR(20) DEFAULT 'medium',
    assigned_to         UUID REFERENCES users(id),
    -- Configuración de recurrencia
    recurrence_type     VARCHAR(20) NOT NULL,
                        -- 'daily'|'weekly'|'monthly'|'day_of_month'
    recurrence_value    INTEGER,    -- Para monthly: día del mes (ej. 28)
    recurrence_day      INTEGER,    -- Para weekly: día de la semana (0=lunes)
    if_holiday_action   VARCHAR(20) DEFAULT 'previous_business_day',
                        -- 'previous_business_day'|'next_business_day'|'same_day'
    is_active           BOOLEAN DEFAULT true,
    last_run_at         TIMESTAMPTZ,
    next_run_at         TIMESTAMPTZ,
    created_by          UUID NOT NULL REFERENCES users(id),
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW()
);
```

### Tabla: `notifications`
```sql
CREATE TABLE notifications (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id),
    user_id         UUID NOT NULL REFERENCES users(id),
    ticket_id       UUID REFERENCES tickets(id),
    type            VARCHAR(50) NOT NULL,
                    -- 'ticket_created'|'ticket_assigned'|'status_changed'
                    -- 'comment_added'|'sla_warning'|'sla_breached'|'ticket_resolved'
    title           VARCHAR(255) NOT NULL,
    body            TEXT,
    is_read         BOOLEAN DEFAULT false,
    read_at         TIMESTAMPTZ,
    -- Envío diferido (correos fuera de horario hábil)
    scheduled_for   TIMESTAMPTZ,    -- NULL = enviar de inmediato; NON-NULL = enviar a esta hora
    email_sent_at   TIMESTAMPTZ,    -- NULL = aún no enviado
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Índice parcial para consulta eficiente de emails pendientes
CREATE INDEX ix_notifications_scheduled_for
    ON notifications(scheduled_for)
    WHERE scheduled_for IS NOT NULL AND email_sent_at IS NULL;
```

### Índices críticos
```sql
-- Todos los queries principales filtran por tenant_id primero
CREATE INDEX idx_tickets_tenant_status ON tickets(tenant_id, status);
CREATE INDEX idx_tickets_tenant_assigned ON tickets(tenant_id, assigned_to);
CREATE INDEX idx_tickets_tenant_created ON tickets(tenant_id, created_at DESC);
CREATE INDEX idx_tickets_sla_due ON tickets(tenant_id, sla_due_at) WHERE sla_breached = false;
CREATE INDEX idx_notifications_user_unread ON notifications(tenant_id, user_id, is_read) WHERE is_read = false;
CREATE INDEX idx_comments_ticket ON ticket_comments(ticket_id, created_at);
CREATE INDEX idx_history_ticket ON ticket_history(ticket_id, created_at DESC);
CREATE INDEX idx_users_tenant_active ON users(tenant_id, is_archived) WHERE deleted_at IS NULL;
```

---

## 8. API — Endpoints

### Convenciones
- Base URL: `https://{subdominio}/api/v1`
- Autenticación: `Authorization: Bearer {access_token}` en todos los endpoints protegidos
- Formato: JSON en request y response
- Errores: `{ "detail": "Mensaje de error", "code": "ERROR_CODE" }`
- Paginación: `?page=1&size=20` → responde con `{ "items": [], "total": 0, "page": 1, "pages": 1 }`

### Auth
```
POST   /auth/login              # Login con usuario/contraseña
POST   /auth/login/azure        # Iniciar flujo OAuth2 con Azure AD
GET    /auth/callback/azure     # Callback de Azure AD
POST   /auth/refresh            # Renovar access token con refresh token
POST   /auth/logout             # Revocar refresh token
GET    /auth/me                 # Usuario autenticado actual
```

### Tickets
```
GET    /tickets                 # Listar tickets (filtros: status, priority, area, category, assignee)
POST   /tickets                 # Crear ticket
GET    /tickets/{id}            # Detalle de ticket
PATCH  /tickets/{id}            # Actualizar ticket (status, priority, assignee, etc.)
DELETE /tickets/{id}            # Archivar ticket (soft delete, solo admin)

POST   /tickets/{id}/comments   # Agregar comentario o nota interna
GET    /tickets/{id}/comments   # Listar comentarios del ticket
PATCH  /tickets/{id}/comments/{comment_id}  # Editar comentario (solo autor, < 5 min)

GET    /tickets/{id}/history    # Historial de cambios del ticket
POST   /tickets/{id}/attachments # Subir adjunto
GET    /tickets/{id}/attachments/{att_id}/download  # URL firmada para descarga

POST   /tickets/{id}/assign     # Asignar a agente
POST   /tickets/{id}/escalate   # Escalar a supervisor o área
POST   /tickets/{id}/resolve    # Marcar como resuelto
POST   /tickets/{id}/close      # Cerrar ticket
POST   /tickets/{id}/reopen     # Reabrir ticket (requiere motivo)
```

### Dashboard y Reportes
```
GET    /dashboard/summary       # Métricas generales en tiempo real
GET    /dashboard/tickets-by-area    # Distribución por área
GET    /dashboard/tickets-by-status  # Distribución por estado
GET    /dashboard/sla-compliance     # Cumplimiento de SLAs
GET    /dashboard/agent-performance  # Métricas por agente
GET    /dashboard/urgency-abuse      # Reporte CEO (requiere permiso especial)
GET    /reports/weekly          # Datos del reporte semanal
```

### Usuarios y Áreas
```
GET    /users                   # Listar usuarios activos del tenant
POST   /users                   # Crear usuario (admin)
GET    /users/{id}              # Perfil de usuario
PATCH  /users/{id}              # Actualizar usuario
POST   /users/{id}/archive      # Archivar usuario (ex-empleado)

GET    /areas                   # Listar áreas del tenant
POST   /areas                   # Crear área (admin)
PATCH  /areas/{id}              # Actualizar área
GET    /areas/{id}/members      # Miembros del área
POST   /areas/{id}/members      # Agregar miembro al área
DELETE /areas/{id}/members/{user_id}  # Remover miembro
```

### Configuración (Admin)
```
GET    /admin/config            # Configuración del tenant
PATCH  /admin/config            # Actualizar configuración
GET    /admin/categories        # Listar categorías
POST   /admin/categories        # Crear categoría
PATCH  /admin/categories/{id}   # Editar categoría
GET    /admin/slas              # Listar SLAs configurados
POST   /admin/slas              # Crear SLA
PATCH  /admin/slas/{id}         # Editar SLA
GET    /admin/recurring         # Listar plantillas recurrentes
POST   /admin/recurring         # Crear plantilla recurrente
PATCH  /admin/recurring/{id}    # Editar plantilla
DELETE /admin/recurring/{id}    # Desactivar plantilla
```

### Notificaciones
```
GET    /notifications           # Listar notificaciones del usuario autenticado
POST   /notifications/read-all  # Marcar todas como leídas
PATCH  /notifications/{id}/read # Marcar una como leída
GET    /notifications/ws        # WebSocket endpoint (upgrade)
```

### Sistema
```
GET    /health                  # Health check (sin auth)
GET    /docs                    # Swagger UI (solo en desarrollo)
```

---

## 9. Estándares de Programación

### Estructura de directorios

#### Backend
```
backend/
├── app/
│   ├── main.py                 # Entrada FastAPI, registro de routers
│   ├── config.py               # Settings con Pydantic BaseSettings
│   ├── database.py             # Sesión async de SQLAlchemy
│   ├── dependencies.py         # Dependencias FastAPI (get_current_user, etc.)
│   ├── middleware/
│   │   ├── tenant.py           # Inyecta tenant_id en cada request
│   │   └── logging.py          # Logging estructurado
│   ├── models/                 # Modelos SQLAlchemy (uno por tabla)
│   │   ├── base.py             # BaseModel con id, tenant_id, timestamps
│   │   ├── tenant.py
│   │   ├── user.py
│   │   ├── ticket.py
│   │   └── ...
│   ├── schemas/                # Schemas Pydantic (Request/Response)
│   │   ├── ticket.py           # TicketCreate, TicketUpdate, TicketResponse
│   │   └── ...
│   ├── routers/                # Endpoints FastAPI
│   │   ├── auth.py
│   │   ├── tickets.py
│   │   ├── dashboard.py
│   │   └── ...
│   ├── services/               # Lógica de negocio
│   │   ├── ticket_service.py
│   │   ├── notification_service.py
│   │   ├── sla_service.py
│   │   └── ...
│   ├── repositories/           # Acceso a datos
│   │   ├── ticket_repository.py
│   │   └── ...
│   ├── tasks/                  # Tareas Celery
│   │   ├── celery_app.py
│   │   ├── email_tasks.py
│   │   ├── notification_tasks.py  # send_scheduled_notifications (cada 5 min)
│   │   ├── recurring_tasks.py
│   │   ├── report_tasks.py
│   │   └── sla_tasks.py
│   └── utils/
│       ├── security.py         # JWT, hashing
│       ├── email.py            # Envío de correos
│       └── storage.py          # Manejo de archivos
├── migrations/                 # Alembic
│   ├── env.py
│   └── versions/
├── tests/
│   ├── conftest.py
│   ├── test_tickets.py
│   └── ...
├── Dockerfile
├── requirements.txt
└── .env.example
```

#### Frontend
```
frontend/
├── src/
│   ├── app/                    # Next.js App Router
│   │   ├── (auth)/
│   │   │   └── login/
│   │   ├── (dashboard)/
│   │   │   ├── layout.tsx      # Layout con sidebar
│   │   │   ├── page.tsx        # Dashboard principal
│   │   │   ├── tickets/
│   │   │   │   ├── page.tsx    # Listado
│   │   │   │   └── [id]/
│   │   │   │       └── page.tsx # Detalle
│   │   │   ├── admin/
│   │   │   └── reports/
│   │   └── api/
│   │       └── auth/[...nextauth]/route.ts
│   ├── components/
│   │   ├── ui/                 # shadcn/ui components
│   │   ├── tickets/            # Componentes específicos de tickets
│   │   │   ├── TicketCard.tsx
│   │   │   ├── TicketTable.tsx
│   │   │   ├── TicketDetail.tsx
│   │   │   └── CreateTicketForm.tsx
│   │   ├── dashboard/
│   │   │   ├── StatsRow.tsx
│   │   │   ├── TicketsByAreaChart.tsx
│   │   │   └── StatusDonut.tsx
│   │   └── shared/
│   │       ├── Sidebar.tsx
│   │       ├── Topbar.tsx
│   │       └── NotificationBell.tsx
│   ├── hooks/
│   │   ├── useTickets.ts
│   │   ├── useNotifications.ts
│   │   └── useWebSocket.ts
│   ├── stores/
│   │   ├── notificationStore.ts
│   │   └── uiStore.ts
│   ├── lib/
│   │   ├── api.ts              # Cliente axios con interceptores
│   │   ├── auth.ts             # Config NextAuth
│   │   └── utils.ts
│   └── types/
│       ├── ticket.ts
│       ├── user.ts
│       └── api.ts
├── public/
├── Dockerfile
├── next.config.ts
└── .env.example
```

### Convenciones de código

#### Nombrado
- **Python**: snake_case para variables, funciones y módulos. PascalCase para clases.
- **TypeScript**: camelCase para variables y funciones. PascalCase para componentes y tipos.
- **Base de datos**: snake_case para tablas y columnas.
- **API endpoints**: kebab-case. Ej: `/tickets/{id}/read-all`
- **Variables de entorno**: SCREAMING_SNAKE_CASE. Ej: `DATABASE_URL`

#### Commits (Conventional Commits)
```
feat(tickets): add recurring ticket creation
fix(auth): handle expired azure token refresh
docs(api): update ticket endpoints documentation
refactor(service): extract sla calculation to utility
test(tickets): add tests for priority escalation
chore(deps): update fastapi to 0.111
```
Formato: `tipo(scope): descripción en minúsculas`
Tipos permitidos: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `perf`

#### Python — Reglas específicas
- Usar type hints en todas las funciones
- Todos los endpoints son `async`
- Todos los repositorios usan sesiones async de SQLAlchemy
- Nunca usar `SELECT *` — siempre especificar columnas
- Nunca hardcodear `tenant_id` — siempre viene del JWT via middleware
- Usar `Annotated` de Pydantic v2 para validaciones
- Documentar con docstrings todas las funciones de service y repository

```python
# ✅ CORRECTO
async def get_ticket_by_id(
    self,
    ticket_id: UUID,
    tenant_id: UUID,
    db: AsyncSession
) -> Ticket | None:
    """Retorna un ticket por ID validando que pertenezca al tenant."""
    result = await db.execute(
        select(Ticket)
        .where(Ticket.id == ticket_id)
        .where(Ticket.tenant_id == tenant_id)
        .where(Ticket.deleted_at.is_(None))
    )
    return result.scalar_one_or_none()

# ❌ INCORRECTO
async def get_ticket(id):
    result = await db.execute(select(Ticket).where(Ticket.id == id))
    return result.scalar_one_or_none()
```

#### TypeScript — Reglas específicas
- No usar `any`. Siempre tipar correctamente.
- Preferir `interface` sobre `type` para objetos
- Todos los componentes React son funcionales con TypeScript
- Props siempre tipadas con `interface NombreProps`
- Usar React Query para toda comunicación con la API (no fetch directo en componentes)
- No lógica de negocio en componentes — extraer a hooks o utils

```typescript
// ✅ CORRECTO
interface TicketCardProps {
  ticket: Ticket;
  onAssign: (ticketId: string, agentId: string) => void;
}

const TicketCard: React.FC<TicketCardProps> = ({ ticket, onAssign }) => {
  ...
}

// ❌ INCORRECTO
const TicketCard = ({ ticket, onAssign }: any) => {
  ...
}
```

#### Variables de entorno — nunca en el código
```bash
# .env.example (commitear este, nunca el .env real)
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/tickets_db
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=your-secret-key-here
AZURE_CLIENT_ID=
AZURE_CLIENT_SECRET=
AZURE_TENANT_ID=
SMTP_HOST=
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
STORAGE_PATH=/app/storage
```

---

## 10. CI/CD Pipeline

### Flujo general

```
Push a branch  →  Tests + Lint  →  Build imagen  →  Push registro
                                                          │
                                              ┌───────────┴───────────┐
                                         main branch              develop branch
                                              │                        │
                                       Deploy producción         Deploy staging
```

### Archivo `.github/workflows/ci.yml`

```yaml
name: CI Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]

jobs:
  # ── JOB 1: Backend Tests ─────────────────────────────────
  test-backend:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_DB: test_db
          POSTGRES_USER: test_user
          POSTGRES_PASSWORD: test_pass
        ports: ['5432:5432']
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
      redis:
        image: redis:7
        ports: ['6379:6379']

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python 3.12
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'
          cache: 'pip'

      - name: Install dependencies
        run: |
          cd backend
          pip install -r requirements.txt

      - name: Run linter (ruff)
        run: |
          cd backend
          ruff check app/
          ruff format --check app/

      - name: Run type checker (mypy)
        run: |
          cd backend
          mypy app/ --ignore-missing-imports

      - name: Run tests with coverage
        env:
          DATABASE_URL: postgresql+asyncpg://test_user:test_pass@localhost:5432/test_db
          REDIS_URL: redis://localhost:6379/0
          SECRET_KEY: test-secret-key-for-ci
        run: |
          cd backend
          pytest tests/ -v --cov=app --cov-report=xml --cov-fail-under=80

      - name: Upload coverage report
        uses: codecov/codecov-action@v4
        with:
          file: ./backend/coverage.xml

  # ── JOB 2: Frontend Tests ─────────────────────────────────
  test-frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Node.js 20
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
          cache-dependency-path: frontend/package-lock.json

      - name: Install dependencies
        run: |
          cd frontend
          npm ci

      - name: Run linter (ESLint)
        run: |
          cd frontend
          npm run lint

      - name: Type check (TypeScript)
        run: |
          cd frontend
          npm run type-check

      - name: Run tests
        run: |
          cd frontend
          npm run test -- --coverage --watchAll=false

  # ── JOB 3: Build & Push Docker Images ─────────────────────
  build:
    needs: [test-backend, test-frontend]
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main' || github.ref == 'refs/heads/develop'

    steps:
      - uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Login to GitHub Container Registry
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Determine environment tag
        id: env_tag
        run: |
          if [[ "${{ github.ref }}" == "refs/heads/main" ]]; then
            echo "tag=production" >> $GITHUB_OUTPUT
          else
            echo "tag=staging" >> $GITHUB_OUTPUT
          fi

      - name: Build and push backend
        uses: docker/build-push-action@v5
        with:
          context: ./backend
          push: true
          tags: ghcr.io/${{ github.repository }}/backend:${{ steps.env_tag.outputs.tag }}
          cache-from: type=gha
          cache-to: type=gha,mode=max

      - name: Build and push frontend
        uses: docker/build-push-action@v5
        with:
          context: ./frontend
          push: true
          tags: ghcr.io/${{ github.repository }}/frontend:${{ steps.env_tag.outputs.tag }}
          cache-from: type=gha
          cache-to: type=gha,mode=max

  # ── JOB 4: Deploy ─────────────────────────────────────────
  deploy:
    needs: build
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'

    steps:
      - name: Deploy to VPS via SSH
        uses: appleboy/ssh-action@v1
        with:
          host: ${{ secrets.VPS_HOST }}
          username: ${{ secrets.VPS_USER }}
          key: ${{ secrets.VPS_SSH_KEY }}
          script: |
            cd /opt/tickets-app
            docker compose pull
            docker compose up -d --no-deps --build
            docker compose exec backend alembic upgrade head
            docker system prune -f
```

### Variables secretas en GitHub (Settings → Secrets)
```
VPS_HOST           — IP del servidor VPS
VPS_USER           — Usuario SSH (ej: deploy)
VPS_SSH_KEY        — Clave privada SSH para acceso al VPS
```

### Ramas de trabajo
```
main         → Producción. Solo merge via PR aprobado. Deploy automático.
develop      → Staging. Integración de features. Deploy automático a staging.
feature/*    → Desarrollo de funcionalidades. PR hacia develop.
fix/*        → Corrección de bugs. PR hacia develop (o main si es crítico).
```

### Regla de protección de ramas
- `main` y `develop`: requieren al menos 1 aprobación en PR
- CI debe pasar completamente antes de permitir merge
- No se permite push directo a `main`

---

## 11. Infraestructura y Despliegue

### `docker-compose.yml` (Producción)

```yaml
version: '3.9'

services:
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/certs:/etc/letsencrypt:ro
      - frontend_build:/usr/share/nginx/html:ro
    depends_on:
      - backend
      - frontend
    restart: always

  backend:
    image: ghcr.io/${REPO}/backend:production
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=${REDIS_URL}
      - SECRET_KEY=${SECRET_KEY}
      - AZURE_CLIENT_ID=${AZURE_CLIENT_ID}
      - AZURE_CLIENT_SECRET=${AZURE_CLIENT_SECRET}
      - SMTP_HOST=${SMTP_HOST}
      - STORAGE_PATH=/app/storage
    volumes:
      - storage_data:/app/storage
    depends_on:
      - db
      - redis
    restart: always
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  frontend:
    image: ghcr.io/${REPO}/frontend:production
    environment:
      - NEXTAUTH_URL=${NEXTAUTH_URL}
      - NEXTAUTH_SECRET=${NEXTAUTH_SECRET}
      - NEXT_PUBLIC_API_URL=${API_URL}
    restart: always

  worker:
    image: ghcr.io/${REPO}/backend:production
    command: celery -A app.tasks.celery_app worker --loglevel=info
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=${REDIS_URL}
      - SECRET_KEY=${SECRET_KEY}
      - SMTP_HOST=${SMTP_HOST}
    volumes:
      - storage_data:/app/storage
    depends_on:
      - db
      - redis
    restart: always

  beat:
    image: ghcr.io/${REPO}/backend:production
    command: celery -A app.tasks.celery_app beat --loglevel=info
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=${REDIS_URL}
    depends_on:
      - redis
    restart: always

  db:
    image: postgres:16-alpine
    environment:
      - POSTGRES_DB=${POSTGRES_DB}
      - POSTGRES_USER=${POSTGRES_USER}
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: always
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER}"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
    restart: always

  backup:
    image: postgres:16-alpine
    environment:
      - PGPASSWORD=${POSTGRES_PASSWORD}
    volumes:
      - backup_data:/backups
    entrypoint: /bin/sh -c
    command: >
      "while true; do
        pg_dump -h db -U ${POSTGRES_USER} ${POSTGRES_DB} > /backups/backup_$$(date +%Y%m%d_%H%M%S).sql
        find /backups -name '*.sql' -mtime +30 -delete
        sleep 86400
      done"
    depends_on:
      - db
    restart: always

volumes:
  postgres_data:
  redis_data:
  storage_data:
  backup_data:
  frontend_build:
```

### Requerimientos del VPS
- **OS**: Ubuntu 22.04 LTS
- **CPU**: 2 vCPU mínimo (recomendado 4)
- **RAM**: 4 GB mínimo (recomendado 8 GB)
- **Disco**: 80 GB SSD mínimo
- **Proveedor recomendado**: Hetzner CX22 (~$6 USD/mes) o Contabo VPS S
- **Puerto 80 y 443**: Abiertos en firewall
- **Docker + Docker Compose**: Instalados en el servidor

### Configuración inicial del servidor (una sola vez)
```bash
# 1. Instalar Docker
curl -fsSL https://get.docker.com | sh
usermod -aG docker deploy

# 2. Instalar Certbot para SSL
apt install certbot python3-certbot-nginx -y

# 3. Obtener certificado SSL
certbot certonly --nginx -d tickets.smartsecurity.com.co

# 4. Clonar repositorio y configurar
git clone https://github.com/org/tickets-app /opt/tickets-app
cd /opt/tickets-app
cp .env.example .env
# Editar .env con los valores reales

# 5. Primer despliegue
docker compose up -d
docker compose exec backend alembic upgrade head

# 6. Renovación automática de SSL (cron)
crontab -e
# 0 3 * * * certbot renew --quiet && docker compose restart nginx
```

---

## 12. Plan de Trabajo — Tareas Detalladas

> Cada tarea está escrita con el nivel de detalle suficiente para que Claude Code la ejecute de manera eficiente sin ambigüedades. Seguir el orden es importante ya que hay dependencias entre tareas.

---

### FASE 1 — Fundación del Proyecto (Semana 1–2)

---

#### TAREA 1.1 — Inicialización del repositorio y estructura base

**Objetivo:** Crear la estructura completa del repositorio con toda la configuración base lista para desarrollar.

**Acciones:**
1. Crear repositorio GitHub con estructura monorepo: `/backend`, `/frontend`, `/nginx`, `/docs`
2. En `/backend`: inicializar proyecto Python con `pyproject.toml` usando las dependencias del stack definido. Crear estructura de carpetas completa según la sección 9. Crear `.env.example` con todas las variables necesarias.
3. En `/frontend`: inicializar Next.js 14 con TypeScript, Tailwind CSS y App Router. Instalar todas las dependencias del stack. Crear estructura de carpetas completa según sección 9.
4. Crear `docker-compose.yml` para desarrollo local con hot-reload activo para backend y frontend. Los servicios de DB y Redis deben tener datos persistentes en volúmenes locales.
5. Crear `docker-compose.prod.yml` basado en la sección 11.
6. Crear `.github/workflows/ci.yml` completo según sección 10.
7. Crear `.gitignore` apropiado para Python, Node y Docker.
8. Crear `Makefile` con comandos útiles: `make dev`, `make test`, `make migrate`, `make lint`.

**Criterio de aceptación:** `make dev` levanta todo el stack localmente. Frontend en `localhost:3000`, backend en `localhost:8000`, docs en `localhost:8000/docs`.

---

#### TAREA 1.2 — Modelo de base de datos y migraciones

**Objetivo:** Crear todos los modelos SQLAlchemy y las migraciones Alembic correspondientes al modelo de datos de la sección 7.

**Acciones:**
1. Crear `app/models/base.py` con clase `BaseModel` que incluya `id` (UUID, default gen_random_uuid), `tenant_id` (UUID, FK a tenants, not null), `created_at`, `updated_at` (auto-update). Todos los modelos heredan de esta base.
2. Crear un modelo SQLAlchemy por cada tabla definida en la sección 7. Incluir todos los campos, tipos, constraints y relaciones.
3. Crear `app/database.py` con engine async de SQLAlchemy, sesión async y función `get_db` para dependency injection en FastAPI.
4. Configurar Alembic con soporte async. El `env.py` debe importar todos los modelos automáticamente.
5. Generar migración inicial con `alembic revision --autogenerate -m "initial_schema"`. Revisar el archivo generado para asegurar que los índices críticos definidos en la sección 7 estén incluidos.
6. Crear script `scripts/seed.py` que genere datos de prueba: 1 tenant (Smart Security), 5 usuarios con diferentes roles, 3 áreas, 5 categorías, 20 tickets en diferentes estados.

**Criterio de aceptación:** `make migrate` ejecuta la migración sin errores. `make seed` crea datos de prueba. Todas las tablas existen con sus índices en la DB.

---

#### TAREA 1.3 — Autenticación y middleware multi-tenant

**Objetivo:** Implementar el sistema completo de autenticación incluyendo JWT, login local y Azure AD, más el middleware que inyecta el tenant en cada request.

**Acciones:**
1. Crear `app/utils/security.py` con funciones: `hash_password`, `verify_password`, `create_access_token`, `create_refresh_token`, `decode_token`. Los tokens incluyen `user_id`, `tenant_id`, `role` en el payload.
2. Crear `app/middleware/tenant.py`: middleware FastAPI que en cada request extrae el token JWT, valida su firma, extrae `tenant_id` y lo pone en `request.state.tenant_id`. Si el token no existe o es inválido, retorna 401.
3. Crear `app/dependencies.py` con:
   - `get_current_user`: extrae usuario del token, lo busca en DB, valida que esté activo y no archivado.
   - `require_role(*roles)`: dependency factory que verifica que el usuario tenga uno de los roles requeridos.
   - `get_tenant_id`: shortcut para obtener tenant_id desde request.state.
4. Crear `app/routers/auth.py` con endpoints:
   - `POST /auth/login`: recibe email + password, valida, retorna access_token + refresh_token.
   - `POST /auth/refresh`: recibe refresh_token (desde cookie httpOnly), retorna nuevo access_token.
   - `POST /auth/logout`: revoca refresh_token (borrándolo de Redis).
   - `GET /auth/me`: retorna usuario autenticado con sus áreas y permisos.
   - `GET /auth/login/azure`: retorna URL de redirección a Microsoft.
   - `GET /auth/callback/azure`: recibe code de Azure, obtiene token, busca o crea usuario, retorna JWT.
5. Los refresh tokens se almacenan en Redis con clave `refresh:{user_id}:{jti}` y TTL de 7 días.
6. Crear `app/services/auth_service.py` con la lógica de autenticación Azure AD usando la librería `msal`.

**Criterio de aceptación:** Tests unitarios para todas las funciones de security. Test de integración para el flujo completo de login → acceso a endpoint protegido → refresh → logout.

---

### FASE 2 — Core de Tickets (Semana 3–4)

---

#### TAREA 2.1 — CRUD completo de tickets

**Objetivo:** Implementar toda la lógica de creación, lectura, actualización y gestión de tickets incluyendo el enrutamiento automático.

**Acciones:**
1. Crear `app/schemas/ticket.py` con schemas Pydantic: `TicketCreate`, `TicketUpdate`, `TicketResponse`, `TicketListResponse`. `TicketResponse` debe incluir datos del solicitante, agente asignado, área y categoría (no solo IDs).
2. Crear `app/repositories/ticket_repository.py` con métodos:
   - `get_by_id(ticket_id, tenant_id)`: busca ticket validando tenant.
   - `get_list(tenant_id, filters, pagination)`: lista con filtros opcionales por status, priority, area_id, category_id, assigned_to, date_range. Siempre pagina.
   - `create(data, tenant_id)`: crea ticket y genera número secuencial `#TK-XXXX` atómicamente usando `SELECT MAX + 1` con lock para evitar duplicados.
   - `update(ticket_id, data, tenant_id)`: actualiza campos permitidos.
   - `soft_delete(ticket_id, tenant_id)`: setea `deleted_at`.
3. Crear `app/services/ticket_service.py` con métodos:
   - `create_ticket`: valida que la categoría y área existan en el tenant, aplica enrutamiento automático (busca `default_area_id` y `default_agent_id` de la categoría), calcula el SLA correspondiente y setea `sla_due_at`, registra en `ticket_history` la acción `created`, dispara notificación al agente asignado.
   - `update_ticket`: valida permisos (el solicitante solo puede editar si status es `open`; agente puede editar campos de su área; admin puede editar todo), registra cambios en `ticket_history`.
   - `change_status`: valida que la transición de estado sea válida (seguir el flujo definido), registra en history, dispara notificaciones correspondientes.
   - `assign_ticket`: asigna agente, valida que pertenezca al área del ticket, registra en history, notifica al agente.
   - `escalate_ticket`: cambia a estado `escalated`, registra en history, notifica al supervisor del área.
   - `resolve_ticket`: cambia a `resolved`, setea `resolved_at`, calcula si se cumplió el SLA.
   - `close_ticket`: cambia a `closed`, setea `closed_at`.
   - `reopen_ticket`: cambia de `resolved`/`closed` a `open`, incrementa `reopen_count`, registra motivo en history.
4. Crear `app/routers/tickets.py` con todos los endpoints definidos en la sección 8. Usar las dependencies de autenticación y rol apropiadas en cada endpoint.
5. Aplicar reglas de visibilidad: los `requester` solo ven sus propios tickets. Los `agent` ven tickets de sus áreas. Los `supervisor` y `admin` ven todos.

**Criterio de aceptación:** Tests de integración para el ciclo completo de un ticket: crear → asignar → trabajar → resolver → cerrar → reabrir. Tests para validación de permisos por rol.

---

#### TAREA 2.2 — Comentarios, adjuntos e historial

**Objetivo:** Implementar el sistema de comentarios (públicos e internos), historial de cambios y subida de archivos adjuntos.

**Acciones:**
1. Crear `app/repositories/comment_repository.py` y `app/services/comment_service.py`. Los comentarios internos (`is_internal=true`) solo son visibles para usuarios con rol `agent`, `supervisor` o `admin` — nunca para `requester`. Validar en el service que el `requester` no puede crear notas internas.
2. Crear `app/utils/storage.py` con:
   - `save_file(file, tenant_id, ticket_id)`: guarda el archivo en `{STORAGE_PATH}/{tenant_id}/{ticket_id}/{uuid}_{filename}`. Valida tipo MIME (solo PDF, JPG, PNG, WEBP) y tamaño máximo 10 MB.
   - `generate_signed_url(file_path, expires_in=3600)`: genera URL temporal firmada con HMAC para descarga segura. El endpoint de descarga valida la firma antes de servir el archivo.
   - `delete_file(file_path)`: borra el archivo físico.
3. Crear endpoint `POST /tickets/{id}/attachments` que recibe `multipart/form-data`, valida y guarda el archivo, registra en `ticket_attachments` y en `ticket_history`.
4. Crear endpoint `GET /tickets/{id}/attachments/{att_id}/download` que genera y retorna la URL firmada temporal.
5. El historial (`ticket_history`) se registra automáticamente desde el `ticket_service` en cada acción. Crear `GET /tickets/{id}/history` que lo retorna ordenado por `created_at DESC`, incluyendo datos del actor (nombre, avatar).

**Criterio de aceptación:** Test de subida de archivo con tipo inválido debe rechazarse. Test de URL firmada debe expirar correctamente. Test de visibilidad de notas internas por rol.

---

#### TAREA 2.3 — Sistema de SLAs

**Objetivo:** Implementar el cálculo de SLAs con tiempo en horas hábiles, alertas y seguimiento de cumplimiento.

**Acciones:**
1. Crear `app/utils/business_hours.py` con las siguientes funciones:
   - `calculate_due_date(start_datetime, hours, tenant_config)`: recibe fecha de inicio, horas hábiles y config del tenant. Calcula la fecha de vencimiento excluyendo fines de semana y días fuera del horario laboral. Ejemplo: 8 horas hábiles desde viernes 4pm → lunes 12pm.
   - `is_within_business_hours(now, timezone_str, working_days, working_hours_start, working_hours_end)`: retorna `True` si `now` cae dentro del horario hábil configurado del tenant.
   - `next_business_start(now, timezone_str, working_days, working_hours_start, working_hours_end)`: retorna el próximo inicio de jornada hábil en UTC, para programar envíos diferidos.
2. En `ticket_service.create_ticket`: después de crear el ticket, buscar el SLA aplicable (por categoría y prioridad, usando el más específico disponible). Si existe, calcular `sla_due_at` usando `calculate_due_date`.
3. Crear tarea Celery `tasks/sla_tasks.py`:
   - `check_sla_warnings`: se ejecuta cada 30 minutos. Busca tickets donde `sla_due_at` está entre ahora y las próximas 2 horas y `sla_breached=false`. Para cada uno: enviar notificación de advertencia al agente y supervisor del área.
   - `check_sla_breaches`: se ejecuta cada 15 minutos. Busca tickets donde `sla_due_at < NOW()` y `sla_breached=false` y status no es `resolved`/`closed`. Para cada uno: setear `sla_breached=true`, enviar notificación crítica al supervisor.
4. Configurar Celery Beat con el schedule de estas tareas.
5. En el `TicketResponse`, incluir campos calculados: `sla_status` (on_time / warning / breached), `sla_percentage` (% del tiempo consumido).

**Criterio de aceptación:** Test de `calculate_due_date` con casos borde (viernes tarde, víspera de festivo). Test de detección de breach en la tarea Celery.

---

### FASE 3 — Notificaciones y Tiempo Real (Semana 5)

---

#### TAREA 3.1 — Sistema de notificaciones con WebSocket

**Objetivo:** Implementar notificaciones en tiempo real dentro del aplicativo y por correo electrónico.

**Acciones:**
1. Crear `app/services/notification_service.py` con método `create_and_send(user_id, tenant_id, type, ticket_id, title, body)` que:
   - Guarda la notificación en la tabla `notifications`.
   - Publica el evento en Redis pub/sub en el canal `notifications:{user_id}`.
   - **Lógica de horario hábil**: si el tipo requiere correo, verifica si `now` cae dentro del horario laboral del tenant usando `is_within_business_hours`. Si sí → encola el correo de inmediato y setea `email_sent_at`. Si no → guarda `scheduled_for = next_business_start(...)` y deja `email_sent_at = null` para que la tarea `send_scheduled_notifications` lo procese.
2. Crear endpoint WebSocket `GET /notifications/ws` en FastAPI. Al conectarse, el cliente se suscribe al canal de Redis de su `user_id`. Cuando llega un mensaje, lo retransmite al cliente WebSocket. Manejar correctamente la desconexión y reconexión.
3. Crear `app/utils/email.py` con función `send_email(to, subject, template_name, context)` usando `smtplib` o `aiosmtplib`. Las plantillas HTML de correo se almacenan en `app/templates/emails/` como archivos Jinja2.
4. Crear plantillas de correo para: ticket creado, ticket asignado, estado cambiado, comentario nuevo, SLA warning, SLA breach, ticket resuelto, reporte semanal.
5. Crear tarea Celery `tasks/email_tasks.py: send_notification_email(to, subject, template, context)`.
6. Crear tarea Celery `tasks/notification_tasks.py: send_scheduled_notifications()` que se ejecuta cada 5 minutos. Busca notificaciones donde `scheduled_for <= NOW()` y `email_sent_at IS NULL`, encola el correo correspondiente y actualiza `email_sent_at`. Reintentos automáticos x3.
7. En el frontend, crear `hooks/useWebSocket.ts` que se conecta al endpoint WS, maneja reconexión automática con backoff exponencial, y actualiza el store de notificaciones (Zustand) cuando llega un mensaje nuevo.
8. Crear componente `NotificationBell.tsx` con badge de contador de no leídas, dropdown con listado y botón "marcar todas como leídas".

**Criterio de aceptación:** Test de que al cambiar el estado de un ticket, el agente asignado recibe notificación en tiempo real. Test de que el correo se encola cuando corresponde según la config del tenant.

---

### FASE 4 — Funcionalidades Avanzadas (Semana 6–7)

---

#### TAREA 4.1 — Tickets recurrentes

**Objetivo:** Implementar el módulo de plantillas de tickets recurrentes con generación automática por calendario.

**Acciones:**
1. Crear endpoints CRUD en `app/routers/admin.py` para gestión de `recurring_templates`. Solo accesible para rol `admin`.
2. Crear `app/services/recurring_service.py` con método `calculate_next_run(template)` que:
   - Para `day_of_month`: calcula el próximo día X del mes actual o siguiente.
   - Si la fecha calculada cae en fin de semana o festivo, ajusta según `if_holiday_action` de la plantilla.
   - Retorna el `datetime` exacto en que debe ejecutarse.
3. Crear tarea Celery `tasks/recurring_tasks.py: process_recurring_tickets()` que:
   - Se ejecuta cada hora (configurado en Celery Beat).
   - Busca todas las plantillas activas donde `next_run_at <= NOW()`.
   - Para cada una: crea el ticket usando `ticket_service.create_ticket` con los datos de la plantilla, actualiza `last_run_at` y recalcula `next_run_at`.
   - El ticket creado queda marcado con `is_recurring_instance=true` y referencia a la plantilla.
4. Al crear o actualizar una plantilla, calcular y guardar inmediatamente el `next_run_at`.

**Criterio de aceptación:** Test de `calculate_next_run` para día 28 que cae en domingo con acción `previous_business_day`. Test de que el ticket se crea correctamente y `next_run_at` se recalcula.

---

#### TAREA 4.2 — Dashboard y reportes

**Objetivo:** Implementar todos los endpoints del dashboard y el sistema de reportes automáticos semanales.

**Acciones:**
1. Crear `app/routers/dashboard.py` con los endpoints definidos en la sección 8. Todas las queries deben ser eficientes (no N+1). Usar agregaciones SQL en lugar de procesamiento en Python.
2. Crear `app/repositories/dashboard_repository.py` con queries optimizadas:
   - `get_summary(tenant_id, date_range)`: retorna counts por estado, tiempo promedio de resolución, tickets nuevos hoy.
   - `get_tickets_by_area(tenant_id, date_range)`: agrupación por área con counts.
   - `get_sla_compliance(tenant_id, date_range)`: porcentaje de tickets resueltos dentro del SLA.
   - `get_agent_performance(tenant_id, date_range, area_ids=None)`: métricas por agente. Si `area_ids` no es `None`, filtra solo los agentes que pertenecen a esas áreas. Los supervisores reciben solo las áreas donde son miembros o managers.
   - `get_urgency_abuse_report(tenant_id, date_range)`: porcentaje de tickets urgentes por usuario, comparado con período anterior. Solo retorna datos si el usuario que consulta tiene `id` igual a `tenant_config.urgency_report_visible_to`.
3. Crear tarea Celery `tasks/report_tasks.py: send_weekly_report(tenant_id)` que:
   - Obtiene métricas de la semana anterior.
   - Renderiza plantilla HTML del reporte.
   - Envía por correo a los destinatarios configurados en `tenant_config.weekly_report_recipients`.
4. Configurar Celery Beat para ejecutar `send_weekly_report` cada lunes a las 8am (en la zona horaria del tenant).

**Criterio de aceptación:** Test de que el reporte de abuso de urgencia rechaza el acceso a usuarios sin permiso. Test de que el reporte semanal se envía con los datos correctos.

---

#### TAREA 4.3 — Panel de administración del tenant

**Objetivo:** Implementar todas las funcionalidades del panel de administración para que el admin del tenant pueda configurar el sistema sin tocar código.

**Acciones:**
1. Implementar endpoints de administración definidos en la sección 8 bajo `/admin/*`. Todos protegidos con `require_role('admin')`.
2. Crear servicio para gestión de usuarios: crear usuario (enviar correo de bienvenida con contraseña temporal si es login local), editar (cambiar rol, áreas), archivar (setea `is_archived=true`, revoca todos sus refresh tokens en Redis).
3. Gestión de áreas: CRUD completo. Al crear área, se puede asignar responsable y miembros iniciales.
4. Gestión de categorías: CRUD con configuración de enrutamiento (área destino, agente por defecto, si requiere aprobación).
5. Gestión de SLAs: CRUD. Validar que no haya SLAs duplicados para misma categoría + prioridad.
6. Configuración del tenant: endpoint `PATCH /admin/config` que permite actualizar cualquier campo de `tenant_configs`. Invalidar caché de Redis al actualizar.
7. Al archivar un usuario: sus tickets abiertos se reasignan automáticamente con la siguiente prioridad: (1) `manager_id` del área del ticket, (2) primer supervisor activo del área. Solo si no existe ninguno queda sin asignar (`null`). En todos los casos se registra en `ticket_history` con `action="assigned"` y `reason="agent_archived"`, y se notifica al nuevo asignado. La lista `GET /users` incluye `primary_area_id` en cada usuario.

**Criterio de aceptación:** Test de que un usuario archivado no puede hacer login. Test de que sus tickets quedan reasignados correctamente. Test de que la caché se invalida al cambiar la configuración.

---

### FASE 5 — Frontend Completo (Semana 8–9)

---

#### TAREA 5.1 — Autenticación y layout base del frontend

**Objetivo:** Implementar el flujo de autenticación en Next.js y el layout base del aplicativo.

**Acciones:**
1. Configurar NextAuth.js en `src/app/api/auth/[...nextauth]/route.ts` con dos providers: `AzureADProvider` (con las variables de entorno del tenant) y `CredentialsProvider` (para login local).
2. Crear página de login `/app/(auth)/login/page.tsx` con:
   - Formulario de email + password (para login local).
   - Botón "Ingresar con Microsoft" que inicia el flujo Azure AD.
   - Validación del formulario con React Hook Form + Zod.
   - Manejo de errores (credenciales inválidas, cuenta archivada).
3. Crear `src/lib/api.ts`: instancia de Axios configurada con base URL del backend, interceptor que añade `Authorization: Bearer {token}` en cada request, interceptor de respuesta que maneja 401 (token expirado) intentando refresh automático y redirigiendo a login si falla.
4. Crear layout principal `/app/(dashboard)/layout.tsx` que incluye `Sidebar` y `Topbar`. Proteger con middleware Next.js que redirige a login si no hay sesión.
5. Crear componente `Sidebar.tsx` con navegación completa. Los ítems del menú se muestran según el rol del usuario (admin ve todo, requester solo ve "Mis Solicitudes" y "Nueva Solicitud").
6. Crear `stores/notificationStore.ts` con Zustand para manejar notificaciones. Inicializar conexión WebSocket al montar el layout.

**Criterio de aceptación:** El flujo completo de login con M365 funciona end-to-end. El layout se adapta al rol del usuario. La reconexión automática del WebSocket funciona correctamente.

---

#### TAREA 5.2 — Módulo de tickets en el frontend

**Objetivo:** Implementar todas las pantallas relacionadas con tickets: listado, detalle y creación.

**Acciones:**
1. Crear `hooks/useTickets.ts` usando React Query:
   - `useTicketList(filters)`: query con caché, refetch en foco, paginación.
   - `useTicket(id)`: query individual con prefetch.
   - `useCreateTicket()`: mutación que invalida la lista al completarse.
   - `useUpdateTicket()`: mutación con optimistic update.
2. Crear página de listado `/tickets/page.tsx` con:
   - Tabla de tickets con columnas: ID, título, área, estado (badge de color), prioridad (badge), asignado, fecha.
   - Filtros por estado, área, prioridad y búsqueda por texto. Los filtros se sincronizan con la URL (query params) para que sean compartibles.
   - Paginación.
   - Indicador visual de SLA (borde o badge amarillo si está por vencer, rojo si está vencido).
3. Crear página de detalle `/tickets/[id]/page.tsx` con:
   - Header con título, badges de estado y prioridad, acciones disponibles según rol.
   - Descripción del ticket.
   - Timeline de historial de cambios.
   - Sección de comentarios con diferenciación visual entre comentarios públicos y notas internas.
   - Editor de nuevo comentario con checkbox "Nota interna" (solo visible para agents y superiores).
   - Panel lateral con metadata: estado, asignado, solicitante, fechas, progreso de SLA.
   - Botones de acción contextuales según rol y estado actual: "Asignar", "En Proceso", "Escalar", "Resolver", "Cerrar", "Reabrir".
   - **Asignación por supervisores**: los supervisores pueden reasignar tickets de áreas donde son managers o miembros. La lógica `canAssign` verifica esto consultando los endpoints `/areas` y `/areas/{id}/members`.
4. Crear modal/página de creación `/tickets/new` con formulario completo: selects de categoría y prioridad, título, descripción (rich text básico), área, zona de adjuntos con drag & drop.
   - **Área obligatoria si no hay agente asignado**: si el campo "Asignar a" está vacío, el campo "Área" es requerido para que el supervisor del área pueda reasignarlo.
   - **Auto-completar área**: al seleccionar un agente, si el área está vacía se rellena automáticamente con el `primary_area_id` del agente seleccionado.
5. Todos los cambios de estado del ticket deben actualizar la UI optimísticamente y sincronizar con el servidor.

**Criterio de aceptación:** Crear un ticket end-to-end desde el frontend y verlo aparecer en tiempo real en el listado. El badge de SLA cambia de color según el estado.

---

#### TAREA 5.3 — Dashboard y pantallas de administración

**Objetivo:** Implementar el dashboard principal con gráficas y las pantallas del panel de administración.

**Acciones:**
1. Crear página de dashboard `/page.tsx` con:
   - Fila de 4 cards de estadísticas (total abiertos, en proceso, resueltos hoy, tiempo promedio).
   - Gráfica de barras horizontal de tickets por área usando Recharts.
   - Gráfica donut de distribución por estado usando Recharts.
   - Lista de actividad reciente.
   - Panel de tickets próximos a vencer SLA (solo para supervisor/admin).
2. Crear sección `/reports/page.tsx` con el reporte de abuso de urgencia. Esta sección solo es visible para el usuario con permiso especial (CEO). Si otro usuario intenta acceder, mostrar 403.
3. Crear sección de administración `/admin/` con sub-páginas:
   - `/admin/users`: tabla de usuarios con acciones de editar y archivar. Modal de creación/edición.
   - `/admin/areas`: lista de áreas con sus miembros. Modal de gestión.
   - `/admin/categories`: lista de categorías con configuración de enrutamiento.
   - `/admin/slas`: tabla de SLAs configurados con modal de edición.
   - `/admin/recurring`: lista de plantillas recurrentes. Modal de creación con selector de tipo de recurrencia.
   - `/admin/config`: formulario de configuración general del tenant (branding, SLA defaults, etc.).
4. Todas las pantallas de admin incluyen confirmación antes de acciones destructivas (archivar usuario, desactivar plantilla).

**Criterio de aceptación:** El dashboard muestra datos reales del seed. La sección de reportes de abuso rechaza usuarios sin permiso. El CRUD de usuarios funciona end-to-end incluyendo el archivado.

---

### FASE 6 — Multi-Tenant y Onboarding (Semana 10)

---

#### TAREA 6.1 — Sistema de onboarding para nuevos tenants

**Objetivo:** Implementar el proceso automatizado para dar de alta un nuevo cliente (tenant) en el sistema con configuración mínima.

**Acciones:**
1. Crear script `scripts/create_tenant.py` que recibe como argumentos: nombre, slug, subdominio, método de auth, y datos de configuración inicial. El script:
   - Crea el registro en `tenants` y `tenant_configs`.
   - Crea el usuario admin inicial.
   - Crea áreas y categorías por defecto (plantilla genérica aplicable a cualquier empresa).
   - Crea SLAs por defecto (24h para low, 8h para medium, 4h para high, 1h para urgent).
   - Envía correo de bienvenida al admin con sus credenciales y enlace al sistema.
2. Crear plantilla de configuración inicial en `scripts/templates/default_tenant.yaml` con categorías genéricas (Soporte TI, Mantenimiento, Administración, Compras, RRHH) y sus SLAs por defecto. Cualquier nuevo tenant parte de esta plantilla y personaliza después.
3. Documentar en `docs/onboarding.md` el proceso completo para incorporar un nuevo cliente: desde la llamada al script hasta la primera sesión del admin en el sistema.
4. Crear endpoint `POST /superadmin/tenants` (protegido con API key de superadmin, no JWT de tenant) para crear tenants programáticamente vía API. Esto permite en el futuro tener un panel de gestión de clientes.

**Criterio de aceptación:** Ejecutar el script crea un tenant completamente funcional. El admin puede hacer login inmediatamente y personalizar su configuración.

---

### FASE 7 — Calidad y Despliegue (Semana 11)

---

#### TAREA 7.1 — Suite completa de tests

**Objetivo:** Alcanzar cobertura de tests ≥ 80% en lógica crítica de negocio.

**Acciones:**
1. Backend — tests con pytest:
   - `tests/test_auth.py`: login local, login Azure (mock), refresh, logout, acceso con token inválido.
   - `tests/test_tickets.py`: ciclo completo de ticket, validaciones de permisos por rol, transiciones de estado inválidas.
   - `tests/test_sla.py`: cálculo de horas hábiles con festivos, detección de breach.
   - `tests/test_recurring.py`: cálculo de `next_run_at` para todos los tipos de recurrencia.
   - `tests/test_notifications.py`: creación de notificación y publicación en Redis.
   - `tests/test_multitenancy.py`: verificar que usuario del tenant A no puede ver datos del tenant B.
2. Frontend — tests con Vitest + Testing Library:
   - Tests de componentes: `TicketCard`, `TicketDetail`, formularios.
   - Tests de hooks: `useTickets`, `useWebSocket`.
   - Tests de stores: `notificationStore`.
3. Configurar reporte de cobertura y asegurarse de que el pipeline CI falla si la cobertura cae por debajo del 80%.

**Criterio de aceptación:** `make test` pasa completamente. El reporte de cobertura muestra ≥ 80% en servicios y repositorios.

---

#### TAREA 7.2 — Despliegue inicial en VPS

**Objetivo:** Desplegar el sistema en el VPS configurado para Smart Security y validar que todo funciona end-to-end en producción.

**Acciones:**
1. Configurar el VPS (Hetzner o similar) siguiendo los pasos de la sección 11.
2. Crear subdominio `tickets.smartsecurity.com.co` apuntando al VPS (registro DNS tipo A).
3. Obtener y configurar certificado SSL con Certbot.
4. Crear `.env` de producción en el servidor con todos los valores reales (nunca commitear este archivo).
5. Ejecutar primer despliegue via `docker compose up -d` y correr migraciones.
6. Ejecutar el script de onboarding para crear el tenant de Smart Security con todos sus usuarios.
7. Configurar Azure AD: registrar la aplicación en el portal de Microsoft, obtener `client_id`, `client_secret` y `tenant_id`, configurar redirect URI.
8. Verificar checklist de producción:
   - [ ] HTTPS funciona correctamente
   - [ ] Login con Microsoft funciona
   - [ ] Creación de tickets funciona end-to-end
   - [ ] Notificaciones en tiempo real funcionan
   - [ ] Correos se envían correctamente
   - [ ] Backup automático de DB está activo
   - [ ] Pipeline CI/CD despliega correctamente al hacer push a `main`
   - [ ] Logs son accesibles via `docker compose logs`

**Criterio de aceptación:** El equipo de Smart Security puede hacer login con su correo corporativo M365 y crear su primer ticket real.

---

## Resumen de Fases y Estimación

| Fase | Descripción | Semanas | Tareas | Estado |
|---|---|---|---|---|
| 1 | Fundación | 1–2 | 1.1, 1.2, 1.3 | ✅ Completada |
| 2 | Core de Tickets | 3–4 | 2.1, 2.2, 2.3 | ✅ Completada |
| 3 | Notificaciones y Tiempo Real | 5 | 3.1 | ✅ Completada |
| 4 | Funcionalidades Avanzadas | 6–7 | 4.1, 4.2, 4.3 | ✅ Completada |
| 5 | Frontend Completo | 8–9 | 5.1, 5.2, 5.3 | ✅ Completada |
| 6 | Multi-Tenant y Onboarding | 10 | 6.1 | ✅ Completada |
| 7 | Calidad y Despliegue | 11 | 7.1, 7.2 | 🔲 Pendiente |

**Total estimado:** 11 semanas · ~15 tareas principales

---

## Mejoras Implementadas Post-Fase 6

Las siguientes mejoras fueron implementadas tras completar las fases principales:

### Notificaciones fuera de horario hábil
- **Migration `002`**: columnas `scheduled_for` y `email_sent_at` en la tabla `notifications`.
- `notification_service.py` verifica `is_within_business_hours` antes de enviar cada correo. Si está fuera de horario, guarda `scheduled_for = next_business_start(...)`.
- Nueva tarea Celery `send_scheduled_notifications` (cada 5 min) en `notification_tasks.py`: busca notificaciones con `scheduled_for <= NOW()` y `email_sent_at IS NULL` y despacha los correos pendientes.

### Dashboard — filtro de agentes por área para supervisores
- El endpoint `GET /dashboard/agent-performance` ahora scoping el resultado: los supervisores solo ven métricas de agentes que pertenecen a sus áreas (como manager o como miembro).
- `DashboardRepository.get_agent_performance` acepta parámetro opcional `area_ids`.

### Archivado de usuario — reasignación inteligente
- Al archivar un usuario vía `POST /users/{id}/archive`, sus tickets abiertos se reasignan automáticamente:
  1. Al `manager_id` del área del ticket (si existe).
  2. Al primer supervisor activo del área (fallback).
  3. A `null` si no hay ninguno disponible.
- Cada reasignación queda registrada en `ticket_history` con `reason: "agent_archived"` y se notifica al nuevo asignado.
- `GET /users` incluye `primary_area_id` en cada usuario de la respuesta.

### Frontend — mejoras de asignación
- **CreateTicketForm**: área es obligatoria si no se selecciona agente. Al seleccionar un agente se auto-rellena el área con su `primary_area_id`.
- **TicketDetail**: supervisores pueden asignar/reasignar tickets de áreas donde son managers o miembros activos.

---

*Este documento es la fuente de verdad del proyecto. Cualquier decisión técnica que no esté cubierta aquí debe resolverse priorizando: (1) consistencia con las decisiones ya tomadas, (2) la visión multi-tenant, (3) simplicidad sobre complejidad prematura.*
