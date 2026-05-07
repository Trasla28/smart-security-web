# CLAUDE.md — Sistema de Gestión de Tickets · Smart Security
## Guía de Arquitectura y Referencia Técnica (Aplicativo Completo)

> **Propósito de este documento:** Referencia técnica para entender rápidamente el sistema al realizar ajustes o mejoras. Describe qué es el proyecto, cómo está estructurado, cómo funciona cada parte y cómo se conectan entre sí. El proyecto está **completamente desarrollado** (Fases 1–6).

---

## Tabla de Contenidos

1. [Qué es este proyecto](#1-qué-es-este-proyecto)
2. [Stack tecnológico](#2-stack-tecnológico)
3. [Arquitectura general](#3-arquitectura-general)
4. [Cómo levantar el entorno local](#4-cómo-levantar-el-entorno-local)
5. [Modelo de datos](#5-modelo-de-datos)
6. [Backend — estructura de carpetas](#6-backend--estructura-de-carpetas)
7. [API — todos los endpoints](#7-api--todos-los-endpoints)
8. [Servicios — lógica de negocio](#8-servicios--lógica-de-negocio)
9. [Tareas Celery — background jobs](#9-tareas-celery--background-jobs)
10. [Frontend — páginas y componentes](#10-frontend--páginas-y-componentes)
11. [Autenticación — flujo completo](#11-autenticación--flujo-completo)
12. [Multi-tenant — cómo funciona](#12-multi-tenant--cómo-funciona)
13. [SLA y horas hábiles](#13-sla-y-horas-hábiles)
14. [Notificaciones — tiempo real y email](#14-notificaciones--tiempo-real-y-email)
15. [Flujos principales de negocio](#15-flujos-principales-de-negocio)
16. [Roles y permisos](#16-roles-y-permisos)
17. [Onboarding de nuevos tenants](#17-onboarding-de-nuevos-tenants)
18. [Estándares de código](#18-estándares-de-código)

---

## 1. Qué es este proyecto

**Smart Security** es una empresa colombiana de seguridad privada (~15 usuarios administrativos) que manejaba todas sus solicitudes internas por correo electrónico, sin trazabilidad ni métricas.

Este sistema es una **plataforma web de gestión de tickets internos**, construida como **multi-tenant desde el día 1** para poder vender a otras empresas sin tocar código.

### Qué resuelve
| Problema anterior | Solución implementada |
|---|---|
| Solicitudes perdidas en el correo | Tickets con número único y estado rastreable |
| Sin responsable claro | Enrutamiento automático por categoría y asignación por área |
| Sin visibilidad del estado | Dashboard en tiempo real + notificaciones WebSocket |
| Sin métricas | Reports de SLA compliance, performance por agente, reporte semanal |
| Sin trazabilidad | Historial inmutable de cada acción en el ticket |
| Sin cumplimiento de tiempos | Sistema de SLAs con cálculo en horas hábiles y alertas automáticas |

### Alcance del sistema
- Creación, seguimiento y cierre de tickets
- Enrutamiento automático por categoría → área → agente
- SLAs con monitoreo continuo (alertas 2h antes del breach)
- Tickets recurrentes por calendario (daily/weekly/monthly)
- Notificaciones en tiempo real (WebSocket) + email
- Dashboard con métricas y reporte semanal automatizado
- Gestión completa de usuarios, áreas, categorías
- Login local o Azure AD (SSO Microsoft 365)
- Branding configurable por tenant
- Superadmin para provisionar nuevos tenants

---

## 2. Stack tecnológico

| Capa | Tecnología |
|---|---|
| **Backend API** | FastAPI 0.104+ (Python 3.12), async |
| **ORM** | SQLAlchemy 2.0+ async + Alembic migraciones |
| **Base de datos** | PostgreSQL 16 |
| **Cache / Broker** | Redis 7 |
| **Background tasks** | Celery 5.3 + Celery Beat |
| **Autenticación** | JWT (python-jose) + MSAL (Azure AD) |
| **Emails** | aiosmtplib + Jinja2 templates |
| **Frontend** | Next.js 13+ (App Router), React 18, TypeScript |
| **Estado frontend** | TanStack React Query + Zustand |
| **Auth frontend** | NextAuth.js (CredentialsProvider + JWT strategy) |
| **UI** | Tailwind CSS + Radix UI + Lucide React |
| **Forms** | React Hook Form + Zod |
| **HTTP client** | Axios con interceptors de auto-refresh |
| **Contenerización** | Docker + Docker Compose |
| **Proxy inverso** | Nginx |
| **Mock SMTP (dev)** | MailHog (puerto 1025, UI en 8025) |

---

## 3. Arquitectura general

```
                        ┌─────────────────┐
                        │   Nginx proxy   │
                        └────────┬────────┘
                                 │
              ┌──────────────────┼──────────────────┐
              │                  │                  │
     ┌────────▼───────┐  ┌───────▼──────┐  ┌───────▼──────┐
     │  Next.js :3000  │  │ FastAPI :8000│  │ Static files │
     │  (frontend)     │  │  (backend)   │  │              │
     └────────┬────────┘  └───────┬──────┘  └──────────────┘
              │                  │
              │      ┌───────────┼────────────┐
              │      │           │            │
              │  ┌───▼──┐  ┌────▼───┐  ┌─────▼────┐
              │  │  DB   │  │ Redis  │  │ Storage  │
              │  │ PG:16 │  │  :6379 │  │ /storage │
              │  └───────┘  └────────┘  └──────────┘
              │                  │
              │            ┌─────┴──────┐
              │            │   Celery   │
              │            │ Worker/Beat│
              │            └────────────┘
              │
    NextAuth ←→ API (/api/v1/auth)
    React Query ←→ API (/api/v1/*)
    WebSocket ←→ API (/api/v1/notifications/ws)
```

### Principio de aislamiento multi-tenant
Todos los datos viven en la misma base de datos. Cada tabla principal tiene `tenant_id`. El `TenantMiddleware` inyecta el `tenant_id` desde el JWT en cada request. **Nunca se filtra manualmente por tenant en los servicios** — el middleware garantiza el aislamiento.

### Capas del backend (de request a DB)
```
Router (FastAPI) → Service (lógica negocio) → Repository (queries SQL) → DB
```
- Los **routers** validan permisos y parsean schemas Pydantic.
- Los **services** contienen la lógica de negocio (transiciones de estado, cálculo SLA, notificaciones).
- Los **repositories** son los únicos que hablan con SQLAlchemy.

---

## 4. Cómo levantar el entorno local

```bash
# Levantar todo (backend, frontend, db, redis, mailhog, celery worker + beat)
make dev
# o directamente:
docker-compose up --build

# Aplicar migraciones (solo la primera vez o después de nuevas migraciones)
docker-compose exec backend alembic upgrade head

# Seed de datos de prueba
docker-compose exec backend python scripts/seed.py

# URLs en desarrollo
# Frontend:  http://localhost:3000
# Backend:   http://localhost:8000
# API docs:  http://localhost:8000/docs
# MailHog:   http://localhost:8025
```

### Variables de entorno clave (`.env`)
```
DATABASE_URL=postgresql+asyncpg://postgres:postgres@db:5432/tickets
REDIS_URL=redis://redis:6379/0
SECRET_KEY=<clave-secreta-jwt>
SUPERADMIN_API_KEY=<clave-para-provisionar-tenants>

# Frontend
NEXTAUTH_URL=http://localhost:3000
NEXTAUTH_SECRET=<clave-nextauth>
NEXT_PUBLIC_API_URL=http://localhost:8000

# Azure AD (opcional, para login SSO)
AZURE_CLIENT_ID=...
AZURE_CLIENT_SECRET=...
AZURE_TENANT_ID=...
```

---

## 5. Modelo de datos

### Tablas principales y relaciones

```
tenants ──< tenant_configs (1:1)
tenants ──< users
tenants ──< areas
tenants ──< categories
tenants ──< slas
tenants ──< recurring_templates
tenants ──< notifications
tenants ──< tickets

users >──< areas (via user_areas — tabla pivote)
tickets >── users (requester_id, assigned_to)
tickets >── areas
tickets >── categories
tickets >── slas
tickets ──< ticket_comments
tickets ──< ticket_history
tickets ──< ticket_attachments
```

### Descripción de cada tabla

#### `tenants`
Empresa cliente. Identificada por `slug` (ej: `smart-security`) y `subdomain`.

| Campo | Tipo | Descripción |
|---|---|---|
| id | UUID PK | |
| slug | VARCHAR(100) unique | Identificador URL-safe |
| name | VARCHAR(255) | Nombre empresa |
| subdomain | VARCHAR(100) unique | Para routing multi-tenant |
| is_active | Boolean | Deshabilitar sin borrar |

#### `tenant_configs`
Configuración personalizada por tenant (1:1 con tenants).

| Campo | Descripción |
|---|---|
| primary_color | Branding (#1565C0 por defecto) |
| auth_method | `local` o `azure` |
| azure_* | Credenciales Azure AD |
| auto_close_days | Días para auto-cerrar tickets resueltos (default: 3) |
| urgency_abuse_threshold | % de tickets urgentes que activa alerta (default: 50) |
| timezone | Zona horaria tenant (default: America/Bogota) |
| working_hours_start/end | Horario laboral para cálculo SLA |
| working_days | Array de días [1..7] (default: [1,2,3,4,5]) |
| weekly_report_enabled | Toggle reporte semanal automático |
| weekly_report_day | Día de envío (1=lunes) |
| weekly_report_recipients | Emails de destinatarios |

#### `users`
```
id, tenant_id, email, full_name, password_hash, azure_oid,
role (admin|supervisor|agent|requester), is_active, is_archived,
avatar_url, last_login_at, deleted_at
```

#### `tickets`
```
id, tenant_id, ticket_number (#TK-0001),
title, description,
status (open|in_progress|pending|escalated|resolved|closed),
priority (low|medium|high|urgent),
category_id, area_id, requester_id, assigned_to, sla_id,
sla_due_at, sla_breached,
first_response_at, resolved_at, closed_at,
recurring_template_id, is_recurring_instance,
reopen_count, deleted_at
```

#### `ticket_comments`
```
id, ticket_id, author_id, body, is_internal, deleted_at
```
Los comentarios `is_internal=True` solo son visibles para agentes/admin/supervisores.

#### `ticket_history` (inmutable, audit trail)
```
id, ticket_id, actor_id, action, old_value (JSONB), new_value (JSONB)
```
Acciones registradas: `created`, `status_changed`, `assigned`, `escalated`, `comment_added`, `attachment_added`, `reopened`, `resolved`, `closed`.

#### `ticket_attachments`
```
id, ticket_id, comment_id, filename, file_path, file_size, mime_type, uploaded_by
```
Archivos en `/app/storage`. Acceso via signed URLs con expiración.

#### `areas`
```
id, tenant_id, name, description, manager_id, is_active
```

#### `user_areas` (pivote)
```
id, tenant_id, user_id, area_id, is_primary
```
Un usuario puede pertenecer a múltiples áreas. `is_primary` indica el área principal.

#### `categories`
```
id, tenant_id, name, description,
default_area_id, default_agent_id,
requires_approval, approver_role, is_active
```
Las categorías definen el **enrutamiento automático**: al crear un ticket, si la categoría tiene `default_area_id` o `default_agent_id`, se asignan automáticamente.

#### `slas`
```
id, tenant_id, category_id, priority,
response_hours, resolution_hours, is_active
```
Un SLA aplica para una combinación de `category_id` + `priority`. Si no hay SLA específico para la categoría, se usa el SLA por `priority` (category_id=NULL).

#### `recurring_templates`
```
id, tenant_id, title, description, category_id, area_id, priority, assigned_to,
recurrence_type (daily|weekly|monthly|day_of_month),
recurrence_value, recurrence_day,
if_holiday_action (skip|next_business_day|prev_business_day|same_day),
is_active, last_run_at, next_run_at, created_by
```

#### `notifications`
```
id, tenant_id, user_id, ticket_id, type, title, body,
is_read, read_at,
scheduled_for (para envío off-hours),
email_sent_at
```

---

## 6. Backend — estructura de carpetas

```
backend/
├── app/
│   ├── main.py              # Entry point FastAPI, registra routers y middleware
│   ├── config.py            # Settings (Pydantic BaseSettings, carga .env)
│   ├── database.py          # AsyncEngine + AsyncSession, get_db dependency
│   ├── dependencies.py      # Deps de auth: get_current_user, require_role, get_tenant
│   │
│   ├── middleware/
│   │   └── tenant.py        # TenantMiddleware: inyecta tenant_id desde JWT
│   │
│   ├── models/              # SQLAlchemy ORM models (1 archivo por entidad)
│   │   ├── base.py          # Base declarativa, TimestampMixin
│   │   ├── tenant.py        # Tenant, TenantConfig
│   │   ├── user.py          # User, UserArea
│   │   ├── ticket.py        # Ticket, TicketComment, TicketHistory, TicketAttachment
│   │   ├── area.py          # Area
│   │   ├── category.py      # Category
│   │   ├── sla.py           # SLA
│   │   ├── notification.py  # Notification
│   │   └── recurring.py     # RecurringTemplate
│   │
│   ├── schemas/             # Pydantic schemas (request/response)
│   │   ├── ticket.py        # TicketCreate, TicketResponse, TicketListItem, etc.
│   │   ├── comment.py       # CommentCreate, CommentResponse
│   │   ├── admin.py         # User/Area/Category/SLA/TenantConfig/Recurring schemas
│   │   ├── dashboard.py     # DashboardSummary, AgentPerformance, etc.
│   │   ├── notification.py  # NotificationResponse
│   │   └── common.py        # PaginatedResponse[T]
│   │
│   ├── repositories/        # Capa de acceso a datos (solo SQLAlchemy aquí)
│   │   ├── ticket_repository.py
│   │   ├── comment_repository.py
│   │   └── dashboard_repository.py
│   │
│   ├── services/            # Lógica de negocio
│   │   ├── ticket_service.py       # CRUD + transiciones de estado + SLA + routing
│   │   ├── comment_service.py      # Comentarios + validaciones
│   │   ├── notification_service.py # Crear notif + WebSocket + email scheduling
│   │   └── recurring_service.py   # Cálculo de next_run_at
│   │
│   ├── routers/             # Endpoints FastAPI (1 archivo por dominio)
│   │   ├── auth.py          # Login, logout, refresh, /me, Azure OAuth
│   │   ├── tickets.py       # CRUD + acciones de tickets
│   │   ├── users.py         # Gestión de usuarios
│   │   ├── areas.py         # Gestión de áreas + miembros
│   │   ├── admin.py         # Config, categories, SLAs, recurring templates
│   │   ├── dashboard.py     # Métricas y reportes
│   │   ├── notifications.py # Listado + WebSocket
│   │   ├── superadmin.py    # Provisioning de nuevos tenants
│   │   └── files.py         # Descarga de adjuntos con signed token
│   │
│   ├── tasks/               # Celery tasks
│   │   ├── celery_app.py    # Config Celery + Beat schedule
│   │   ├── sla_tasks.py     # check_sla_warnings, check_sla_breaches
│   │   ├── email_tasks.py   # send_notification_email y variantes
│   │   ├── notification_tasks.py # send_scheduled_notifications (off-hours)
│   │   ├── recurring_tasks.py    # process_recurring_tickets
│   │   └── report_tasks.py       # send_weekly_report
│   │
│   ├── utils/
│   │   ├── business_hours.py  # calculate_due_date, is_business_hour (zoneinfo)
│   │   ├── storage.py         # save_file, generate_signed_url, validate_signed_url
│   │   └── email.py           # send_email via aiosmtplib
│   │
│   └── templates/
│       └── emails/            # Plantillas Jinja2 HTML
│           ├── base.html
│           ├── welcome_tenant.html
│           ├── ticket_created.html
│           ├── ticket_assigned.html
│           ├── status_changed.html
│           ├── comment_added.html
│           ├── sla_warning.html
│           ├── sla_breached.html
│           ├── ticket_resolved.html
│           └── weekly_report.html
│
├── migrations/
│   ├── env.py
│   └── versions/
│       ├── 001_initial_schema.py           # Todas las tablas
│       └── 002_notification_scheduled_email.py  # Columnas scheduled_for, email_sent_at
│
├── scripts/
│   ├── create_tenant.py        # CLI de onboarding: crea tenant desde YAML
│   ├── seed.py                 # Datos de prueba
│   └── templates/
│       └── default_tenant.yaml # Template genérico (5 áreas, 7 categorías, 4 SLAs)
│
└── tests/
    ├── test_tickets.py
    └── test_sla.py
```

---

## 7. API — todos los endpoints

Prefijo base: `/api/v1`

### Auth — `/auth`

| Método | Ruta | Descripción | Auth |
|---|---|---|---|
| POST | `/auth/login` | Login email+password → access token | No |
| POST | `/auth/refresh` | Renovar access token (usa cookie refresh) | Cookie |
| POST | `/auth/logout` | Revocar refresh token | JWT |
| GET | `/auth/me` | Perfil del usuario autenticado | JWT |
| GET | `/auth/login/azure` | Iniciar flujo OAuth Azure AD | No |
| GET | `/auth/callback/azure` | Callback Azure AD → crear/actualizar user | No |

### Tickets — `/tickets`

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/tickets` | Listar tickets con filtros (status, priority, area, category, assigned_to, fechas, page, size) |
| POST | `/tickets` | Crear ticket nuevo |
| GET | `/tickets/{id}` | Detalle de ticket |
| PATCH | `/tickets/{id}` | Actualizar metadata (title, description, priority, category, area) |
| DELETE | `/tickets/{id}` | Soft-delete (admin only) |
| POST | `/tickets/{id}/status` | Cambiar estado (valida VALID_TRANSITIONS) |
| POST | `/tickets/{id}/assign` | Asignar a agente |
| POST | `/tickets/{id}/escalate` | Escalar con razón y área opcional |
| POST | `/tickets/{id}/resolve` | Marcar como resuelto |
| POST | `/tickets/{id}/close` | Cerrar (solo desde resuelto) |
| POST | `/tickets/{id}/reopen` | Reabrir con razón |
| GET | `/tickets/{id}/comments` | Listar comentarios |
| POST | `/tickets/{id}/comments` | Agregar comentario (público o interno) |
| PATCH | `/tickets/{id}/comments/{cid}` | Editar comentario (autor only, ventana 5 min) |
| GET | `/tickets/{id}/attachments` | Listar adjuntos con URLs firmadas |
| POST | `/tickets/{id}/attachments` | Subir archivo (PDF, Word, Excel, img; máx 10MB) |
| GET | `/tickets/{id}/attachments/{aid}/download` | Generar URL de descarga firmada |
| GET | `/tickets/{id}/history` | Audit trail completo |

### Users — `/users`

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/users` | Listar usuarios (filtros: role, is_active) |
| POST | `/users` | Crear usuario (admin only) |
| GET | `/users/{id}` | Perfil de usuario |
| PATCH | `/users/{id}` | Actualizar usuario (admin only) |
| POST | `/users/{id}/archive` | Archivar + reasignar tickets abiertos (admin only) |

### Areas — `/areas`

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/areas` | Listar áreas (active_only opcional) |
| POST | `/areas` | Crear área (admin only) |
| PATCH | `/areas/{id}` | Actualizar área (admin/supervisor) |
| DELETE | `/areas/{id}` | Eliminar área (admin only) |
| GET | `/areas/{id}/members` | Listar miembros del área |
| POST | `/areas/{id}/members` | Agregar miembro (admin/supervisor) |
| DELETE | `/areas/{id}/members/{user_id}` | Remover miembro (admin/supervisor) |

### Admin — `/admin`

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/admin/config` | Obtener config del tenant |
| PATCH | `/admin/config` | Actualizar config + invalidar cache Redis |
| GET | `/admin/categories` | Listar categorías |
| POST | `/admin/categories` | Crear categoría |
| PATCH | `/admin/categories/{id}` | Actualizar categoría |
| GET | `/admin/slas` | Listar SLAs |
| POST | `/admin/slas` | Crear SLA |
| PATCH | `/admin/slas/{id}` | Actualizar SLA |
| GET | `/admin/recurring` | Listar templates recurrentes |
| POST | `/admin/recurring` | Crear template (calcula next_run_at) |
| PATCH | `/admin/recurring/{id}` | Actualizar + recalcular schedule |
| DELETE | `/admin/recurring/{id}` | Desactivar template (soft-delete) |

### Dashboard — `/dashboard`

| Método | Ruta | Descripción | Acceso |
|---|---|---|---|
| GET | `/dashboard/summary` | KPIs: total, abiertos, resueltos, avg resolución, SLA% | Todos |
| GET | `/dashboard/tickets-by-area` | Distribución por área | Todos |
| GET | `/dashboard/tickets-by-status` | Distribución por estado + % | Todos |
| GET | `/dashboard/sla-compliance` | Compliance SLA general y por prioridad | Admin/Supervisor |
| GET | `/dashboard/agent-performance` | Métricas por agente | Admin/Supervisor |
| GET | `/dashboard/user-performance` | Performance detallado para decisiones | Admin/Supervisor |
| GET | `/dashboard/urgency-abuse` | Usuarios con abuso de prioridad urgente | Admin configurable |
| GET | `/dashboard/weekly-report` | Datos para reporte semanal email | Admin/Supervisor |

### Notifications — `/notifications`

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/notifications` | Listar notificaciones paginadas (unread_only opcional) |
| POST | `/notifications/read-all` | Marcar todas como leídas |
| PATCH | `/notifications/{id}/read` | Marcar una como leída |
| WS | `/notifications/ws?token=JWT` | WebSocket para notificaciones en tiempo real |

### Superadmin — `/superadmin`

| Método | Ruta | Descripción | Auth |
|---|---|---|---|
| POST | `/superadmin/tenants` | Crear tenant completo desde YAML | X-API-Key header |

### Files — `/files`

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/files/download?token=...` | Descargar archivo con signed token |

---

## 8. Servicios — lógica de negocio

### `ticket_service.py`

**Responsabilidades:**
- Crear tickets: genera número secuencial con `pg_advisory_xact_lock`, asigna SLA, calcula `sla_due_at`, aplica routing por categoría.
- Validar transiciones de estado con esta máquina de estados:

```python
VALID_TRANSITIONS = {
    "open":        {"in_progress", "pending", "escalated"},
    "in_progress": {"pending", "escalated", "resolved"},
    "pending":     {"in_progress", "escalated"},
    "escalated":   {"in_progress", "resolved"},
    "resolved":    {"closed"},
    "closed":      set(),  # Estado terminal
}
```

- Calcular `sla_status` (`ok` / `warning` / `breached`) y `sla_percentage` en cada respuesta.
- Generar y validar signed URLs para adjuntos.
- Disparar notificaciones en cada acción relevante.

### `comment_service.py`

- Valida que requesters no puedan crear comentarios internos (`is_internal=True`).
- Ventana de edición: 5 minutos desde `created_at`.
- Filtra comentarios internos según el rol del usuario que consulta.

### `notification_service.py`

- `create_and_send(user_id, ticket_id, type, ...)`:
  1. Crea registro en `notifications`.
  2. Publica en Redis pub/sub `notifications:{user_id}` (WebSocket).
  3. Si el destinatario está fuera de horario laboral → `scheduled_for` = inicio del próximo día hábil.
  4. Encola tarea Celery `send_notification_email`.

### `recurring_service.py`

- `calculate_next_run(template, tenant_config)`: calcula la próxima ejecución respetando timezone y `if_holiday_action`:
  - `skip`: si cae en festivo, saltar.
  - `next_business_day`: mover al siguiente día hábil.
  - `prev_business_day`: mover al anterior.
  - `same_day`: ejecutar igual aunque sea festivo.

---

## 9. Tareas Celery — background jobs

### Schedule (definido en `celery_app.py`)

| Task | Frecuencia | Descripción |
|---|---|---|
| `check_sla_warnings` | Cada 30 min | Tickets con SLA a 2h de vencer → notificación warning |
| `check_sla_breaches` | Cada 15 min | Tickets con SLA vencido → marcar `sla_breached=True` + notificación |
| `process_recurring_tickets` | Cada hora | Genera tickets desde templates con `next_run_at <= now` |
| `send_scheduled_notifications` | Cada 5 min | Envía emails con `scheduled_for <= now` (notificaciones off-hours) |

### Notas importantes sobre Celery

- Las tasks usan `_run_async()` como wrapper porque Celery es síncrono pero el ORM es async. **No usar `asyncio.run()` directamente** (conflicto con asyncpg).
- La generación de `ticket_number` usa `pg_advisory_xact_lock` para evitar duplicados en concurrencia.
- Todos los modelos SQLAlchemy deben estar importados antes de ejecutar queries en las tasks.

---

## 10. Frontend — páginas y componentes

### Estructura de rutas (`src/app/`)

```
(auth)/
  login/page.tsx           ← Formulario login (local + botón Azure AD)
  azure-callback/page.tsx  ← Intercepta callback OAuth, completa sesión NextAuth

(dashboard)/               ← Requiere sesión activa (middleware.ts)
  page.tsx                 ← Dashboard: stat cards + gráficos + performance
  tickets/
    page.tsx               ← Tabla con filtros avanzados y paginación
    new/page.tsx           ← Formulario de creación de ticket
    [id]/page.tsx          ← Detalle: timeline, comentarios, adjuntos, cambios estado
  reports/page.tsx         ← SLA compliance + agent performance + urgency abuse
  admin/
    users/page.tsx         ← CRUD usuarios + archivar
    areas/page.tsx         ← CRUD áreas + panel de miembros expandible
    categories/page.tsx    ← CRUD categorías + toggle activo/inactivo
    slas/page.tsx          ← CRUD SLAs + confirmación eliminación
    recurring/page.tsx     ← CRUD templates recurrentes + toggle
    config/page.tsx        ← Branding, horario laboral, días, reporte semanal
```

### Componentes clave (`src/components/`)

| Componente | Descripción |
|---|---|
| `NotificationBell.tsx` | Campana con badge unread, dropdown de notificaciones recientes |
| `shared/Topbar.tsx` | Header: logo, nombre usuario, campana, menú logout |
| `shared/Sidebar.tsx` | Navegación lateral (ítems visibles según rol) |
| `tickets/TicketTable.tsx` | Tabla con columnas configurables, sort, paginación |
| `tickets/TicketDetail.tsx` | Vista completa ticket: timeline, comentarios, adjuntos |
| `tickets/StatusBadge.tsx` | Pill de color por estado |
| `tickets/PriorityBadge.tsx` | Pill de color por prioridad |
| `tickets/SLAIndicator.tsx` | Barra de progreso SLA con color según estado |
| `dashboard/StatsRow.tsx` | 4 tarjetas de KPIs |
| `dashboard/TicketsByAreaChart.tsx` | Bar chart por área |
| `dashboard/StatusDonut.tsx` | Donut chart de distribución por estado |

### Hooks React Query (`src/hooks/`)

**`useTickets.ts`** — todos los hooks de tickets:
```typescript
useTicketList(filters)       // GET /tickets
useTicket(id)                // GET /tickets/{id}
useTicketComments(ticketId)  // GET /tickets/{id}/comments
useTicketHistory(ticketId)   // GET /tickets/{id}/history
useTicketAttachments(id)     // GET /tickets/{id}/attachments
useCreateTicket()            // POST /tickets
useUpdateTicket(id)          // PATCH /tickets/{id}
useChangeStatus(id)          // POST /tickets/{id}/status
useAssignTicket(id)          // POST /tickets/{id}/assign
useResolveTicket(id)         // POST /tickets/{id}/resolve
useCloseTicket(id)           // POST /tickets/{id}/close
useReopenTicket(id)          // POST /tickets/{id}/reopen
useAddComment(id)            // POST /tickets/{id}/comments
useUploadAttachment(id)      // POST /tickets/{id}/attachments
```

**`useDashboard.ts`**:
```typescript
useDashboardSummary()
useTicketsByArea()
useTicketsByStatus()
useAgentPerformance()
useUserPerformance(days)
useUrgencyAbuse()
```

**`useWebSocket.ts`**:
- Conecta a `ws://{api}/api/v1/notifications/ws?token={jwt}`
- Reconnect automático con exponential backoff (1s → 2s → 4s → ... → 30s max)
- Al recibir mensaje → `notificationStore.addNotification()`

### Estado global (`src/store/`)

**`notificationStore.ts`** (Zustand):
```typescript
state:   notifications[], unreadCount
actions: addNotification, setNotifications, markOneRead, markAllRead
```

### Cliente HTTP (`src/lib/api.ts`)

Axios con interceptors:
1. **Request**: agrega `Authorization: Bearer {token}` desde sesión NextAuth.
2. **Response error 401**: intenta `POST /auth/refresh` automáticamente. Si falla → `signOut()`.

---

## 11. Autenticación — flujo completo

### Login local
```
Frontend (login form)
  → POST /api/v1/auth/login {email, password}
  ← { access_token, token_type }  + Set-Cookie: refresh_token (HttpOnly, 7d)
  → NextAuth.signIn('credentials') guarda token en sesión
  → Middleware.ts protege rutas /dashboard/*
```

### Login Azure AD
```
Frontend (botón "Ingresar con Microsoft")
  → GET /api/v1/auth/login/azure
  ← Redirect a login.microsoftonline.com
  → Usuario autentica en Microsoft
  → Redirect a GET /api/v1/auth/callback/azure
  ← Crea/actualiza User con azure_oid
  ← { access_token } en query param
  → Frontend /azure-callback captura token → NextAuth.signIn('credentials')
```

### Refresh automático
```
Axios interceptor detecta 401
  → POST /api/v1/auth/refresh (cookie refresh_token en header automático)
  ← { access_token } nuevo
  → Reintenta request original con nuevo token
  → Si refresh falla → NextAuth.signOut() → redirect /login
```

### JWT payload
```json
{
  "sub": "user_id",
  "tenant_id": "tenant_uuid",
  "role": "admin|supervisor|agent|requester",
  "exp": 1234567890
}
```

---

## 12. Multi-tenant — cómo funciona

### Resolución de tenant en cada request
1. `TenantMiddleware` extrae `Authorization: Bearer {jwt}`.
2. Decodifica JWT → obtiene `tenant_id` y `role`.
3. Inyecta `request.state.tenant_id` y `request.state.current_user`.
4. Todos los servicios y repositorios leen `tenant_id` de `request.state`.

### Onboarding de nuevo tenant
Dos opciones:

**Opción A — Script CLI:**
```bash
python scripts/create_tenant.py --config mi_empresa.yaml
```

**Opción B — API REST:**
```bash
curl -X POST /api/v1/superadmin/tenants \
  -H "X-API-Key: {SUPERADMIN_API_KEY}" \
  -H "Content-Type: application/json" \
  -d @tenant_config.json
```

Ambas crean: `Tenant` + `TenantConfig` + usuario admin + áreas + categorías + SLAs.
El admin recibe email de bienvenida con credenciales (`welcome_tenant.html`).

El archivo `backend/scripts/templates/default_tenant.yaml` es la plantilla base con 5 áreas, 7 categorías y 4 SLAs predefinidos.

---

## 13. SLA y horas hábiles

### Cómo se asigna un SLA a un ticket
Al crear el ticket, `ticket_service.py` busca el SLA más específico:
1. SLA con `category_id == ticket.category_id` y `priority == ticket.priority`.
2. Si no existe → SLA con `category_id == NULL` y `priority == ticket.priority`.
3. Si no existe → sin SLA (ticket sin fecha límite).

### Cálculo de `sla_due_at`
```python
# business_hours.py
calculate_due_date(start_datetime, hours, tenant_config)
```
Suma `resolution_hours` al tiempo de creación, saltando:
- Horas fuera de `working_hours_start/end`.
- Días no listados en `working_days`.
- La zona horaria del tenant (`zoneinfo`).

### Monitoreo de SLA (Celery Beat)
- **Cada 15 min**: `check_sla_breaches` → tickets con `sla_due_at < now` y `sla_breached=False` → marca flag + notificación.
- **Cada 30 min**: `check_sla_warnings` → tickets con `sla_due_at` entre `now` y `now + 2h` → notificación warning.

### Indicador visual en frontend
`SLAIndicator.tsx` muestra:
- **Verde** (ok): menos del 75% del tiempo consumido.
- **Amarillo** (warning): 75%–99%.
- **Rojo** (breached): 100%+.

---

## 14. Notificaciones — tiempo real y email

### Flujo completo de una notificación

```
Acción en backend (ej: ticket asignado)
  → notification_service.create_and_send()
    1. INSERT en tabla notifications
    2. PUBLISH en Redis: PUBLISH notifications:{user_id} {json_payload}
       → WebSocket handler recibe → envía al cliente conectado
    3. ¿Es horario laboral?
       Sí → enqueue email_task inmediatamente
       No → SET scheduled_for = inicio próximo día hábil
             → Celery beat (cada 5 min) envía emails scheduled

Frontend (WebSocket conectado):
  → Recibe JSON → notificationStore.addNotification()
  → NotificationBell.tsx actualiza badge unreadCount
```

### Tipos de notificación
| Tipo | Cuándo se dispara |
|---|---|
| `ticket_created` | Al crear el ticket (al requester) |
| `ticket_assigned` | Al asignar agente |
| `comment_added` | Al agregar comentario público |
| `sla_warning` | 2h antes del vencimiento SLA |
| `sla_breached` | Al detectar breach de SLA |
| `ticket_resolved` | Al marcar como resuelto |
| `ticket_closed` | Al cerrar el ticket |

### Plantillas de email
Todas heredan de `base.html` (header con logo/color del tenant, footer). Se renderizan con Jinja2 pasando el contexto del ticket/tenant.

---

## 15. Flujos principales de negocio

### Crear y resolver un ticket (happy path)

```
1. Requester crea ticket → POST /tickets
   - Se genera #TK-XXXX (número secuencial por tenant)
   - Se busca SLA por category + priority → se calcula sla_due_at
   - Si category tiene default_area/agent → se asigna automáticamente
   - Historial: action="created"
   - Notificación: ticket_created → requester

2. Agente toma el ticket → POST /tickets/{id}/status {new_status: "in_progress"}
   - Valida transición open → in_progress ✓
   - Se registra first_response_at (si no tenía)
   - Historial: action="status_changed"

3. Agente comenta → POST /tickets/{id}/comments
   - Comentario público → notificación comment_added al requester
   - Comentario interno → solo visible para agentes/admin/supervisores

4. Agente resuelve → POST /tickets/{id}/resolve
   - Estado: in_progress → resolved
   - Se registra resolved_at
   - Notificación: ticket_resolved al requester
   - Historial: action="resolved"

5. Auto-close (Celery) o manual → POST /tickets/{id}/close
   - Estado: resolved → closed (terminal)
   - Se registra closed_at
```

### Escalación

```
Agente escala → POST /tickets/{id}/escalate {reason, area_id?}
  - Estado: in_progress → escalated
  - Si area_id: se cambia el área asignada
  - Historial: action="escalated" con reason en new_value
  - Supervisor del área recibe notificación
```

### Tickets recurrentes

```
Admin crea template → POST /admin/recurring
  - recurring_service.calculate_next_run() determina next_run_at

Celery Beat (cada hora) → process_recurring_tickets
  - Encuentra templates con is_active=True y next_run_at <= now
  - Crea ticket con datos del template (is_recurring_instance=True)
  - Actualiza last_run_at y calcula nuevo next_run_at
  - Si fecha cae en festivo → aplica if_holiday_action
```

---

## 16. Roles y permisos

| Acción | Requester | Agent | Supervisor | Admin |
|---|---|---|---|---|
| Ver sus propios tickets | ✅ | - | - | - |
| Ver tickets de sus áreas | - | ✅ | ✅ | ✅ |
| Ver todos los tickets | - | - | ✅* | ✅ |
| Crear ticket | ✅ | ✅ | ✅ | ✅ |
| Cambiar estado | - | ✅ | ✅ | ✅ |
| Asignar agente | - | ✅ | ✅ | ✅ |
| Comentario interno | - | ✅ | ✅ | ✅ |
| Ver comentarios internos | - | ✅ | ✅ | ✅ |
| CRUD usuarios | - | - | - | ✅ |
| CRUD áreas | - | - | ✅** | ✅ |
| CRUD categorías | - | - | - | ✅ |
| CRUD SLAs | - | - | - | ✅ |
| Ver SLA compliance | - | - | ✅ | ✅ |
| Ver agent performance | - | - | ✅ | ✅ |
| Config tenant | - | - | - | ✅ |

\* Supervisores ven todos los tickets pero reportes limitados a sus áreas.  
\*\* Supervisores pueden gestionar miembros de sus propias áreas.

### Dependency FastAPI
```python
# dependencies.py
get_current_user  → verifica JWT válido
require_role(["admin", "supervisor"])  → verifica rol del usuario
```

---

## 17. Onboarding de nuevos tenants

### Estructura del YAML de configuración

```yaml
tenant:
  name: "Nueva Empresa SAS"
  slug: "nueva-empresa"
  subdomain: "nueva-empresa"
  timezone: "America/Bogota"
  auth_method: "local"  # o "azure"
  working_hours_start: "08:00"
  working_hours_end: "18:00"
  working_days: [1, 2, 3, 4, 5]

admin:
  email: "admin@nueva-empresa.com"
  full_name: "Administrador"
  password: "CambiarEsto123!"

areas:
  - name: "TI"
    description: "Soporte tecnológico"
  - name: "RRHH"
    description: "Recursos humanos"

categories:
  - name: "Soporte técnico"
    default_area: "TI"
  - name: "Solicitud de personal"
    default_area: "RRHH"

slas:
  - priority: "urgent"
    response_hours: 2
    resolution_hours: 8
  - priority: "high"
    response_hours: 4
    resolution_hours: 24
  - priority: "medium"
    response_hours: 8
    resolution_hours: 48
  - priority: "low"
    response_hours: 24
    resolution_hours: 72
```

---

## 18. Estándares de código

### Backend

- **Async everywhere**: todos los endpoints y servicios son `async def`. Las tasks Celery usan `_run_async()` wrapper.
- **Separación de capas**: nunca SQLAlchemy en servicios, nunca lógica de negocio en repositories.
- **Tenant safety**: todo query va filtrado por `tenant_id`. Nunca hacer query sin él.
- **Schemas Pydantic v2**: usar `model_validate`, no `from_orm`. Configurar con `model_config = ConfigDict(from_attributes=True)`.
- **Errores**: usar `HTTPException` con códigos semánticos. No capturar excepciones genéricas.
- **HMAC**: las signed URLs de archivos usan `hmac.compare_digest` para comparación segura.

### Frontend

- **React Query para todo el estado servidor**: no usar `useState` + `useEffect` para fetching.
- **Zustand solo para estado global cliente**: notificaciones, preferencias de UI.
- **TypeScript estricto**: todos los tipos definidos en `src/types/`. No usar `any`.
- **`cn()` de `utils.ts`** para clases Tailwind condicionales.
- **Formularios**: React Hook Form + Zod schema. No validar manualmente.
- **Rutas protegidas**: `middleware.ts` redirige a `/login` si no hay sesión NextAuth.

### Convenciones de nomenclatura

| Elemento | Convención | Ejemplo |
|---|---|---|
| Archivos Python | snake_case | `ticket_service.py` |
| Clases Python | PascalCase | `TicketService` |
| Funciones Python | snake_case | `create_ticket()` |
| Archivos TS/TSX | kebab-case | `ticket-table.tsx` o PascalCase para componentes |
| Componentes React | PascalCase | `TicketTable` |
| Hooks React | camelCase con `use` | `useTicketList()` |
| Endpoints API | kebab-case | `/api/v1/tickets-by-area` |
| Tablas DB | snake_case plural | `ticket_comments` |

---

*Documento generado: mayo 2026 · Proyecto completado Fases 1–6 · Fase 7 pendiente (tests completos + despliegue VPS)*
