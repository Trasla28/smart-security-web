# Plan de Pruebas — Sistema de Tickets Smart Security
## Fases 1, 2, 4, 5 y 6

**Versión:** 4.0
**Fecha:** 2026-03-16
**Alcance:** Fase 1 (Autenticación + Modelos), Fase 2 (Tickets, Comentarios, SLA), Fase 4 (Tickets Recurrentes, Dashboard, Panel Admin), Fase 5 (Frontend Completo) y Fase 6 (Multi-Tenant y Onboarding)
**Ambiente de prueba:** Docker local (`make dev`)

---

## Índice

1. [Alcance y Objetivos](#1-alcance-y-objetivos)
2. [Ambiente y Precondiciones](#2-ambiente-y-precondiciones)
3. [Datos de Prueba (Seed)](#3-datos-de-prueba-seed)
4. [FASE 1 — Autenticación](#4-fase-1--autenticación)
5. [FASE 1 — Modelos y Base de Datos](#5-fase-1--modelos-y-base-de-datos)
6. [FASE 2 — Tickets CRUD](#6-fase-2--tickets-crud)
7. [FASE 2 — Transiciones de Estado](#7-fase-2--transiciones-de-estado)
8. [FASE 2 — Comentarios](#8-fase-2--comentarios)
9. [FASE 2 — Historial de Auditoría](#9-fase-2--historial-de-auditoría)
10. [FASE 2 — Archivos Adjuntos](#10-fase-2--archivos-adjuntos)
11. [FASE 2 — SLA y Horas de Negocio](#11-fase-2--sla-y-horas-de-negocio)
12. [FASE 2 — Visibilidad y Control de Acceso (RBAC)](#12-fase-2--visibilidad-y-control-de-acceso-rbac)
13. [FASE 2 — Auto-enrutamiento de Tickets](#13-fase-2--auto-enrutamiento-de-tickets)
14. [Validaciones de Entrada (todos los endpoints)](#14-validaciones-de-entrada-todos-los-endpoints)
15. [Seguridad y Multi-tenant](#15-seguridad-y-multi-tenant)
16. [Tareas Celery (SLA)](#16-tareas-celery-sla)
17. [Casos de Error Esperados](#17-casos-de-error-esperados)
18. [Matriz de Cobertura por Rol](#18-matriz-de-cobertura-por-rol)
19. [FASE 4 — Gestión de Usuarios](#19-fase-4--gestión-de-usuarios)
20. [FASE 4 — Gestión de Áreas](#20-fase-4--gestión-de-áreas)
21. [FASE 4 — Panel de Administración (Categorías, SLAs, Config)](#21-fase-4--panel-de-administración-categorías-slas-config)
22. [FASE 4 — Tickets Recurrentes](#22-fase-4--tickets-recurrentes)
23. [FASE 4 — Dashboard y Reportes](#23-fase-4--dashboard-y-reportes)
24. [FASE 4 — Tareas Celery (Recurrentes y Reportes)](#24-fase-4--tareas-celery-recurrentes-y-reportes)
25. [Matriz de Cobertura por Rol — Fase 4](#25-matriz-de-cobertura-por-rol--fase-4)
26. [FASE 5 — Autenticación Frontend](#26-fase-5--autenticación-frontend)
27. [FASE 5 — Dashboard Principal](#27-fase-5--dashboard-principal)
28. [FASE 5 — Gestión de Tickets (Lista y Filtros)](#28-fase-5--gestión-de-tickets-lista-y-filtros)
29. [FASE 5 — Detalle de Ticket](#29-fase-5--detalle-de-ticket)
30. [FASE 5 — Crear Ticket](#30-fase-5--crear-ticket)
31. [FASE 5 — Panel Admin — Usuarios](#31-fase-5--panel-admin--usuarios)
32. [FASE 5 — Panel Admin — Áreas](#32-fase-5--panel-admin--áreas)
33. [FASE 5 — Panel Admin — Categorías](#33-fase-5--panel-admin--categorías)
34. [FASE 5 — Panel Admin — SLAs](#34-fase-5--panel-admin--slas)
35. [FASE 5 — Panel Admin — Plantillas Recurrentes](#35-fase-5--panel-admin--plantillas-recurrentes)
36. [FASE 5 — Panel Admin — Configuración](#36-fase-5--panel-admin--configuración)
37. [FASE 5 — Reportes](#37-fase-5--reportes)
38. [FASE 5 — Notificaciones y WebSocket](#38-fase-5--notificaciones-y-websocket)
39. [Matriz de Cobertura — Fase 5](#39-matriz-de-cobertura--fase-5)
40. [FASE 6 — Script CLI de Onboarding](#40-fase-6--script-cli-de-onboarding)
41. [FASE 6 — API Superadmin (POST /superadmin/tenants)](#41-fase-6--api-superadmin-post-superadmintenants)
42. [FASE 6 — Verificación del Tenant Provisionado](#42-fase-6--verificación-del-tenant-provisionado)
43. [FASE 6 — Plantilla YAML y Configuración](#43-fase-6--plantilla-yaml-y-configuración)
44. [FASE 6 — Seguridad del Endpoint Superadmin](#44-fase-6--seguridad-del-endpoint-superadmin)
45. [Matriz de Cobertura — Fase 6](#45-matriz-de-cobertura--fase-6)

---

## 1. Alcance y Objetivos

### 1.1 Objetivo General
Verificar que las Fases 1 y 2 del sistema de tickets funcionan correctamente, cubriendo autenticación, ciclo de vida de tickets, permisos por rol, SLA, comentarios y adjuntos.

### 1.2 Funcionalidades en Alcance

| Componente | Incluido |
|---|---|
| Login email/contraseña | ✅ |
| Login Azure AD (MSAL) | ✅ |
| Refresh / Logout de tokens | ✅ |
| Middleware multi-tenant | ✅ |
| Creación y edición de tickets | ✅ |
| Transiciones de estado (máquina de estados) | ✅ |
| Auto-enrutamiento por categoría | ✅ |
| Asignación de agente | ✅ |
| Escalamiento | ✅ |
| Cierre y reapertura | ✅ |
| Comentarios públicos e internos | ✅ |
| Edición de comentarios (ventana 5 min) | ✅ |
| Historial inmutable de auditoría | ✅ |
| Carga y descarga de adjuntos | ✅ |
| Cálculo de SLA en horas de negocio | ✅ |
| Alertas y breaches de SLA (Celery) | ✅ |
| Visibilidad por rol (RBAC) | ✅ |
| Paginación y filtros | ✅ |

### 1.3 Fuera de Alcance
- Frontend / Next.js
- Notificaciones WebSocket (Fase 3)
- Dashboard / Reportes (Fase 4)
- Gestión de usuarios, áreas, categorías (Fase 4)

---

## 2. Ambiente y Precondiciones

### 2.1 Levantar el stack local

```bash
make dev
# Verifica que todos los contenedores estén arriba:
docker compose ps
```

Servicios esperados: `backend`, `postgres`, `redis`, `celery_worker`

### 2.2 Aplicar migraciones y seed

```bash
docker compose exec backend alembic upgrade head
docker compose exec backend python seed.py
```

### 2.3 Verificar health check

```http
GET /health
→ 200 { "status": "ok" }
```

### 2.4 Herramientas recomendadas
- **Postman / Insomnia** para pruebas manuales de API
- **pytest** para pruebas automatizadas (`make test`)
- **psql / DBeaver** para verificación directa en BD
- **Redis CLI** para verificar tokens almacenados

### 2.5 Variables de entorno mínimas para pruebas

```env
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/tickets_dev
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=dev-secret-key-do-not-use-in-prod
STORAGE_PATH=/tmp/tickets_storage
ENVIRONMENT=development
```

---

## 3. Datos de Prueba (Seed)

El archivo `seed.py` debe generar los siguientes datos. Verificar que existan antes de ejecutar los tests.

### 3.1 Tenant

| Campo | Valor |
|---|---|
| id | `tenant-uuid-1` (UUID fijo para reproducibilidad) |
| slug | `smart-security` |
| name | `Smart Security` |
| subdomain | `smartsecurity` |
| is_active | `true` |

### 3.2 Usuarios de prueba

| Alias | Email | Contraseña | Rol |
|---|---|---|---|
| ADMIN | admin@smartsecurity.co | Admin123! | admin |
| SUPERVISOR | supervisor@smartsecurity.co | Super123! | supervisor |
| AGENT_1 | agente1@smartsecurity.co | Agent123! | agent |
| AGENT_2 | agente2@smartsecurity.co | Agent123! | agent |
| REQUESTER_1 | solicitante1@smartsecurity.co | Req123! | requester |
| REQUESTER_2 | solicitante2@smartsecurity.co | Req123! | requester |

### 3.3 Áreas de prueba

| Alias | Nombre |
|---|---|
| AREA_TI | Tecnología |
| AREA_RRHH | Recursos Humanos |

AGENT_1 asignado a AREA_TI (primaria).
AGENT_2 asignado a AREA_RRHH (primaria).

### 3.4 Categorías de prueba

| Alias | Nombre | default_area_id | default_agent_id |
|---|---|---|---|
| CAT_INCIDENTE | Incidente TI | AREA_TI | null |
| CAT_SOLICITUD | Solicitud RRHH | AREA_RRHH | AGENT_2 |
| CAT_LIBRE | Sin ruta | null | null |

### 3.5 SLAs de prueba

| Alias | category_id | priority | response_hours | resolution_hours |
|---|---|---|---|---|
| SLA_URGENTE | null | urgent | 1 | 4 |
| SLA_ALTO | null | high | 2 | 8 |
| SLA_MEDIO | null | medium | 4 | 24 |
| SLA_BAJO | null | low | 8 | 72 |
| SLA_INCIDENTE_URGENTE | CAT_INCIDENTE | urgent | 0.5 | 2 |

---

## 4. FASE 1 — Autenticación

### TC-AUTH-001: Login exitoso con credenciales válidas

**Endpoint:** `POST /api/v1/auth/login`
**Precondición:** Usuario ADMIN existe y está activo

**Request:**
```json
{
  "email": "admin@smartsecurity.co",
  "password": "Admin123!"
}
```

**Resultado esperado:**
- HTTP 200
- Body contiene `access_token` (string no vacío)
- Cookie `refresh_token` presente (HttpOnly)
- `token_type` = "bearer"

**Verificación adicional:**
- Decodificar el JWT: claims deben contener `sub` (user_id), `tenant_id`, `role` = "admin", `type` = "access"
- `exp` debe ser aproximadamente 15 minutos en el futuro

---

### TC-AUTH-002: Login con contraseña incorrecta

**Request:**
```json
{
  "email": "admin@smartsecurity.co",
  "password": "Incorrect!"
}
```

**Resultado esperado:**
- HTTP 401
- Body: `{ "detail": "Credenciales inválidas" }` (o similar)
- NO debe incluir `access_token`

---

### TC-AUTH-003: Login con email inexistente

**Request:**
```json
{
  "email": "noexiste@smartsecurity.co",
  "password": "cualquiera"
}
```

**Resultado esperado:**
- HTTP 401
- Mensaje genérico (no debe revelar si el email existe)

---

### TC-AUTH-004: Login con usuario inactivo

**Precondición:** Marcar AGENT_2 como `is_active = false` en BD

**Request:**
```json
{
  "email": "agente2@smartsecurity.co",
  "password": "Agent123!"
}
```

**Resultado esperado:**
- HTTP 401 o 403
- No debe generar token

**Postcondición:** Restaurar `is_active = true`

---

### TC-AUTH-005: Refresh token — genera nuevo access token

**Precondición:** Obtener `refresh_token` cookie del TC-AUTH-001

**Request:** `POST /api/v1/auth/refresh`
Cookie: `refresh_token=<token_obtenido>`

**Resultado esperado:**
- HTTP 200
- Nuevo `access_token` (diferente al anterior)
- Cookie `refresh_token` renovada

---

### TC-AUTH-006: Refresh token inválido o expirado

**Request:** `POST /api/v1/auth/refresh`
Cookie: `refresh_token=token.invalido.xxx`

**Resultado esperado:**
- HTTP 401

---

### TC-AUTH-007: Logout revoca el refresh token

**Precondición:** Obtener `refresh_token` cookie

**Paso 1:** `POST /api/v1/auth/logout`
**Resultado paso 1:** HTTP 200, `{ "message": "..." }`

**Paso 2:** Intentar `POST /api/v1/auth/refresh` con el mismo refresh_token
**Resultado paso 2:** HTTP 401 (token revocado)

**Verificación Redis:**
```bash
redis-cli KEYS "refresh:*"
# La clave del token eliminado NO debe aparecer
```

---

### TC-AUTH-008: GET /me devuelve el usuario autenticado

**Request:** `GET /api/v1/auth/me`
Header: `Authorization: Bearer <access_token_admin>`

**Resultado esperado:**
- HTTP 200
- `email` = "admin@smartsecurity.co"
- `role` = "admin"
- `tenant_id` = ID del tenant

---

### TC-AUTH-009: GET /me sin token

**Request:** `GET /api/v1/auth/me` (sin Authorization header)

**Resultado esperado:**
- HTTP 401 o 403

---

### TC-AUTH-010: GET /me con token de otro tenant

**Precondición:** Crear un segundo tenant y usuario en BD

**Request:** `GET /api/v1/auth/me`
Header: `Authorization: Bearer <token_de_tenant_2>`

**Resultado esperado:**
- HTTP 200 pero con datos del usuario del tenant 2
- `tenant_id` debe ser del tenant 2 (no del tenant 1)

---

### TC-AUTH-011: Acceso a endpoint protegido con access token expirado

**Precondición:** Generar un JWT manualmente con `exp` en el pasado

**Resultado esperado:**
- HTTP 401

---

### TC-AUTH-012: Login con usuario archivado

**Precondición:** Marcar AGENT_1 como `is_archived = true`

**Resultado esperado:**
- HTTP 401 o 403

**Postcondición:** Restaurar `is_archived = false`

---

## 5. FASE 1 — Modelos y Base de Datos

### TC-DB-001: Verificar que las 13 tablas existen

```sql
SELECT tablename FROM pg_tables
WHERE schemaname = 'public'
ORDER BY tablename;
```

**Resultado esperado (mínimo):**
`areas`, `categories`, `notifications`, `recurring_templates`, `slas`, `tenant_configs`, `tenants`, `ticket_attachments`, `ticket_comments`, `ticket_history`, `tickets`, `user_areas`, `users`

---

### TC-DB-002: Verificar índices críticos

```sql
SELECT indexname, tablename FROM pg_indexes
WHERE schemaname = 'public'
ORDER BY tablename, indexname;
```

**Índices esperados (mínimo):**
- `tickets.tenant_id`
- `tickets.status`
- `tickets.requester_id`
- `tickets.assigned_to`
- `ticket_comments.ticket_id`
- `ticket_history.ticket_id`
- `users.tenant_id`

---

### TC-DB-003: Unicidad del email por tenant

```sql
-- Intentar insertar email duplicado dentro del mismo tenant debe fallar
INSERT INTO users (id, tenant_id, email, full_name, role, is_active, is_archived)
VALUES (gen_random_uuid(), '<tenant_id>', 'admin@smartsecurity.co', 'Dup', 'agent', true, false);
-- Debe lanzar UNIQUE constraint violation
```

---

### TC-DB-004: ticket_number es único por tenant

```sql
-- Verificar que el constraint único aplica en el mismo tenant
SELECT COUNT(*), ticket_number FROM tickets
WHERE tenant_id = '<tenant_id>'
GROUP BY ticket_number HAVING COUNT(*) > 1;
-- Resultado esperado: 0 filas
```

---

### TC-DB-005: Seed genera datos esperados

```sql
SELECT role, COUNT(*) FROM users WHERE tenant_id = '<tenant_id>' GROUP BY role;
-- Esperado: admin=1, supervisor=1, agent=2, requester=2
```

---

## 6. FASE 2 — Tickets CRUD

### TC-TK-001: Crear ticket exitosamente (admin)

**Endpoint:** `POST /api/v1/tickets`
**Auth:** ADMIN

**Request:**
```json
{
  "title": "Falla en acceso remoto VPN",
  "description": "No puedo conectarme desde esta mañana",
  "priority": "high",
  "category_id": "<CAT_INCIDENTE_ID>",
  "area_id": "<AREA_TI_ID>"
}
```

**Resultado esperado:**
- HTTP 201
- `ticket_number` con formato `#TK-XXXX`
- `status` = "open"
- `requester_id` = ID del admin que creó
- `sla_id` no nulo (SLA asignado automáticamente)
- `sla_due_at` no nulo
- `created_at` presente
- `sla_status` = "ok"

---

### TC-TK-002: Crear ticket — requester solo crea para sí mismo

**Auth:** REQUESTER_1

**Request:**
```json
{
  "title": "Necesito acceso al sistema",
  "description": "Requiero permisos de lectura",
  "priority": "low"
}
```

**Resultado esperado:**
- HTTP 201
- `requester_id` = ID de REQUESTER_1 (no puede ser otro)

---

### TC-TK-003: Crear ticket — sin título (validación)

**Auth:** ADMIN

**Request:**
```json
{
  "description": "Sin título",
  "priority": "medium"
}
```

**Resultado esperado:** HTTP 422

---

### TC-TK-004: Crear ticket — título muy corto (< 3 caracteres)

**Request:**
```json
{
  "title": "AB",
  "description": "Descripción",
  "priority": "low"
}
```

**Resultado esperado:** HTTP 422

---

### TC-TK-005: Crear ticket — prioridad inválida

**Request:**
```json
{
  "title": "Ticket con prioridad inválida",
  "description": "Test",
  "priority": "critical"
}
```

**Resultado esperado:** HTTP 422

---

### TC-TK-006: Obtener ticket por ID (admin)

**Precondición:** Tener el `ticket_id` del TC-TK-001

**Request:** `GET /api/v1/tickets/<ticket_id>`
**Auth:** ADMIN

**Resultado esperado:**
- HTTP 200
- Todos los campos de `TicketResponse` presentes
- `requester` object con `id`, `full_name`, `email`
- `sla_status` calculado correctamente

---

### TC-TK-007: Obtener ticket inexistente

**Request:** `GET /api/v1/tickets/00000000-0000-0000-0000-000000000000`
**Auth:** ADMIN

**Resultado esperado:** HTTP 404

---

### TC-TK-008: Listar tickets — respuesta paginada

**Request:** `GET /api/v1/tickets?page=1&size=10`
**Auth:** ADMIN

**Resultado esperado:**
- HTTP 200
- Body: `{ "items": [...], "total": N, "page": 1, "pages": M, "size": 10 }`
- `items` es array
- `total` >= 0

---

### TC-TK-009: Listar tickets — filtro por status

**Request:** `GET /api/v1/tickets?status=open`
**Auth:** ADMIN

**Resultado esperado:**
- HTTP 200
- Todos los items tienen `status` = "open"

---

### TC-TK-010: Listar tickets — filtro por prioridad

**Request:** `GET /api/v1/tickets?priority=high`
**Auth:** ADMIN

**Resultado esperado:** Todos los items tienen `priority` = "high"

---

### TC-TK-011: Listar tickets — filtro por fecha

**Request:** `GET /api/v1/tickets?date_from=2026-01-01&date_to=2026-12-31`
**Auth:** ADMIN

**Resultado esperado:** HTTP 200, tickets dentro del rango de fechas

---

### TC-TK-012: Listar tickets — paginación con size máximo

**Request:** `GET /api/v1/tickets?size=101`
**Auth:** ADMIN

**Resultado esperado:** HTTP 422 o tamaño limitado a 100

---

### TC-TK-013: Actualizar ticket (admin)

**Precondición:** Ticket en estado "open"

**Request:** `PATCH /api/v1/tickets/<ticket_id>`
**Auth:** ADMIN

```json
{
  "title": "Título actualizado",
  "priority": "urgent"
}
```

**Resultado esperado:**
- HTTP 200
- `title` = "Título actualizado"
- `priority` = "urgent"
- `updated_at` > `created_at`

---

### TC-TK-014: Actualizar ticket — requester solo puede editar tickets en estado "open"

**Auth:** REQUESTER_1
**Precondición:** Ticket del REQUESTER_1 en estado "open"

**Request:** `PATCH /api/v1/tickets/<ticket_id>`
```json
{ "title": "Mi actualización" }
```

**Resultado esperado:** HTTP 200

---

### TC-TK-015: Actualizar ticket — requester NO puede editar ticket en estado "in_progress"

**Auth:** REQUESTER_1
**Precondición:** Ticket del REQUESTER_1 en estado "in_progress"

**Resultado esperado:** HTTP 403

---

### TC-TK-016: Eliminar ticket (soft-delete, solo admin)

**Auth:** ADMIN

**Request:** `DELETE /api/v1/tickets/<ticket_id>`

**Resultado esperado:**
- HTTP 204
- En BD: `deleted_at` no es null
- GET del mismo ticket → HTTP 404

---

### TC-TK-017: Eliminar ticket — non-admin recibe 403

**Auth:** SUPERVISOR

**Request:** `DELETE /api/v1/tickets/<ticket_id>`

**Resultado esperado:** HTTP 403

---

### TC-TK-018: ticket_number es secuencial y único

**Acción:** Crear 3 tickets en secuencia rápida

**Resultado esperado:**
- `ticket_number` = `#TK-0001`, `#TK-0002`, `#TK-0003` (o continuación del contador actual)
- No hay duplicados aunque se creen concurrentemente

---

## 7. FASE 2 — Transiciones de Estado

### TC-ST-001: Asignar ticket (supervisor)

**Auth:** SUPERVISOR
**Precondición:** Ticket en estado "open"

**Request:** `POST /api/v1/tickets/<ticket_id>/assign`
```json
{ "agent_id": "<AGENT_1_ID>" }
```

**Resultado esperado:**
- HTTP 200
- `assigned_to` = AGENT_1_ID
- Historial: action = "assigned"

---

### TC-ST-002: Asignar ticket — agente no pertenece al tenant

**Auth:** SUPERVISOR

**Request:** `POST /api/v1/tickets/<ticket_id>/assign`
```json
{ "agent_id": "<UUID_de_otro_tenant>" }
```

**Resultado esperado:** HTTP 404 o 422

---

### TC-ST-003: Asignar ticket — non-supervisor recibe 403

**Auth:** AGENT_1

**Request:** `POST /api/v1/tickets/<ticket_id>/assign`
```json
{ "agent_id": "<AGENT_2_ID>" }
```

**Resultado esperado:** HTTP 403

---

### TC-ST-004: Transición open → in_progress

**Auth:** AGENT_1
**Precondición:** Ticket asignado a AGENT_1, en estado "open"

**Request:** `PATCH /api/v1/tickets/<ticket_id>`
_(o el endpoint específico de cambio de estado si existe)_

**Verificación:**
- `status` = "in_progress"
- `first_response_at` no es null y es aproximadamente `now()`

---

### TC-ST-005: Escalamiento exitoso

**Auth:** SUPERVISOR
**Precondición:** Ticket en estado "open" o "in_progress"

**Request:** `POST /api/v1/tickets/<ticket_id>/escalate`
```json
{
  "reason": "Requiere atención de nivel 2",
  "area_id": "<AREA_RRHH_ID>"
}
```

**Resultado esperado:**
- HTTP 200
- `status` = "escalated"
- `area_id` = AREA_RRHH_ID
- Historial: action = "escalated"

---

### TC-ST-006: Escalamiento — transición inválida desde "resolved"

**Auth:** SUPERVISOR
**Precondición:** Ticket en estado "resolved"

**Request:** `POST /api/v1/tickets/<ticket_id>/escalate`
```json
{ "reason": "Escalamiento tardío" }
```

**Resultado esperado:** HTTP 422 — transición no permitida

---

### TC-ST-007: Resolver ticket

**Auth:** AGENT_1
**Precondición:** Ticket en estado "in_progress"

**Request:** `POST /api/v1/tickets/<ticket_id>/resolve`

**Resultado esperado:**
- HTTP 200
- `status` = "resolved"
- `resolved_at` no es null
- Historial: action = "status_changed" o "resolved"

---

### TC-ST-008: Cerrar ticket

**Auth:** SUPERVISOR
**Precondición:** Ticket en estado "resolved"

**Request:** `POST /api/v1/tickets/<ticket_id>/close`

**Resultado esperado:**
- HTTP 200
- `status` = "closed"
- `closed_at` no es null

---

### TC-ST-009: Cerrar ticket desde estado inválido (ej. "open")

**Auth:** SUPERVISOR
**Precondición:** Ticket en estado "open"

**Request:** `POST /api/v1/tickets/<ticket_id>/close`

**Resultado esperado:** HTTP 422

---

### TC-ST-010: Reabrir ticket resuelto

**Auth:** REQUESTER_1
**Precondición:** Ticket del REQUESTER_1 en estado "resolved"

**Request:** `POST /api/v1/tickets/<ticket_id>/reopen`
```json
{ "reason": "El problema persiste" }
```

**Resultado esperado:**
- HTTP 200
- `status` = "open"
- `resolved_at` = null
- `reopen_count` incrementado en 1
- Historial: action = "reopened"

---

### TC-ST-011: Reabrir ticket cerrado

**Auth:** REQUESTER_1
**Precondición:** Ticket en estado "closed"

**Request:** `POST /api/v1/tickets/<ticket_id>/reopen`
```json
{ "reason": "Necesito que se revise nuevamente" }
```

**Resultado esperado:** HTTP 200, `status` = "open"

---

### TC-ST-012: Reabrir sin reason — debe fallar

**Auth:** REQUESTER_1

**Request:** `POST /api/v1/tickets/<ticket_id>/reopen`
```json
{}
```

**Resultado esperado:** HTTP 422

---

### TC-ST-013: No se puede reabrir ticket en estado "in_progress"

**Auth:** REQUESTER_1
**Precondición:** Ticket en estado "in_progress"

**Request:** `POST /api/v1/tickets/<ticket_id>/reopen`
```json
{ "reason": "Intento de reapertura inválido" }
```

**Resultado esperado:** HTTP 422

---

### TC-ST-014: Ciclo de vida completo (happy path)

**Secuencia:**
1. REQUESTER_1 crea ticket → `status: open`
2. SUPERVISOR asigna a AGENT_1 → `assigned_to: AGENT_1`
3. AGENT_1 mueve a in_progress → `first_response_at` != null
4. AGENT_1 resuelve → `status: resolved`, `resolved_at` != null
5. SUPERVISOR cierra → `status: closed`, `closed_at` != null

**Verificación:** Historial con 5 entradas (created, assigned, status_changed x2, status_changed)

---

## 8. FASE 2 — Comentarios

### TC-CMT-001: Agregar comentario público (requester)

**Auth:** REQUESTER_1
**Precondición:** Ticket del REQUESTER_1

**Request:** `POST /api/v1/tickets/<ticket_id>/comments`
```json
{
  "body": "¿Tienen alguna actualización?",
  "is_internal": false
}
```

**Resultado esperado:**
- HTTP 201
- `is_internal` = false
- `author_id` = REQUESTER_1_ID
- `author` object presente

---

### TC-CMT-002: Requester NO puede crear nota interna

**Auth:** REQUESTER_1

**Request:**
```json
{
  "body": "Nota interna de prueba",
  "is_internal": true
}
```

**Resultado esperado:** HTTP 403

---

### TC-CMT-003: Agent puede crear nota interna

**Auth:** AGENT_1

**Request:**
```json
{
  "body": "Revisando el servidor VPN...",
  "is_internal": true
}
```

**Resultado esperado:**
- HTTP 201
- `is_internal` = true

---

### TC-CMT-004: Listar comentarios — requester solo ve públicos

**Precondición:** Ticket con un comentario público y uno interno

**Auth:** REQUESTER_1
**Request:** `GET /api/v1/tickets/<ticket_id>/comments`

**Resultado esperado:**
- Solo aparece el comentario con `is_internal = false`
- El comentario interno NO aparece

---

### TC-CMT-005: Listar comentarios — agent ve todos

**Auth:** AGENT_1
**Request:** `GET /api/v1/tickets/<ticket_id>/comments`

**Resultado esperado:**
- Aparecen tanto comentarios públicos como internos

---

### TC-CMT-006: Editar comentario dentro de la ventana de 5 minutos

**Auth:** AGENT_1
**Precondición:** Comentario creado hace menos de 5 minutos por AGENT_1

**Request:** `PATCH /api/v1/tickets/<ticket_id>/comments/<comment_id>`
```json
{ "body": "Revisando el servidor VPN (actualizado)" }
```

**Resultado esperado:**
- HTTP 200
- `body` = "Revisando el servidor VPN (actualizado)"

---

### TC-CMT-007: Editar comentario fuera de la ventana de 5 minutos

**Precondición:** Comentario creado hace más de 5 minutos (modificar `created_at` en BD o esperar)

**Request:** `PATCH /api/v1/tickets/<ticket_id>/comments/<comment_id>`
```json
{ "body": "Intento de edición tardía" }
```

**Resultado esperado:** HTTP 403

---

### TC-CMT-008: Editar comentario de otro autor

**Auth:** AGENT_2 (intenta editar comentario de AGENT_1)

**Resultado esperado:** HTTP 403

---

### TC-CMT-009: Listar comentarios ordenados por fecha ascendente

**Precondición:** Ticket con múltiples comentarios

**Resultado esperado:** Orden cronológico ascendente (`created_at`)

---

### TC-CMT-010: Comentario con body vacío debe fallar

**Request:**
```json
{ "body": "" }
```

**Resultado esperado:** HTTP 422

---

## 9. FASE 2 — Historial de Auditoría

### TC-HIST-001: Historial registra creación del ticket

**Request:** `GET /api/v1/tickets/<ticket_id>/history`
**Auth:** ADMIN

**Resultado esperado:**
- Array con al menos 1 elemento
- Primera entrada: `action` = "created"
- `actor_id` = ID del creador
- `new_value` contiene datos del ticket

---

### TC-HIST-002: Historial registra cambio de estado

**Precondición:** Ticket que pasó por al menos un cambio de estado

**Resultado esperado:**
- Entrada con `action` = "status_changed"
- `old_value` contiene estado anterior
- `new_value` contiene estado nuevo

---

### TC-HIST-003: Historial registra asignación

**Resultado esperado:**
- Entrada con `action` = "assigned"
- `new_value` contiene `agent_id`

---

### TC-HIST-004: Historial registra reapertura

**Resultado esperado:**
- Entrada con `action` = "reopened"
- `new_value` contiene `reason`

---

### TC-HIST-005: Historial es inmutable — no hay endpoint de modificación

**Verificar:**
- No existe `PATCH /api/v1/tickets/<ticket_id>/history/<id>`
- No existe `DELETE /api/v1/tickets/<ticket_id>/history/<id>`

---

### TC-HIST-006: Historial ordenado descendente

**Resultado esperado:** Entrada más reciente primero (`created_at` DESC)

---

### TC-HIST-007: Historial registra comentario agregado

**Precondición:** Agregar comentario al ticket

**Resultado esperado:**
- Nueva entrada con `action` = "comment_added"

---

### TC-HIST-008: Historial registra actualización de campos

**Precondición:** Actualizar `title` o `priority` del ticket

**Resultado esperado:**
- Entrada con `action` = "updated"
- `old_value` y `new_value` reflejan el campo cambiado

---

## 10. FASE 2 — Archivos Adjuntos

### TC-ADJ-001: Subir archivo PDF válido

**Endpoint:** `POST /api/v1/tickets/<ticket_id>/attachments`
**Auth:** AGENT_1
**Content-Type:** multipart/form-data

**Archivo:** un PDF de menos de 10MB

**Resultado esperado:**
- HTTP 201
- `filename` = nombre original del archivo
- `mime_type` = "application/pdf"
- `file_size` > 0
- `uploaded_by` = AGENT_1_ID

---

### TC-ADJ-002: Subir imagen JPEG válida

**Archivo:** imagen JPEG

**Resultado esperado:** HTTP 201, `mime_type` = "image/jpeg"

---

### TC-ADJ-003: Subir imagen PNG válida

**Resultado esperado:** HTTP 201, `mime_type` = "image/png"

---

### TC-ADJ-004: Subir imagen WebP válida

**Resultado esperado:** HTTP 201, `mime_type` = "image/webp"

---

### TC-ADJ-005: Rechazar tipo MIME no permitido (ej. .xlsx)

**Archivo:** archivo Excel o .txt

**Resultado esperado:** HTTP 400

---

### TC-ADJ-006: Rechazar archivo mayor a 10MB

**Archivo:** crear un archivo de 11MB

```bash
dd if=/dev/zero bs=1M count=11 | gzip > /tmp/big_file.gz
# O usar un archivo legítimo grande
```

**Resultado esperado:** HTTP 400 o HTTP 422

---

### TC-ADJ-007: Obtener URL firmada de descarga

**Request:** `GET /api/v1/tickets/<ticket_id>/attachments/<attachment_id>/download`
**Auth:** AGENT_1

**Resultado esperado:**
- HTTP 200
- `download_url` presente y no vacío
- La URL contiene un token de firma

---

### TC-ADJ-008: URL firmada expira después de 1 hora

**Precondición:** Obtener URL firmada
**Acción:** Modificar el timestamp del token para que sea de hace más de 1 hora
**Resultado esperado:** HTTP 401 o 403 al intentar usar la URL expirada

---

### TC-ADJ-009: Verificar almacenamiento en disco

**Precondición:** Subir un archivo exitosamente

**Verificación:**
```bash
ls {STORAGE_PATH}/<tenant_id>/<ticket_id>/
# Debe existir el archivo
```

---

### TC-ADJ-010: Subir adjunto a ticket de otro tenant debe fallar

**Auth:** Token de tenant 2
**Request:** `POST /api/v1/tickets/<ticket_id_de_tenant_1>/attachments`

**Resultado esperado:** HTTP 404 (el ticket no es visible para el tenant 2)

---

## 11. FASE 2 — SLA y Horas de Negocio

### TC-SLA-001: SLA asignado automáticamente al crear ticket

**Precondición:** Existe SLA para `priority = "urgent"` (SLA_URGENTE: 1h respuesta, 4h resolución)

**Request:** Crear ticket con `priority = "urgent"`

**Resultado esperado:**
- `sla_id` = ID del SLA_URGENTE
- `sla_due_at` = fecha creación + 4 horas de negocio (resolution_hours)
- `sla_status` = "ok"

---

### TC-SLA-002: SLA específico por categoría tiene precedencia sobre SLA global

**Precondición:** Existe SLA_INCIDENTE_URGENTE (CAT_INCIDENTE + urgent, 0.5h/2h)

**Request:** Crear ticket con `category_id = CAT_INCIDENTE`, `priority = "urgent"`

**Resultado esperado:**
- `sla_id` = ID del SLA_INCIDENTE_URGENTE (no el SLA_URGENTE global)
- `sla_due_at` = ahora + 2 horas de negocio

---

### TC-SLA-003: sla_status = "warning" cuando se supera el 75% del tiempo

**Acción:** Crear ticket y modificar `sla_due_at` en BD para que venza en 30 minutos
(siendo el total de resolución 4 horas = 240 min, el 75% = 180 min han transcurrido)

**Request:** `GET /api/v1/tickets/<ticket_id>`

**Resultado esperado:**
- `sla_status` = "warning"
- `sla_percentage` > 75

---

### TC-SLA-004: sla_status = "breached" cuando se supera el tiempo

**Acción:** Modificar `sla_due_at` en BD a un timestamp pasado

**Request:** `GET /api/v1/tickets/<ticket_id>`

**Resultado esperado:**
- `sla_status` = "breached"
- `sla_percentage` >= 100

---

### TC-SLA-005: sla_status = null cuando ticket no tiene SLA asignado

**Precondición:** Ticket sin `sla_id` (creado sin categoría ni prioridad con SLA configurado)

**Resultado esperado:** `sla_status` = null, `sla_percentage` = null

---

### TC-SLA-006: Cálculo de horas de negocio — mismo día

**Test unitario:** `calculate_due_date(lunes_10h, 2, "America/Bogota")`
**Resultado esperado:** lunes 12:00 (misma zona horaria)

---

### TC-SLA-007: Cálculo de horas de negocio — spans día

**Test unitario:** `calculate_due_date(lunes_17h, 2, "America/Bogota")`
**Resultado esperado:** martes 09:00 (1h restante del lunes: 17-18, 1h del martes: 08-09)

---

### TC-SLA-008: Cálculo de horas de negocio — inicio en fin de semana

**Test unitario:** `calculate_due_date(sabado_10h, 4, "America/Bogota")`
**Resultado esperado:** lunes 12:00

---

### TC-SLA-009: Cálculo de horas de negocio — viernes fin del día

**Test unitario:** `calculate_due_date(viernes_16h, 8, "America/Bogota")`
**Resultado esperado:** lunes 14:00

---

### TC-SLA-010: Resultado de calculate_due_date siempre en UTC

**Verificación:** El timestamp retornado tiene `tzinfo = UTC`

---

### TC-SLA-011: SLA marcado como breached por tarea Celery

**Precondición:** Ticket con `sla_due_at` en el pasado y `sla_breached = false`

**Acción:** Ejecutar `check_sla_breaches` manualmente:
```bash
docker compose exec celery_worker celery -A app.tasks.celery_app call app.tasks.sla_tasks.check_sla_breaches
```

**Resultado esperado:**
- `sla_breached = true` en BD para el ticket
- Respuesta de la tarea: `{ "status": "ok", "breaches_processed": N }`

---

### TC-SLA-012: Tarea de warnings detecta tickets próximos a vencer

**Precondición:** Ticket con `sla_due_at` en los próximos 90 minutos

**Acción:** Ejecutar `check_sla_warnings`

**Resultado esperado:**
- Respuesta: `{ "status": "ok", "warnings_sent": N }`
- N >= 1

---

## 12. FASE 2 — Visibilidad y Control de Acceso (RBAC)

### TC-RBAC-001: Requester solo ve sus propios tickets

**Precondición:**
- REQUESTER_1 tiene 2 tickets
- REQUESTER_2 tiene 1 ticket

**Auth:** REQUESTER_1
**Request:** `GET /api/v1/tickets`

**Resultado esperado:**
- `total` = 2 (solo los de REQUESTER_1)
- Ningún ticket de REQUESTER_2 aparece

---

### TC-RBAC-002: Requester no puede ver ticket de otro requester por ID

**Auth:** REQUESTER_1
**Request:** `GET /api/v1/tickets/<ticket_de_REQUESTER_2>`

**Resultado esperado:** HTTP 404

---

### TC-RBAC-003: Agent ve tickets de sus áreas

**Precondición:** Ticket creado en AREA_TI (área de AGENT_1)

**Auth:** AGENT_1
**Request:** `GET /api/v1/tickets`

**Resultado esperado:** El ticket de AREA_TI aparece en la lista

---

### TC-RBAC-004: Agent ve tickets asignados directamente aunque no sea de su área

**Precondición:** Ticket en AREA_RRHH asignado directamente a AGENT_1

**Auth:** AGENT_1
**Request:** `GET /api/v1/tickets`

**Resultado esperado:** El ticket aparece a pesar de no ser del área de AGENT_1

---

### TC-RBAC-005: Agent NO ve tickets de otras áreas que no son las suyas y que no le están asignados

**Precondición:** Ticket en AREA_RRHH sin asignar

**Auth:** AGENT_1 (solo tiene AREA_TI)
**Request:** `GET /api/v1/tickets/<ticket_area_rrhh>`

**Resultado esperado:** HTTP 404

---

### TC-RBAC-006: Supervisor ve todos los tickets del tenant

**Auth:** SUPERVISOR
**Request:** `GET /api/v1/tickets`

**Resultado esperado:**
- `total` = total de tickets del tenant (de todos los usuarios)

---

### TC-RBAC-007: Admin ve todos los tickets del tenant

**Auth:** ADMIN
**Request:** `GET /api/v1/tickets`

**Resultado esperado:** Igual que SUPERVISOR — todos los tickets

---

### TC-RBAC-008: Requester no puede asignar ticket

**Auth:** REQUESTER_1
**Request:** `POST /api/v1/tickets/<ticket_id>/assign`
```json
{ "agent_id": "<AGENT_1_ID>" }
```

**Resultado esperado:** HTTP 403

---

### TC-RBAC-009: Agent no puede eliminar ticket

**Auth:** AGENT_1
**Request:** `DELETE /api/v1/tickets/<ticket_id>`

**Resultado esperado:** HTTP 403

---

### TC-RBAC-010: Usuarios de diferentes tenants no comparten tickets

**Precondición:** Tenant 2 con su propio usuario y tickets

**Auth:** Usuario del Tenant 2
**Request:** `GET /api/v1/tickets/<ticket_id_de_tenant_1>`

**Resultado esperado:** HTTP 404

---

## 13. FASE 2 — Auto-enrutamiento de Tickets

### TC-ROUTE-001: Categoría con área por defecto auto-asigna área

**Request:** Crear ticket con `category_id = CAT_INCIDENTE` (tiene `default_area_id = AREA_TI`)
**Sin especificar `area_id` en el request**

**Resultado esperado:**
- `area_id` = AREA_TI_ID (asignado automáticamente)

---

### TC-ROUTE-002: Categoría con agente por defecto auto-asigna agente

**Request:** Crear ticket con `category_id = CAT_SOLICITUD` (tiene `default_agent_id = AGENT_2`)
**Sin especificar `assigned_to`**

**Resultado esperado:**
- `assigned_to` = AGENT_2_ID
- `area_id` = AREA_RRHH_ID

---

### TC-ROUTE-003: Categoría sin ruta no asigna área ni agente

**Request:** Crear ticket con `category_id = CAT_LIBRE`

**Resultado esperado:**
- `area_id` = null (o el valor enviado en el request)
- `assigned_to` = null

---

### TC-ROUTE-004: area_id manual en el request prevalece sobre el de la categoría

**Request:** Crear ticket con `category_id = CAT_INCIDENTE`, `area_id = AREA_RRHH_ID`

**Resultado esperado:** `area_id` = AREA_RRHH_ID (el especificado manualmente)

---

## 14. Validaciones de Entrada (todos los endpoints)

### TC-VAL-001: Content-Type incorrecto en POST

**Request:** `POST /api/v1/tickets` con `Content-Type: text/plain`

**Resultado esperado:** HTTP 422 o 415

---

### TC-VAL-002: JSON malformado

**Request:** `POST /api/v1/tickets` con body `{invalid json}`

**Resultado esperado:** HTTP 422

---

### TC-VAL-003: UUID inválido en path parameter

**Request:** `GET /api/v1/tickets/not-a-uuid`

**Resultado esperado:** HTTP 422

---

### TC-VAL-004: Parámetro de paginación negativo

**Request:** `GET /api/v1/tickets?page=-1`

**Resultado esperado:** HTTP 422 o página 1

---

### TC-VAL-005: Formato de fecha inválido en filtro

**Request:** `GET /api/v1/tickets?date_from=2026/13/45`

**Resultado esperado:** HTTP 422

---

## 15. Seguridad y Multi-tenant

### TC-SEC-001: El JWT no puede ser manipulado

**Acción:** Tomar un JWT válido y modificar el `role` de "requester" a "admin" (sin conocer SECRET_KEY)

**Resultado esperado:** HTTP 401 (firma inválida)

---

### TC-SEC-002: Access token no puede usarse como refresh token

**Acción:** Usar el `access_token` en el endpoint de refresh

**Resultado esperado:** HTTP 401 (tipo incorrecto)

---

### TC-SEC-003: Ruta /health no requiere autenticación

**Request:** `GET /health` (sin Authorization header)

**Resultado esperado:** HTTP 200

---

### TC-SEC-004: Rutas de auth no requieren token

**Request:** `POST /api/v1/auth/login` (sin Authorization header)

**Resultado esperado:** HTTP 200 o 401 (según credenciales), nunca un error de autenticación previo

---

### TC-SEC-005: Documentación solo disponible en development

**Precondición:** `ENVIRONMENT = "production"`

**Request:** `GET /docs`

**Resultado esperado:** HTTP 404

---

### TC-SEC-006: Aislamiento de datos multi-tenant

**Precondición:** Dos tenants con datos distintos

**Verificación SQL:**
```sql
SELECT COUNT(*) FROM tickets WHERE tenant_id != '<mi_tenant_id>';
-- Al hacer queries con el JWT del tenant 1, nunca deben aparecer tickets del tenant 2
```

---

### TC-SEC-007: File path traversal en nombres de archivos

**Acción:** Intentar subir archivo con nombre `../../../../etc/passwd`

**Resultado esperado:**
- HTTP 400 o el archivo se guarda con el UUID como nombre (sin path traversal)
- El path en BD no debe contener `..`

---

### TC-SEC-008: Headers de seguridad en respuestas

**Verificar que las respuestas incluyan:**
- `X-Content-Type-Options: nosniff` (o similar)
- No incluya información de versiones de servidor

---

## 16. Tareas Celery (SLA)

### TC-CELERY-001: check_sla_warnings se puede ejecutar sin errores

```bash
docker compose exec celery_worker celery -A app.tasks.celery_app call app.tasks.sla_tasks.check_sla_warnings
```

**Resultado esperado:**
- Retorna `{ "status": "ok", "warnings_sent": N }`
- Sin excepciones en logs

---

### TC-CELERY-002: check_sla_breaches actualiza sla_breached en BD

**Precondición:** Ticket con `sla_due_at` < `now()` y `sla_breached = false`

**Resultado esperado:**
- Después de ejecutar la tarea: `sla_breached = true`

---

### TC-CELERY-003: Celery conecta a Redis correctamente

```bash
docker compose exec celery_worker celery -A app.tasks.celery_app inspect ping
```

**Resultado esperado:** Respuesta del worker

---

### TC-CELERY-004: La tarea maneja reintentos ante fallas

**Verificar configuración en código:**
- `max_retries = 3`
- `default_retry_delay = 60`

---

## 17. Casos de Error Esperados

### Tabla de referencia rápida

| Código | Escenario | Endpoint de ejemplo |
|---|---|---|
| 200 | Operación GET exitosa | `GET /api/v1/tickets/{id}` |
| 201 | Recurso creado | `POST /api/v1/tickets` |
| 204 | Eliminación exitosa | `DELETE /api/v1/tickets/{id}` |
| 400 | Archivo inválido (MIME/tamaño) | `POST /api/v1/tickets/{id}/attachments` |
| 401 | Token ausente o inválido | Cualquier endpoint protegido |
| 401 | Contraseña incorrecta | `POST /api/v1/auth/login` |
| 403 | Permiso insuficiente (RBAC) | Requester intenta eliminar |
| 403 | Edición de comentario fuera de ventana | `PATCH /comments/{id}` |
| 404 | Recurso no encontrado | `GET /api/v1/tickets/uuid-inexistente` |
| 404 | Ticket de otro tenant | Aislamiento multi-tenant |
| 422 | Validación de campos (Pydantic) | Falta title, enum inválido |
| 422 | Transición de estado inválida | Cerrar ticket "open" |

---

## 18. Matriz de Cobertura por Rol

| Acción | requester | agent | supervisor | admin |
|---|---|---|---|---|
| Crear ticket | ✅ (propio) | ✅ | ✅ | ✅ |
| Ver ticket propio | ✅ | ✅ | ✅ | ✅ |
| Ver ticket de otro requester | ❌ 404 | ❌ 404 (fuera de área) | ✅ | ✅ |
| Editar ticket (open) | ✅ | ✅ | ✅ | ✅ |
| Editar ticket (in_progress) | ❌ 403 | ✅ | ✅ | ✅ |
| Eliminar ticket | ❌ 403 | ❌ 403 | ❌ 403 | ✅ |
| Asignar ticket | ❌ 403 | ❌ 403 | ✅ | ✅ |
| Escalar ticket | ❌ 403 | ❌ 403 | ✅ | ✅ |
| Resolver ticket | ❌ | ✅ | ✅ | ✅ |
| Cerrar ticket | ❌ | ✅ | ✅ | ✅ |
| Reabrir ticket | ✅ (propio) | ✅ | ✅ | ✅ |
| Comentario público | ✅ | ✅ | ✅ | ✅ |
| Comentario interno | ❌ 403 | ✅ | ✅ | ✅ |
| Ver comentario interno | ❌ | ✅ | ✅ | ✅ |
| Subir adjunto | ✅ | ✅ | ✅ | ✅ |
| Ver historial | ✅ (propio) | ✅ | ✅ | ✅ |
| Ver todos los tickets | ❌ | ❌ (solo áreas) | ✅ | ✅ |

---

## 19. FASE 4 — Gestión de Usuarios

### TC-USR-001: Listar usuarios (admin)

**Endpoint:** `GET /api/v1/users`
**Auth:** ADMIN

**Resultado esperado:**
- HTTP 200
- Lista paginada con todos los usuarios activos no archivados del tenant
- Estructura: `{ items, total, page, pages, size }`

---

### TC-USR-002: Listar usuarios — agente solo ve activos no archivados

**Auth:** AGENT_1
**Request:** `GET /api/v1/users`

**Resultado esperado:**
- HTTP 200
- Solo usuarios con `is_active=true` e `is_archived=false`
- No aparecen usuarios archivados aunque existan

---

### TC-USR-003: Crear usuario (admin)

**Auth:** ADMIN
**Request:** `POST /api/v1/users`
```json
{
  "email": "nuevo@smartsecurity.co",
  "full_name": "Usuario Nuevo",
  "role": "agent",
  "password": "Pass1234!",
  "area_ids": ["<AREA_TI_ID>"],
  "primary_area_id": "<AREA_TI_ID>"
}
```

**Resultado esperado:**
- HTTP 201
- `email` = "nuevo@smartsecurity.co"
- `role` = "agent"
- `is_active` = true, `is_archived` = false

**Verificación adicional:**
- El usuario puede hacer login inmediatamente con la contraseña provista
- `user_areas` contiene el registro con `is_primary = true`

---

### TC-USR-004: Crear usuario — email duplicado en el tenant

**Auth:** ADMIN
**Request:** Intentar crear con `email = "admin@smartsecurity.co"` (ya existe)

**Resultado esperado:** HTTP 409

---

### TC-USR-005: Crear usuario — non-admin recibe 403

**Auth:** SUPERVISOR
**Request:** `POST /api/v1/users` con payload válido

**Resultado esperado:** HTTP 403

---

### TC-USR-006: Obtener usuario por ID

**Auth:** ADMIN
**Request:** `GET /api/v1/users/<AGENT_1_ID>`

**Resultado esperado:**
- HTTP 200
- Campos correctos del usuario

---

### TC-USR-007: Obtener usuario de otro tenant

**Auth:** Admin del tenant 2
**Request:** `GET /api/v1/users/<AGENT_1_ID_de_tenant_1>`

**Resultado esperado:** HTTP 404

---

### TC-USR-008: Actualizar rol de usuario (admin)

**Auth:** ADMIN
**Request:** `PATCH /api/v1/users/<AGENT_1_ID>`
```json
{ "role": "supervisor" }
```

**Resultado esperado:**
- HTTP 200
- `role` = "supervisor"

---

### TC-USR-009: Actualizar áreas del usuario

**Auth:** ADMIN
**Request:** `PATCH /api/v1/users/<AGENT_1_ID>`
```json
{
  "area_ids": ["<AREA_TI_ID>", "<AREA_RRHH_ID>"],
  "primary_area_id": "<AREA_TI_ID>"
}
```

**Resultado esperado:**
- HTTP 200
- En BD: 2 registros en `user_areas`, AREA_TI con `is_primary=true`

---

### TC-USR-010: Archivar usuario (admin)

**Auth:** ADMIN
**Request:** `POST /api/v1/users/<AGENT_2_ID>/archive`

**Resultado esperado:**
- HTTP 200
- `is_archived` = true, `is_active` = false

**Verificaciones adicionales:**
1. El usuario archivado no puede hacer login → HTTP 403
2. En BD: tickets abiertos que tenía asignados → `assigned_to = null`
3. En Redis: tokens `refresh:<AGENT_2_ID>:*` eliminados

---

### TC-USR-011: Archivar usuario ya archivado

**Auth:** ADMIN
**Precondición:** Usuario ya archivado

**Request:** `POST /api/v1/users/<user_id>/archive`

**Resultado esperado:** HTTP 409

---

### TC-USR-012: Listar usuarios — filtro por rol

**Auth:** ADMIN
**Request:** `GET /api/v1/users?role=agent`

**Resultado esperado:** Solo usuarios con `role = "agent"`

---

## 20. FASE 4 — Gestión de Áreas

### TC-AREA-001: Listar áreas del tenant

**Auth:** AGENT_1
**Request:** `GET /api/v1/areas`

**Resultado esperado:**
- HTTP 200
- Lista de áreas activas del tenant
- Campos: `id`, `name`, `description`, `manager_id`, `is_active`

---

### TC-AREA-002: Listar áreas — incluir inactivas (admin)

**Auth:** ADMIN
**Request:** `GET /api/v1/areas?active_only=false`

**Resultado esperado:** Incluye áreas con `is_active = false`

---

### TC-AREA-003: Crear área (admin)

**Auth:** ADMIN
**Request:** `POST /api/v1/areas`
```json
{
  "name": "Contabilidad",
  "description": "Área financiera",
  "manager_id": "<SUPERVISOR_ID>"
}
```

**Resultado esperado:**
- HTTP 201
- `name` = "Contabilidad"
- `is_active` = true

---

### TC-AREA-004: Crear área — nombre duplicado

**Auth:** ADMIN
**Request:** Crear área con `name = "Tecnología"` (ya existe)

**Resultado esperado:** HTTP 409

---

### TC-AREA-005: Crear área — non-admin recibe 403

**Auth:** SUPERVISOR
**Resultado esperado:** HTTP 403

---

### TC-AREA-006: Actualizar área

**Auth:** ADMIN
**Request:** `PATCH /api/v1/areas/<AREA_TI_ID>`
```json
{ "description": "Soporte tecnológico actualizado" }
```

**Resultado esperado:** HTTP 200, `description` actualizado

---

### TC-AREA-007: Desactivar área

**Auth:** ADMIN
**Request:** `PATCH /api/v1/areas/<AREA_TI_ID>`
```json
{ "is_active": false }
```

**Resultado esperado:**
- HTTP 200
- `is_active` = false
- El área no aparece en `GET /areas` con `active_only=true`

---

### TC-AREA-008: Listar miembros del área

**Auth:** ADMIN
**Request:** `GET /api/v1/areas/<AREA_TI_ID>/members`

**Resultado esperado:**
- HTTP 200
- Lista con AGENT_1 (`is_primary = true`)

---

### TC-AREA-009: Agregar miembro al área

**Auth:** ADMIN
**Request:** `POST /api/v1/areas/<AREA_RRHH_ID>/members`
```json
{ "user_id": "<AGENT_1_ID>", "is_primary": false }
```

**Resultado esperado:**
- HTTP 201
- AGENT_1 ahora aparece como miembro de AREA_RRHH
- `is_primary` = false (sigue siendo AREA_TI su área principal)

---

### TC-AREA-010: Agregar miembro como primario — reemplaza primario anterior

**Precondición:** AGENT_1 tiene `is_primary=true` en AREA_TI

**Auth:** ADMIN
**Request:** `POST /api/v1/areas/<AREA_RRHH_ID>/members`
```json
{ "user_id": "<AGENT_1_ID>", "is_primary": true }
```

**Resultado esperado:**
- HTTP 201
- En BD: AGENT_1 en AREA_TI tiene `is_primary = false`
- AGENT_1 en AREA_RRHH tiene `is_primary = true`

---

### TC-AREA-011: Agregar miembro duplicado

**Precondición:** AGENT_1 ya es miembro de AREA_TI

**Request:** `POST /api/v1/areas/<AREA_TI_ID>/members`
```json
{ "user_id": "<AGENT_1_ID>" }
```

**Resultado esperado:** HTTP 409

---

### TC-AREA-012: Eliminar miembro del área

**Auth:** ADMIN
**Request:** `DELETE /api/v1/areas/<AREA_TI_ID>/members/<AGENT_1_ID>`

**Resultado esperado:**
- HTTP 204
- AGENT_1 ya no aparece en los miembros de AREA_TI

---

### TC-AREA-013: Eliminar miembro que no pertenece al área

**Request:** `DELETE /api/v1/areas/<AREA_TI_ID>/members/<AGENT_2_ID>` (AGENT_2 es de AREA_RRHH)

**Resultado esperado:** HTTP 404

---

## 21. FASE 4 — Panel de Administración (Categorías, SLAs, Config)

### TC-ADMIN-001: Obtener configuración del tenant

**Auth:** ADMIN
**Request:** `GET /api/v1/admin/config`

**Resultado esperado:**
- HTTP 200
- Campos: `timezone`, `working_hours_start`, `working_hours_end`, `working_days`, `auto_close_days`, `urgency_abuse_threshold`, `weekly_report_enabled`, etc.

---

### TC-ADMIN-002: Actualizar configuración del tenant

**Auth:** ADMIN
**Request:** `PATCH /api/v1/admin/config`
```json
{
  "auto_close_days": 5,
  "urgency_abuse_threshold": 40,
  "weekly_report_enabled": true,
  "weekly_report_recipients": ["gerencia@smartsecurity.co"]
}
```

**Resultado esperado:**
- HTTP 200
- Campos actualizados
- Caché Redis `tenant_config:<tenant_id>` invalidado

---

### TC-ADMIN-003: Actualizar config — color inválido

**Request:**
```json
{ "primary_color": "azul" }
```

**Resultado esperado:** HTTP 422

---

### TC-ADMIN-004: Configuración — non-admin recibe 403

**Auth:** SUPERVISOR
**Request:** `GET /api/v1/admin/config`

**Resultado esperado:** HTTP 403

---

### TC-ADMIN-005: Listar categorías

**Auth:** ADMIN
**Request:** `GET /api/v1/admin/categories`

**Resultado esperado:**
- HTTP 200
- Lista con CAT_INCIDENTE, CAT_SOLICITUD, CAT_LIBRE

---

### TC-ADMIN-006: Crear categoría con enrutamiento automático

**Auth:** ADMIN
**Request:** `POST /api/v1/admin/categories`
```json
{
  "name": "Infraestructura",
  "description": "Solicitudes de infraestructura",
  "default_area_id": "<AREA_TI_ID>",
  "default_agent_id": "<AGENT_1_ID>"
}
```

**Resultado esperado:**
- HTTP 201
- Verificar que al crear un ticket con esta categoría → área y agente se asignan automáticamente

---

### TC-ADMIN-007: Crear categoría — nombre duplicado

**Request:** Crear con `name = "Incidente TI"` (ya existe)

**Resultado esperado:** HTTP 409

---

### TC-ADMIN-008: Actualizar categoría — desactivar

**Auth:** ADMIN
**Request:** `PATCH /api/v1/admin/categories/<CAT_LIBRE_ID>`
```json
{ "is_active": false }
```

**Resultado esperado:**
- HTTP 200
- `is_active` = false
- Categoría no aparece en listados con `active_only=true`

---

### TC-ADMIN-009: Listar SLAs

**Auth:** ADMIN
**Request:** `GET /api/v1/admin/slas`

**Resultado esperado:** Lista con SLA_URGENTE, SLA_ALTO, SLA_MEDIO, SLA_BAJO, SLA_INCIDENTE_URGENTE

---

### TC-ADMIN-010: Crear SLA global (sin categoría ni prioridad)

**Auth:** ADMIN
**Request:** `POST /api/v1/admin/slas`
```json
{
  "response_hours": 24,
  "resolution_hours": 72
}
```

**Resultado esperado:**
- HTTP 201
- `category_id` = null, `priority` = null

---

### TC-ADMIN-011: Crear SLA — combinación duplicada

**Request:** Intentar crear `category_id=null + priority="urgent"` cuando SLA_URGENTE ya existe

**Resultado esperado:** HTTP 409

---

### TC-ADMIN-012: Actualizar SLA — desactivar

**Auth:** ADMIN
**Request:** `PATCH /api/v1/admin/slas/<SLA_BAJO_ID>`
```json
{ "is_active": false }
```

**Resultado esperado:** HTTP 200, `is_active` = false

---

### TC-ADMIN-013: Actualizar SLA — modificar horas

**Auth:** ADMIN
**Request:** `PATCH /api/v1/admin/slas/<SLA_MEDIO_ID>`
```json
{ "resolution_hours": 20 }
```

**Resultado esperado:**
- HTTP 200
- `resolution_hours` = 20
- Tickets nuevos con `priority=medium` heredan el nuevo SLA (tickets existentes no se ven afectados)

---

## 22. FASE 4 — Tickets Recurrentes

### TC-REC-001: Crear plantilla recurrente mensual (día 28)

**Auth:** ADMIN
**Request:** `POST /api/v1/admin/recurring`
```json
{
  "title": "Pago de nómina",
  "description": "Procesar pago de nómina mensual",
  "category_id": "<CAT_SOLICITUD_ID>",
  "area_id": "<AREA_RRHH_ID>",
  "priority": "high",
  "assigned_to": "<AGENT_2_ID>",
  "recurrence_type": "day_of_month",
  "recurrence_value": 28,
  "if_holiday_action": "previous_business_day"
}
```

**Resultado esperado:**
- HTTP 201
- `recurrence_type` = "day_of_month"
- `recurrence_value` = 28
- `next_run_at` calculado correctamente (próximo día 28, o día hábil anterior si cae en fin de semana)
- `is_active` = true

---

### TC-REC-002: Crear plantilla semanal (lunes)

**Auth:** ADMIN
**Request:** `POST /api/v1/admin/recurring`
```json
{
  "title": "Revisión semanal de incidentes",
  "priority": "medium",
  "recurrence_type": "weekly",
  "recurrence_day": 0,
  "if_holiday_action": "next_business_day"
}
```

**Resultado esperado:**
- HTTP 201
- `next_run_at` apunta al próximo lunes a las 08:00 (hora local del tenant)

---

### TC-REC-003: Crear plantilla diaria

**Request:**
```json
{
  "title": "Verificación diaria de sistemas",
  "priority": "low",
  "recurrence_type": "daily",
  "if_holiday_action": "same_day"
}
```

**Resultado esperado:**
- HTTP 201
- `next_run_at` = mañana a las 08:00 hora local

---

### TC-REC-004: next_run_at se calcula al crear — día 28 que cae en domingo

**Precondición:** Forzar `now()` a un jueves, con el próximo día 28 siendo domingo

**Resultado esperado:**
- `if_holiday_action = "previous_business_day"` → `next_run_at` apunta al viernes 26

---

### TC-REC-005: Listar plantillas recurrentes

**Auth:** ADMIN
**Request:** `GET /api/v1/admin/recurring`

**Resultado esperado:** Lista con todas las plantillas del tenant

---

### TC-REC-006: Listar solo plantillas activas

**Request:** `GET /api/v1/admin/recurring?active_only=true`

**Resultado esperado:** Solo plantillas con `is_active = true`

---

### TC-REC-007: Actualizar plantilla — cambiar recurrencia recalcula next_run_at

**Auth:** ADMIN
**Request:** `PATCH /api/v1/admin/recurring/<template_id>`
```json
{
  "recurrence_type": "weekly",
  "recurrence_day": 2
}
```

**Resultado esperado:**
- HTTP 200
- `next_run_at` recalculado para el próximo miércoles

---

### TC-REC-008: Desactivar plantilla recurrente

**Auth:** ADMIN
**Request:** `DELETE /api/v1/admin/recurring/<template_id>`

**Resultado esperado:**
- HTTP 204
- `is_active` = false en BD
- Tickets ya creados por la plantilla NO son eliminados

---

### TC-REC-009: Non-admin no puede gestionar plantillas

**Auth:** SUPERVISOR
**Request:** `POST /api/v1/admin/recurring` con payload válido

**Resultado esperado:** HTTP 403

---

### TC-REC-010: Celery crea ticket desde plantilla vencida

**Precondición:** Plantilla activa con `next_run_at` en el pasado

**Acción:**
```bash
docker compose exec celery_worker celery -A app.tasks.celery_app call app.tasks.recurring_tasks.process_recurring_tickets
```

**Resultado esperado:**
- Respuesta: `{ "status": "ok", "tickets_created": 1 }`
- En BD: nuevo ticket con `is_recurring_instance = true`, `recurring_template_id` = ID de la plantilla
- Plantilla actualizada: `last_run_at` = now, `next_run_at` = nueva fecha calculada

---

### TC-REC-011: Ticket recurrente hereda configuración de la plantilla

**Verificar en el ticket creado por la tarea:**
- `title` = título de la plantilla
- `category_id` = category de la plantilla
- `area_id` = área de la plantilla
- `assigned_to` = agente de la plantilla
- `priority` = prioridad de la plantilla
- `sla_due_at` calculado correctamente si hay SLA configurado

---

### TC-REC-012: Plantilla inactiva NO genera tickets

**Precondición:** Plantilla con `is_active = false` y `next_run_at` en el pasado

**Acción:** Ejecutar `process_recurring_tickets`

**Resultado esperado:** No se crea ningún ticket para esa plantilla

---

### TC-REC-013: calculate_next_run — día 28 en domingo con previous_business_day

**Test unitario:**
```python
from app.services.recurring_service import calculate_next_run

# Crear template mock con recurrence_type="day_of_month", recurrence_value=28,
# if_holiday_action="previous_business_day"
# Pasar after=fecha donde el próximo día 28 es domingo
result = calculate_next_run(template, after=..., timezone_str="America/Bogota")
# Resultado esperado: viernes 26 a las 08:00 UTC equivalente
```

---

### TC-REC-014: calculate_next_run — retorna datetime UTC-aware

**Verificar:** `result.tzinfo` no es `None` y está en UTC

---

## 23. FASE 4 — Dashboard y Reportes

### TC-DASH-001: Summary — métricas generales

**Auth:** ADMIN
**Request:** `GET /api/v1/dashboard/summary`

**Resultado esperado:**
- HTTP 200
- Campos presentes: `total_open`, `total_in_progress`, `total_pending`, `total_escalated`, `total_resolved_today`, `total_closed_today`, `avg_resolution_hours`, `sla_compliance_pct`, `new_today`
- Todos los valores son numéricos (o null para promedios)

---

### TC-DASH-002: Summary — filtro de período

**Request:** `GET /api/v1/dashboard/summary?days=7`

**Resultado esperado:** HTTP 200, `avg_resolution_hours` y `sla_compliance_pct` calculados sobre los últimos 7 días

---

### TC-DASH-003: Tickets por área

**Auth:** SUPERVISOR
**Request:** `GET /api/v1/dashboard/tickets-by-area`

**Resultado esperado:**
- HTTP 200
- Lista con AREA_TI y AREA_RRHH
- Cada item tiene: `area_id`, `area_name`, `total`, `open`, `in_progress`, `resolved`
- `total = open + in_progress + resolved` (aproximadamente)

---

### TC-DASH-004: Tickets por estado

**Auth:** ADMIN
**Request:** `GET /api/v1/dashboard/tickets-by-status`

**Resultado esperado:**
- HTTP 200
- Lista con todos los estados presentes en BD
- `percentage` para cada estado, suma ≈ 100%

---

### TC-DASH-005: SLA compliance — solo supervisors/admins

**Auth:** SUPERVISOR
**Request:** `GET /api/v1/dashboard/sla-compliance`

**Resultado esperado:**
- HTTP 200
- `total_with_sla` >= 0
- `compliance_pct` entre 0 y 100
- `by_priority` lista con desglose por prioridad

---

### TC-DASH-006: SLA compliance — requester recibe 403

**Auth:** REQUESTER_1
**Request:** `GET /api/v1/dashboard/sla-compliance`

**Resultado esperado:** HTTP 403

---

### TC-DASH-007: Rendimiento de agentes

**Auth:** ADMIN
**Request:** `GET /api/v1/dashboard/agent-performance`

**Resultado esperado:**
- HTTP 200
- Lista con métricas por agente: `agent_id`, `agent_name`, `assigned_total`, `resolved_total`, `avg_resolution_hours`, `sla_compliance_pct`

---

### TC-DASH-008: Rendimiento de agentes — agent recibe 403

**Auth:** AGENT_1
**Request:** `GET /api/v1/dashboard/agent-performance`

**Resultado esperado:** HTTP 403

---

### TC-DASH-009: Reporte de abuso de urgencia — usuario con permiso especial

**Precondición:** `tenant_config.urgency_report_visible_to` = SUPERVISOR_ID

**Auth:** SUPERVISOR
**Request:** `GET /api/v1/dashboard/urgency-abuse`

**Resultado esperado:**
- HTTP 200
- Lista con usuarios que han creado tickets, incluyendo `urgent_pct` y `trend`

---

### TC-DASH-010: Reporte de abuso de urgencia — usuario sin permiso recibe 403

**Auth:** AGENT_1
**Request:** `GET /api/v1/dashboard/urgency-abuse`

**Resultado esperado:** HTTP 403

---

### TC-DASH-011: Reporte de abuso — admin siempre tiene acceso

**Auth:** ADMIN (aunque no sea el `urgency_report_visible_to`)

**Request:** `GET /api/v1/dashboard/urgency-abuse`

**Resultado esperado:** HTTP 200

---

### TC-DASH-012: Reporte de abuso — tendencia correcta

**Precondición:**
- REQUESTER_1 creó 10 tickets en el período actual, 7 urgentes (70%)
- En el período anterior: 10 tickets, 4 urgentes (40%)

**Resultado esperado:**
- `urgent_pct` = 70.0
- `prev_period_pct` = 40.0
- `trend` = "worsened"

---

### TC-DASH-013: Reporte de abuso — tendencia mejorada

**Precondición:**
- REQUESTER_2: período actual 30% urgentes, período anterior 60%

**Resultado esperado:** `trend` = "improved"

---

### TC-DASH-014: Reporte semanal — endpoint de datos

**Auth:** SUPERVISOR
**Request:** `GET /api/v1/dashboard/weekly-report`

**Resultado esperado:**
- HTTP 200
- `period_start` y `period_end` correctos (últimos 7 días)
- `summary` presente
- `tickets_by_area` lista
- `tickets_by_status` lista
- `top_agents` lista (máximo 5)

---

### TC-DASH-015: Reporte semanal — requester recibe 403

**Auth:** REQUESTER_1
**Request:** `GET /api/v1/dashboard/weekly-report`

**Resultado esperado:** HTTP 403

---

### TC-DASH-016: Summary — aislamiento multi-tenant

**Precondición:** Tenant 2 tiene 5 tickets propios

**Auth:** Admin del tenant 1
**Request:** `GET /api/v1/dashboard/summary`

**Resultado esperado:**
- El `new_today` NO incluye tickets del tenant 2
- Los conteos son exclusivos del tenant 1

---

## 24. FASE 4 — Tareas Celery (Recurrentes y Reportes)

### TC-CELERY-F4-001: process_recurring_tickets se puede ejecutar sin errores

```bash
docker compose exec celery_worker celery -A app.tasks.celery_app call app.tasks.recurring_tasks.process_recurring_tickets
```

**Resultado esperado:**
- Retorna `{ "status": "ok", "tickets_created": N }`
- Sin excepciones en logs del worker

---

### TC-CELERY-F4-002: send_weekly_report omite tenant sin config

**Precondición:** Tenant sin `TenantConfig` creada

**Acción:**
```bash
docker compose exec celery_worker celery -A app.tasks.celery_app call app.tasks.report_tasks.send_weekly_report --args='["<tenant_id>"]'
```

**Resultado esperado:** `{ "status": "skipped", "reason": "report disabled or no config" }`

---

### TC-CELERY-F4-003: send_weekly_report omite cuando no hay destinatarios

**Precondición:** `tenant_config.weekly_report_recipients = []`

**Resultado esperado:** `{ "status": "skipped", "reason": "no recipients configured" }`

---

### TC-CELERY-F4-004: send_weekly_report encola correos cuando hay destinatarios

**Precondición:** `weekly_report_enabled = true`, `weekly_report_recipients = ["gerencia@smartsecurity.co"]`

**Acción:** Ejecutar tarea manualmente

**Resultado esperado:** `{ "status": "ok", "recipients": 1 }`

---

### TC-CELERY-F4-005: process_recurring_tickets es idempotente en el mismo día

**Precondición:** Plantilla diaria cuyo `next_run_at` es en el pasado; ejecutar la tarea dos veces

**Resultado esperado:**
- Primera ejecución: 1 ticket creado, `next_run_at` actualizado a mañana
- Segunda ejecución: 0 tickets creados (plantilla ya no está vencida)

---

### TC-CELERY-F4-006: Celery Beat tiene todas las tareas programadas

```bash
docker compose exec celery_worker celery -A app.tasks.celery_app beat --dry-run --loglevel=info 2>&1 | head -20
```

**Verificar que aparecen:**
- `check-sla-warnings` (cada 30 min)
- `check-sla-breaches` (cada 15 min)
- `process-recurring-tickets` (cada hora)

---

## 25. Matriz de Cobertura por Rol — Fase 4

| Acción | requester | agent | supervisor | admin |
|---|---|---|---|---|
| Listar usuarios | ✅ (activos) | ✅ (activos) | ✅ (todos) | ✅ (todos) |
| Crear usuario | ❌ 403 | ❌ 403 | ❌ 403 | ✅ |
| Archivar usuario | ❌ 403 | ❌ 403 | ❌ 403 | ✅ |
| Listar áreas | ✅ | ✅ | ✅ | ✅ |
| Crear área | ❌ 403 | ❌ 403 | ❌ 403 | ✅ |
| Gestionar miembros | ❌ 403 | ❌ 403 | ✅ | ✅ |
| Ver config tenant | ❌ 403 | ❌ 403 | ❌ 403 | ✅ |
| Editar config tenant | ❌ 403 | ❌ 403 | ❌ 403 | ✅ |
| Gestionar categorías | ❌ 403 | ❌ 403 | ❌ 403 | ✅ |
| Gestionar SLAs | ❌ 403 | ❌ 403 | ❌ 403 | ✅ |
| Crear plantilla recurrente | ❌ 403 | ❌ 403 | ❌ 403 | ✅ |
| Ver dashboard summary | ✅ | ✅ | ✅ | ✅ |
| Ver tickets por área | ✅ | ✅ | ✅ | ✅ |
| Ver SLA compliance | ❌ 403 | ❌ 403 | ✅ | ✅ |
| Ver agent performance | ❌ 403 | ❌ 403 | ✅ | ✅ |
| Ver urgency abuse | ❌ 403 | ❌ 403 | ✅ (si configurado) | ✅ |
| Ver reporte semanal | ❌ 403 | ❌ 403 | ✅ | ✅ |

---

---

## 26. FASE 5 — Autenticación Frontend

> **Entorno:** Next.js corriendo en `http://localhost:3000`. El backend debe estar activo en `http://localhost:8000`.

### TC-FE-AUTH-001: Página de login carga correctamente

**URL:** `http://localhost:3000/auth/login` (o ruta de login configurada en NextAuth)

**Verificación visual:**
- Formulario con campos Email y Contraseña
- Botón "Iniciar sesión"
- Logo / marca de Smart Security visible
- Sin errores en consola del navegador

---

### TC-FE-AUTH-002: Login con credenciales válidas

**Acción:** Ingresar `email = admin@smartsecurity.co` + contraseña correcta y presionar "Iniciar sesión"

**Resultado esperado:**
- Redirección automática al dashboard (`/`)
- Cookie de sesión o token almacenado (según implementación NextAuth)
- Sidebar con navegación visible
- Nombre del usuario visible en el header/avatar

---

### TC-FE-AUTH-003: Login con credenciales inválidas

**Acción:** Ingresar email válido + contraseña incorrecta

**Resultado esperado:**
- Mensaje de error visible: "Credenciales inválidas" (o similar)
- El usuario permanece en la página de login
- Sin redirección

---

### TC-FE-AUTH-004: Campos requeridos vacíos

**Acción:** Hacer submit sin llenar ningún campo

**Resultado esperado:**
- Mensajes de validación en los campos (requerido)
- Sin llamada al backend (validación del lado cliente)

---

### TC-FE-AUTH-005: Sesión persistente (refresco de página)

**Precondición:** Usuario con sesión activa

**Acción:** Presionar F5 / recargar la página en `/`

**Resultado esperado:**
- El usuario sigue autenticado (no redirige a login)
- Los datos del dashboard se recargan correctamente

---

### TC-FE-AUTH-006: Logout

**Acción:** Hacer click en el botón/menú de logout

**Resultado esperado:**
- Sesión terminada
- Redirección a `/auth/login`
- Al intentar acceder a `/` directamente → redirige a login

---

### TC-FE-AUTH-007: Protección de rutas — usuario no autenticado

**Acción:** Navegar a `http://localhost:3000/` sin sesión activa

**Resultado esperado:**
- Redirección automática a la página de login
- Sin parpadeo de contenido protegido (flash)

---

### TC-FE-AUTH-008: Control de acceso por rol — rutas admin

**Precondición:** Usuario con rol `agent` (sin permisos admin)

**Acción:** Navegar a `http://localhost:3000/admin/users`

**Resultado esperado:**
- Redirección o mensaje de "Acceso denegado"
- No se muestra contenido del panel admin

---

## 27. FASE 5 — Dashboard Principal

### TC-FE-DASH-001: Tarjetas de resumen cargan correctamente

**URL:** `http://localhost:3000/` (autenticado como admin o supervisor)

**Verificación:**
- 4+ tarjetas de métricas visibles: Tickets Abiertos, En Progreso, Resueltos Hoy, Nuevos Hoy
- Los números son consistentes con `GET /api/v1/dashboard/summary`
- Animación de skeleton mientras carga (si aplica)

---

### TC-FE-DASH-002: Gráficos de distribución cargan

**Verificación:**
- Gráfico de tickets por estado (dona o barras)
- Gráfico de tickets por área (si aplica)
- Los valores del gráfico coinciden con `GET /api/v1/dashboard/tickets-by-status` y `tickets-by-area`
- Sin errores de Recharts en consola

---

### TC-FE-DASH-003: Cambio de rango de fechas (parámetro `days`)

**Acción:** Si existe selector de período (7, 30, 90 días), cambiarlo

**Resultado esperado:**
- Las métricas se actualizan automáticamente sin recargar la página
- La consulta al backend incluye el nuevo parámetro `?days=N`

---

### TC-FE-DASH-004: Dashboard — requester no ve métricas admin

**Precondición:** Usuario con rol `requester`

**Verificación:**
- Las secciones de SLA Compliance, Agent Performance y Urgency Abuse no son visibles
- No se realizan llamadas a esos endpoints (verificar en DevTools → Network)

---

### TC-FE-DASH-005: Sidebar de navegación — visibilidad por rol

**Requester:** Ve: Mis Tickets, (sin panel Admin)
**Agent:** Ve: Tickets, Dashboard básico
**Supervisor/Admin:** Ve: Tickets, Dashboard completo, Reportes, Admin panel

---

## 28. FASE 5 — Gestión de Tickets (Lista y Filtros)

### TC-FE-TICK-001: Lista de tickets carga correctamente

**URL:** `/tickets` (autenticado)

**Verificación:**
- Tabla con columnas: ID, Título, Estado, Prioridad, Área, Asignado a, Fecha
- Paginación visible (si hay más de `size` tickets)
- Skeleton de carga mientras llegan los datos

---

### TC-FE-TICK-002: Filtro por estado

**Acción:** Seleccionar filtro "Estado: En progreso"

**Resultado esperado:**
- La tabla muestra solo tickets con `status = "in_progress"`
- La URL se actualiza con el parámetro de filtro (o estado local)
- El conteo total cambia

---

### TC-FE-TICK-003: Filtro por prioridad

**Acción:** Seleccionar filtro "Prioridad: Urgente"

**Resultado esperado:**
- Solo tickets con `priority = "urgent"` visibles
- Badge de prioridad rojo en cada fila

---

### TC-FE-TICK-004: Filtro por búsqueda de texto

**Acción:** Escribir "nómina" en el campo de búsqueda

**Resultado esperado:**
- Lista filtrada a tickets cuyo título o descripción contenga "nómina"
- Debounce de al menos 300ms antes de llamar al backend

---

### TC-FE-TICK-005: Paginación

**Precondición:** Más de 20 tickets existentes

**Acción:** Hacer click en "Página 2"

**Resultado esperado:**
- Se muestran los 20 tickets siguientes
- Número de página activo actualizado en la UI
- Se llama a `GET /api/v1/tickets?page=2`

---

### TC-FE-TICK-006: Columna de estado — badges de color

**Verificación visual:**
- `open` → badge gris/azul
- `in_progress` → badge amarillo/naranja
- `escalated` → badge rojo
- `resolved` → badge verde
- `closed` → badge oscuro/neutro

---

### TC-FE-TICK-007: Requester solo ve sus propios tickets

**Precondición:** Autenticado como REQUESTER_1

**Verificación:**
- La lista no contiene tickets creados por REQUESTER_2
- No se muestran tickets de otras áreas sin relación con el usuario

---

## 29. FASE 5 — Detalle de Ticket

### TC-FE-DETAIL-001: Página de detalle carga todos los datos

**URL:** `/tickets/<ticket_id>`

**Verificación:**
- Título, descripción, estado, prioridad, área, agente asignado
- Timeline/historial de acciones (creación, cambios de estado)
- Sección de comentarios

---

### TC-FE-DETAIL-002: Agregar comentario público

**Acción:** Escribir un comentario en el campo de texto y hacer submit

**Resultado esperado:**
- `POST /api/v1/tickets/<id>/comments` llamado con `is_internal = false`
- Comentario aparece inmediatamente en la lista (optimistic update o refetch)
- Campo de texto se limpia

---

### TC-FE-DETAIL-003: Agregar comentario interno (solo agent/supervisor/admin)

**Precondición:** Usuario con rol `agent`

**Acción:** Marcar checkbox "Interno" y escribir comentario

**Resultado esperado:**
- Comentario enviado con `is_internal = true`
- Aparece con indicador visual diferente (fondo distinto, etiqueta "Interno")
- **Para requester:** El checkbox de "Interno" no es visible

---

### TC-FE-DETAIL-004: Adjuntos — subir archivo

**Acción:** Usar el selector de archivos para subir una imagen PNG < 10MB

**Resultado esperado:**
- `POST /api/v1/tickets/<id>/attachments` con el archivo
- El adjunto aparece en la lista con nombre, tamaño e ícono de tipo
- Botón de descarga disponible

---

### TC-FE-DETAIL-005: Adjuntos — subir archivo rechazado (> 10MB)

**Acción:** Seleccionar archivo de 15MB

**Resultado esperado:**
- Error visible: "El archivo excede el tamaño máximo (10MB)"
- Sin llamada al backend

---

### TC-FE-DETAIL-006: Cambiar estado del ticket (agente)

**Precondición:** Ticket en estado `open`, autenticado como AGENT_1

**Acción:** Click en botón "Iniciar / Tomar ticket"

**Resultado esperado:**
- `PATCH /api/v1/tickets/<id>` o endpoint de transición llamado
- Estado se actualiza a `in_progress` en la UI sin recargar
- Botón cambia a opciones relevantes ("Resolver", "Escalar")

---

### TC-FE-DETAIL-007: Historial inmutable — no hay botón de eliminar

**Verificación:**
- Los registros del historial/auditoría no tienen botón de edición o eliminación
- Son de solo lectura

---

### TC-FE-DETAIL-008: Ticket de otro tenant → 404

**Acción:** Navegar a `/tickets/<uuid_de_otro_tenant>` (autenticado en tenant 1)

**Resultado esperado:**
- Página 404 o mensaje "Ticket no encontrado"
- Sin datos del otro tenant expuestos

---

## 30. FASE 5 — Crear Ticket

### TC-FE-NEW-001: Formulario de creación carga

**URL:** `/tickets/new`

**Verificación:**
- Campos: Título (requerido), Descripción (requerido), Prioridad, Categoría, Área
- Botón "Crear ticket"
- Dropdown de categoría cargado desde `GET /api/v1/admin/categories`

---

### TC-FE-NEW-002: Crear ticket exitoso

**Acción:** Completar todos los campos requeridos y submit

**Resultado esperado:**
- `POST /api/v1/tickets` exitoso
- Redirección automática a `/tickets/<nuevo_id>`
- El ticket aparece con estado `open`

---

### TC-FE-NEW-003: Validación de campos requeridos

**Acción:** Submit sin llenar Título

**Resultado esperado:**
- Mensaje de error bajo el campo: "El título es requerido"
- Sin llamada al backend

---

### TC-FE-NEW-004: Auto-enrutamiento visible en UI

**Acción:** Seleccionar categoría "Incidente TI" (que tiene `default_area_id` configurada)

**Resultado esperado:**
- El campo Área se pre-rellena automáticamente con "TI"
- El usuario puede sobreescribir el área si lo desea

---

### TC-FE-NEW-005: Adjuntar archivo al crear ticket

**Acción:** Usar el campo de archivo durante la creación

**Resultado esperado:**
- El ticket se crea primero, luego se sube el adjunto
- El adjunto aparece en el detalle del ticket recién creado

---

## 31. FASE 5 — Panel Admin — Usuarios

> Todos los casos requieren autenticación como ADMIN.

### TC-FE-USR-001: Lista de usuarios carga correctamente

**URL:** `/admin/users`

**Verificación:**
- Tabla con columnas: Nombre, Rol (badge de color), Estado, Último acceso, Acciones
- Skeleton mientras carga
- Botón "Nuevo usuario" visible

---

### TC-FE-USR-002: Modal de creación abre y cierra

**Acción:** Click en "Nuevo usuario"

**Verificación:**
- Modal abre con overlay oscuro
- Campos: Nombre completo, Email, Rol (select), Contraseña
- Botón X cierra el modal sin enviar datos

---

### TC-FE-USR-003: Crear usuario — validación de email inválido

**Acción:** Ingresar "no-es-email" en el campo Email y submit

**Resultado esperado:**
- Error de validación Zod: "Email inválido"
- Sin llamada al backend

---

### TC-FE-USR-004: Crear usuario exitoso

**Acción:** Completar formulario con datos válidos y submit

**Resultado esperado:**
- Modal se cierra
- La tabla se refresca con el nuevo usuario (`useQueryClient.invalidateQueries`)
- Sin errores en consola

---

### TC-FE-USR-005: Editar usuario — modal con datos pre-cargados

**Acción:** Click en ícono Edit2 de un usuario existente

**Verificación:**
- Modal "Editar usuario" abre con datos actuales del usuario
- Campo `full_name` pre-llenado
- Rol seleccionado correctamente
- Checkbox `is_active` en estado correcto

---

### TC-FE-USR-006: Archivar usuario — diálogo de confirmación

**Acción:** Click en ícono Archive de un usuario activo

**Verificación:**
- Diálogo de confirmación aparece con el nombre del usuario
- Botón "Archivar" en rojo
- Botón "Cancelar" cierra el diálogo sin archivar
- Al confirmar: `POST /api/v1/users/<id>/archive` enviado
- Usuario desaparece de la lista activa (o aparece con badge "Archivado")

---

### TC-FE-USR-007: Badge de rol con color correcto

**Verificación visual:**
- `admin` → fondo morado
- `supervisor` → fondo azul
- `agent` → fondo teal
- `requester` → fondo gris

---

### TC-FE-USR-008: Spinner/loading durante mutación

**Acción:** Click en "Crear usuario" con servidor lento (throttle en DevTools)

**Verificación:**
- Botón muestra "Creando..." y está deshabilitado mientras la petición está en vuelo
- Vuelve a "Crear usuario" cuando completa

---

## 32. FASE 5 — Panel Admin — Áreas

### TC-FE-AREA-001: Lista de áreas con expansión de miembros

**URL:** `/admin/areas`

**Verificación:**
- Cada área muestra nombre, descripción, badge activo/inactivo
- Ícono chevron (▶) para expandir/colapsar miembros
- Al expandir: se llama `GET /api/v1/areas/<id>/members` y se muestran los miembros

---

### TC-FE-AREA-002: Panel de miembros — datos correctos

**Acción:** Expandir área con miembros conocidos

**Verificación:**
- Nombre, email de cada miembro
- Badge "Principal" para el miembro con `is_primary = true`

---

### TC-FE-AREA-003: Crear área exitosa

**Acción:** Click en "Nueva área", completar nombre y submit

**Resultado esperado:**
- `POST /api/v1/areas` llamado
- Modal cierra, nueva área aparece en la lista

---

### TC-FE-AREA-004: Crear área — nombre vacío

**Acción:** Submit con nombre vacío

**Resultado esperado:**
- Error de validación Zod: "El nombre es requerido"

---

### TC-FE-AREA-005: Editar área — datos pre-cargados

**Acción:** Click en Edit2 de un área

**Verificación:**
- Modal abre con nombre, descripción y `manager_id` del área seleccionada

---

### TC-FE-AREA-006: Área inactiva muestra badge correcto

**Precondición:** Área con `is_active = false`

**Verificación:**
- Badge gris con texto "Inactiva"
- Área activa muestra badge verde con "Activa"

---

## 33. FASE 5 — Panel Admin — Categorías

### TC-FE-CAT-001: Lista de categorías carga

**URL:** `/admin/categories`

**Verificación:**
- Tabla con columnas: Nombre/Descripción, Aprobación, Estado, Acciones
- Categorías del seed visibles

---

### TC-FE-CAT-002: Toggle de estado (Activa/Inactiva)

**Acción:** Click en el badge de estado de una categoría activa

**Resultado esperado:**
- `PATCH /api/v1/admin/categories/<id>` con `{ "is_active": false }`
- Badge cambia a "Inactiva" sin recargar la página completa

---

### TC-FE-CAT-003: Crear categoría con "Requiere aprobación"

**Acción:** Marcar checkbox "Requiere aprobación" y crear

**Verificación:**
- En la tabla: columna Aprobación muestra "Requiere aprobación" en ámbar
- `POST /api/v1/admin/categories` enviado con `requires_approval: true`

---

### TC-FE-CAT-004: Editar categoría — datos pre-cargados correctamente

**Acción:** Click en Edit2 de una categoría con `requires_approval = true`

**Verificación:**
- Checkbox "Requiere aprobación" aparece marcado en el modal
- Campos de UUID pre-llenados (si tienen valores)

---

## 34. FASE 5 — Panel Admin — SLAs

### TC-FE-SLA-001: Lista de SLAs carga

**URL:** `/admin/slas`

**Verificación:**
- Tabla con columnas: Prioridad, Respuesta, Resolución, Estado, Acciones
- Badges de prioridad con colores correctos (rojo para urgente, naranja para high, etc.)
- SLA sin prioridad muestra "Sin prioridad" en gris

---

### TC-FE-SLA-002: Crear SLA — validación de horas

**Acción:** Ingresar `response_hours = 0` y submit

**Resultado esperado:**
- Error Zod: "Debe ser mayor a 0"

---

### TC-FE-SLA-003: Crear SLA exitoso

**Acción:** Ingresar `response_hours = 4`, `resolution_hours = 24`, prioridad "Alta"

**Resultado esperado:**
- `POST /api/v1/admin/slas` llamado
- Nuevo SLA en la tabla con badge naranja "Alta"

---

### TC-FE-SLA-004: Editar SLA — campo `is_active` visible

**Verificación:**
- El modal de edición muestra checkbox "SLA activo"
- El modal de creación NO muestra el checkbox (siempre activo al crear)

---

### TC-FE-SLA-005: Eliminar SLA — diálogo de confirmación

**Acción:** Click en ícono Trash2

**Verificación:**
- Diálogo: "¿Estás seguro de que deseas eliminar este SLA? Esta acción no se puede deshacer."
- Botón "Eliminar" en rojo, "Cancelar" en gris
- Al confirmar: `DELETE /api/v1/admin/slas/<id>` llamado
- SLA desaparece de la tabla

---

## 35. FASE 5 — Panel Admin — Plantillas Recurrentes

### TC-FE-REC-001: Lista de plantillas carga

**URL:** `/admin/recurring`

**Verificación:**
- Tabla con columnas: Título, Recurrencia, Prioridad, Próxima ejecución, Estado, Acciones
- Fechas de `next_run_at` formateadas en español (ej. "28 mar 2026 08:00")
- Plantillas inactivas con badge gris

---

### TC-FE-REC-002: Crear plantilla con tipo de recurrencia "Día del mes"

**Acción:** Seleccionar tipo "Día del mes", valor 15, "Si es festivo: Siguiente día hábil"

**Resultado esperado:**
- `POST /api/v1/admin/recurring` con `recurrence_type = "day_of_month"`, `recurrence_value = 15`
- `next_run_at` calculado por el backend y visible en la tabla

---

### TC-FE-REC-003: Toggle de estado de plantilla

**Acción:** Click en badge "Activa" de una plantilla

**Resultado esperado:**
- `PATCH /api/v1/admin/recurring/<id>` con `{ "is_active": false }`
- Badge cambia a "Inactiva"

---

### TC-FE-REC-004: Modal con scroll para formularios largos

**Verificación:**
- El modal de creación/edición tiene `max-h-[90vh] overflow-y-auto`
- En pantallas pequeñas, el formulario es scrolleable dentro del modal

---

### TC-FE-REC-005: Editar plantilla — datos pre-cargados

**Acción:** Click en Edit2 de una plantilla existente

**Verificación:**
- Todos los campos del formulario reflejan los valores actuales de la plantilla
- Selector de tipo de recurrencia en la posición correcta

---

## 36. FASE 5 — Panel Admin — Configuración

### TC-FE-CFG-001: Formulario de configuración carga con datos actuales

**URL:** `/admin/config`

**Verificación:**
- Color picker y campo de texto con el `primary_color` actual
- `auto_close_days` y `urgency_abuse_threshold` pre-llenados
- Zona horaria correcta
- Horario de inicio/fin del tenant
- Días laborales resaltados con botones activos
- Checkbox de reporte semanal en estado correcto

---

### TC-FE-CFG-002: Color picker sincronizado con input de texto

**Acción:** Cambiar el color usando el input de tipo color (rueda de colores)

**Resultado esperado:**
- El campo de texto hexadecimal se actualiza automáticamente
- Al cambiar el hexadecimal manualmente, el color picker se sincroniza

---

### TC-FE-CFG-003: Toggle de días laborales

**Acción:** Click en "Sáb" para activarlo como día laboral

**Resultado esperado:**
- Botón "Sáb" cambia a fondo `#1a2c4e` (activo)
- El valor en el formulario incluye el índice 6 en el array `working_days`
- El botón "Guardar cambios" se activa (formulario `isDirty = true`)

---

### TC-FE-CFG-004: Botón "Guardar cambios" deshabilitado sin cambios

**Verificación:**
- Al cargar la página sin modificar nada: botón "Guardar cambios" está deshabilitado (`isDirty = false`)
- Al modificar cualquier campo: se habilita

---

### TC-FE-CFG-005: Guardar configuración exitoso

**Acción:** Modificar `auto_close_days` y click en "Guardar cambios"

**Resultado esperado:**
- `PATCH /api/v1/admin/config` llamado con los valores actualizados
- Mensaje de confirmación: "Configuración guardada correctamente."
- El cache de React Query se invalida (`admin-config`)

---

### TC-FE-CFG-006: Configuración — campo color con formato inválido

**Acción:** Borrar el hexadecimal y escribir "azul" y submit

**Resultado esperado:**
- Error Zod: "Color inválido"
- Sin llamada al backend

---

### TC-FE-CFG-007: Reporte semanal — selector de día condicionado

**Acción:** Desmarcar checkbox "Activar reporte semanal automático"

**Resultado esperado:**
- El selector de "Día de envío" desaparece de la UI
- Al marcar nuevamente: el selector reaparece

---

## 37. FASE 5 — Reportes

### TC-FE-REP-001: Página de reportes carga (supervisor/admin)

**URL:** `/reports`

**Verificación:**
- Métricas de SLA Compliance visibles: porcentaje general y desglose por prioridad
- Tabla/gráfico de Agent Performance con columnas: Agente, Asignados, Resueltos, Tiempo promedio
- Sin errores en consola

---

### TC-FE-REP-002: Datos de SLA Compliance son correctos

**Verificación:**
- El porcentaje mostrado coincide con `GET /api/v1/dashboard/sla-compliance`
- El desglose por prioridad coincide con `by_priority` del response

---

### TC-FE-REP-003: Agente sin tickets resueltos aparece correctamente

**Verificación:**
- Agente con `resolved_total = 0` aparece en la tabla con "—" o "0"
- Sin errores de división por cero en frontend

---

### TC-FE-REP-004: Página bloqueada para agentes/requesters

**Precondición:** Autenticado como AGENT_1

**Acción:** Navegar a `/reports`

**Resultado esperado:**
- Redirección a página de inicio o mensaje de "Acceso denegado"
- No se llaman los endpoints de SLA o agent performance

---

### TC-FE-REP-005: Reporte semanal — sección de datos de la semana

**Verificación:**
- Si la página incluye una sección de reporte semanal, los datos provienen de `GET /api/v1/dashboard/weekly-report`
- Las fechas del período (`period_start`, `period_end`) se muestran formateadas

---

## 38. FASE 5 — Notificaciones y WebSocket

### TC-FE-NOTIF-001: Bell de notificaciones visible en el header

**Verificación:**
- Ícono de campana visible en el header para todos los roles autenticados
- Si hay notificaciones no leídas: badge con contador
- Si no hay: sin badge o badge con "0"

---

### TC-FE-NOTIF-002: Click en bell abre lista de notificaciones

**Acción:** Click en el ícono de campana

**Verificación:**
- Dropdown o panel con notificaciones recientes
- `GET /api/v1/notifications` llamado
- Cada notificación muestra: mensaje, fecha relativa (ej. "hace 5 min")

---

### TC-FE-NOTIF-003: Marcar notificación como leída

**Acción:** Click en una notificación no leída

**Resultado esperado:**
- `PATCH /api/v1/notifications/<id>` llamado
- Notificación pierde resaltado de "no leída"
- El contador en la campana disminuye

---

### TC-FE-NOTIF-004: "Marcar todas como leídas"

**Acción:** Click en botón "Marcar todo como leído"

**Resultado esperado:**
- `POST /api/v1/notifications/read-all` llamado
- Todas las notificaciones pierden el estado "no leída"
- Badge del counter desaparece o muestra "0"

---

### TC-FE-NOTIF-005: WebSocket — recibir notificación en tiempo real

**Precondición:** Dos pestañas del navegador abiertas con el mismo usuario (o dos usuarios distintos)

**Acción:** Desde el backend (o segunda pestaña), crear un ticket asignado al usuario

**Resultado esperado:**
- En la pestaña del usuario asignado: el contador de notificaciones aumenta sin recargar
- La notificación aparece en el panel de notificaciones automáticamente

---

### TC-FE-NOTIF-006: WebSocket — reconexión automática ante desconexión

**Acción:** Desconectar brevemente la red del navegador (DevTools → Offline) y reconectar

**Resultado esperado:**
- El WebSocket se reconecta automáticamente
- Sin errores permanentes en consola
- Las notificaciones siguen llegando tras la reconexión

---

## 39. Matriz de Cobertura — Fase 5

| Pantalla / Funcionalidad | requester | agent | supervisor | admin |
|---|---|---|---|---|
| Login | ✅ | ✅ | ✅ | ✅ |
| Dashboard (cards resumen) | ✅ (básico) | ✅ (básico) | ✅ (completo) | ✅ (completo) |
| Dashboard (SLA/Agentes) | ❌ oculto | ❌ oculto | ✅ | ✅ |
| Lista de tickets (propios) | ✅ | ✅ | ✅ (todos) | ✅ (todos) |
| Filtros de tickets | ✅ | ✅ | ✅ | ✅ |
| Detalle de ticket | ✅ (propio) | ✅ | ✅ | ✅ |
| Comentario público | ✅ | ✅ | ✅ | ✅ |
| Comentario interno | ❌ oculto | ✅ | ✅ | ✅ |
| Subir adjunto | ✅ | ✅ | ✅ | ✅ |
| Crear ticket | ✅ | ✅ | ✅ | ✅ |
| Cambiar estado del ticket | ❌ | ✅ | ✅ | ✅ |
| Reportes (página /reports) | ❌ bloqueado | ❌ bloqueado | ✅ | ✅ |
| Admin — Usuarios | ❌ | ❌ | ❌ | ✅ |
| Admin — Áreas | ❌ | ❌ | ✅ (ver) | ✅ |
| Admin — Categorías | ❌ | ❌ | ❌ | ✅ |
| Admin — SLAs | ❌ | ❌ | ❌ | ✅ |
| Admin — Recurrentes | ❌ | ❌ | ❌ | ✅ |
| Admin — Configuración | ❌ | ❌ | ❌ | ✅ |
| Bell de notificaciones | ✅ | ✅ | ✅ | ✅ |
| WebSocket (tiempo real) | ✅ | ✅ | ✅ | ✅ |

### Criterios de aceptación para Fase 5

Para considerar la Fase 5 como **APROBADA**, se requiere:

| Criterio | Umbral |
|---|---|
| Login / Logout funcional | 100% |
| Protección de rutas por autenticación | 100% |
| Control de acceso por rol en UI | 100% (sin contenido admin visible para roles menores) |
| Dashboard carga métricas reales del backend | 100% |
| Lista de tickets — filtros operativos | ≥ 95% |
| Detalle de ticket — comentarios y adjuntos | 100% |
| Crear ticket con auto-enrutamiento UI | 100% |
| CRUD usuarios en frontend (crear, editar, archivar) | 100% |
| CRUD áreas con panel de miembros | 100% |
| CRUD categorías con toggle de estado | 100% |
| CRUD SLAs con confirmación de eliminación | 100% |
| CRUD plantillas recurrentes | 100% |
| Configuración de tenant — color picker + días laborales | 100% |
| Página de reportes — SLA y agentes | 100% |
| Bell de notificaciones — marcar leídas | 100% |
| WebSocket — notificación en tiempo real | ≥ 90% (tolerando latencia de red) |
| Sin errores de consola en flujos principales | 100% |

---

---

## 40. FASE 6 — Script CLI de Onboarding

> **Entorno:** El contenedor `backend` está corriendo con acceso a la base de datos. Todos los comandos se ejecutan dentro del contenedor o con acceso directo a Python + DB.

### TC-ONB-001: Crear tenant con plantilla por defecto

**Comando:**
```bash
docker exec -it aplicativotickets-backend-1 bash
python -m scripts.create_tenant \
  --name "Empresa Demo S.A.S" \
  --slug "empresa-demo" \
  --subdomain "tickets.empresademo.com" \
  --admin-email "admin@empresademo.com" \
  --admin-name "Juan García" \
  --auth-method local
```

**Resultado esperado:**
- Salida en consola con `Tenant creado exitosamente: Empresa Demo S.A.S`
- Se muestra email y contraseña generada (con advertencia de guardar)
- Sin errores ni excepciones en el output

**Verificación en BD:**
```sql
SELECT id, slug, name FROM tenants WHERE slug = 'empresa-demo';
SELECT * FROM tenant_configs WHERE tenant_id = '<id>';
SELECT email, role FROM users WHERE tenant_id = '<id>';
SELECT name FROM areas WHERE tenant_id = '<id>';
SELECT name FROM categories WHERE tenant_id = '<id>';
SELECT priority, response_hours, resolution_hours FROM slas WHERE tenant_id = '<id>';
```

---

### TC-ONB-002: Verificar datos provisionados por la plantilla por defecto

**Precondición:** Tenant creado con `TC-ONB-001`

**Verificación SQL:**
```sql
-- Debe haber exactamente 5 áreas
SELECT COUNT(*) FROM areas WHERE tenant_id = '<id>';  -- esperado: 5

-- Debe haber exactamente 7 categorías
SELECT COUNT(*) FROM categories WHERE tenant_id = '<id>';  -- esperado: 7

-- Debe haber exactamente 4 SLAs
SELECT COUNT(*) FROM slas WHERE tenant_id = '<id>';  -- esperado: 4

-- Admin debe tener role = 'admin'
SELECT role FROM users WHERE tenant_id = '<id>' AND email = 'admin@empresademo.com';
```

**Verificación de SLAs:**
| Prioridad | Respuesta esperada | Resolución esperada |
|---|---|---|
| urgent | 1h | 4h |
| high | 4h | 8h |
| medium | 8h | 24h |
| low | 24h | 72h |

---

### TC-ONB-003: Slug duplicado es rechazado

**Precondición:** Ya existe un tenant con `slug = 'empresa-demo'`

**Comando:**
```bash
python -m scripts.create_tenant \
  --name "Otro Nombre" \
  --slug "empresa-demo" \
  --subdomain "tickets.otro.com" \
  --admin-email "admin@otro.com"
```

**Resultado esperado:**
- El script falla con un error de integridad de BD (slug duplicado)
- Sin commit parcial (la transacción revierte completamente)
- No se crea ningún registro en BD

---

### TC-ONB-004: Contraseña generada automáticamente cumple política de seguridad

**Acción:** Crear tenant sin `--admin-password`

**Verificación:**
- La contraseña mostrada en consola tiene al menos 12 caracteres
- Contiene al menos: 1 mayúscula, 1 minúscula, 1 dígito, 1 símbolo (`!@#$%`)
- El admin puede hacer login inmediatamente con esa contraseña

---

### TC-ONB-005: Contraseña manual se respeta

**Comando:** Usar `--admin-password "MiPass123!"`

**Verificación:**
- El admin puede hacer login con exactamente esa contraseña
- El script muestra "Contraseña: (la que indicaste)" (no la revela)

---

### TC-ONB-006: Tenant creado con auth_method=azure

**Comando:** Usar `--auth-method azure`

**Verificación SQL:**
```sql
SELECT auth_method FROM tenant_configs WHERE tenant_id = '<id>';
-- esperado: 'azure'
```

---

### TC-ONB-007: Correo de bienvenida con `--send-welcome`

**Comando:** Usar `--send-welcome` con SMTP configurado

**Resultado esperado:**
- El script muestra "Correo de bienvenida enviado a admin@..."
- El correo recibido contiene: nombre del tenant, credenciales y URL de login

**Sin SMTP configurado:**
- El script muestra "ADVERTENCIA: No se pudo enviar el correo de bienvenida: ..."
- El tenant sigue creándose correctamente (el correo es best-effort)

---

### TC-ONB-008: Plantilla personalizada vía `--template`

**Precondición:** Crear `scripts/templates/custom.yaml` con 2 áreas y 3 categorías

**Comando:**
```bash
python -m scripts.create_tenant \
  --name "Cliente Custom" \
  --slug "cliente-custom" \
  --subdomain "tickets.custom.com" \
  --admin-email "admin@custom.com" \
  --template scripts/templates/custom.yaml
```

**Resultado esperado:**
- Se crean 2 áreas (las del YAML personalizado)
- Se crean 3 categorías (las del YAML personalizado)
- La plantilla por defecto NO se usa

---

### TC-ONB-009: Plantilla con ruta inválida es rechazada

**Comando:** Usar `--template /ruta/que/no/existe.yaml`

**Resultado esperado:**
- El script sale con error: `Error: No se encontró la plantilla en /ruta/que/no/existe.yaml`
- Exit code != 0
- Sin registro en BD

---

### TC-ONB-010: Color primario personalizado

**Comando:** Usar `--primary-color "#FF5722"`

**Verificación SQL:**
```sql
SELECT primary_color FROM tenant_configs WHERE tenant_id = '<id>';
-- esperado: '#FF5722'
```

---

## 41. FASE 6 — API Superadmin (POST /superadmin/tenants)

> **Entorno:** Backend corriendo. Variable de entorno `SUPERADMIN_API_KEY=dev-superadmin-key-change-in-production` configurada.

### TC-SAPI-001: Crear tenant exitoso vía API

**Request:**
```http
POST /api/v1/superadmin/tenants
Content-Type: application/json
X-API-Key: dev-superadmin-key-change-in-production

{
  "name": "TechCorp S.A.S",
  "slug": "techcorp",
  "subdomain": "tickets.techcorp.com",
  "admin_email": "admin@techcorp.com",
  "admin_name": "Laura Martínez",
  "auth_method": "local",
  "primary_color": "#2E7D32",
  "send_welcome": false
}
```

**Resultado esperado:**
- HTTP 201
- Body:
```json
{
  "tenant_id": "<uuid>",
  "slug": "techcorp",
  "admin_email": "admin@techcorp.com",
  "admin_password_generated": true,
  "message": "Tenant 'TechCorp S.A.S' creado exitosamente. ..."
}
```

---

### TC-SAPI-002: API Key inválida es rechazada

**Request:** Mismo body, pero con `X-API-Key: clave-incorrecta`

**Resultado esperado:** HTTP 401, `detail: "API key inválida"`

---

### TC-SAPI-003: API Key ausente es rechazada

**Request:** Sin header `X-API-Key`

**Resultado esperado:** HTTP 422 (campo requerido faltante en header)

---

### TC-SAPI-004: SUPERADMIN_API_KEY no configurada

**Precondición:** Variable de entorno `SUPERADMIN_API_KEY` vacía o no definida

**Request:** Con cualquier valor en `X-API-Key`

**Resultado esperado:** HTTP 503, `detail: "Superadmin API key no configurada"`

---

### TC-SAPI-005: Slug duplicado es rechazado

**Precondición:** Ya existe `slug = 'techcorp'`

**Request:** Mismo slug, diferente subdominio y email

**Resultado esperado:** HTTP 409, `detail: "El slug 'techcorp' ya está en uso"`

---

### TC-SAPI-006: Subdominio duplicado es rechazado

**Precondición:** Ya existe `subdomain = 'tickets.techcorp.com'`

**Request:** Diferente slug, mismo subdominio

**Resultado esperado:** HTTP 409, `detail: "El subdominio 'tickets.techcorp.com' ya está en uso"`

---

### TC-SAPI-007: Slug con formato inválido (mayúsculas, espacios)

**Request:**
```json
{ "slug": "Tech Corp", ... }
```

**Resultado esperado:** HTTP 422 — validación del patrón `^[a-z0-9]+(-[a-z0-9]+)*$`

---

### TC-SAPI-008: Email de admin inválido

**Request:**
```json
{ "admin_email": "no-es-email", ... }
```

**Resultado esperado:** HTTP 422 — Pydantic EmailStr validation

---

### TC-SAPI-009: Color primario con formato inválido

**Request:**
```json
{ "primary_color": "azul-marino", ... }
```

**Resultado esperado:** HTTP 422 — validación del patrón `^#[0-9a-fA-F]{6}$`

---

### TC-SAPI-010: auth_method con valor fuera del enum

**Request:**
```json
{ "auth_method": "saml", ... }
```

**Resultado esperado:** HTTP 422

---

### TC-SAPI-011: Contraseña manual proporcionada — no se genera una aleatoria

**Request con `admin_password`:**
```json
{ "admin_password": "ManualPass1!", ... }
```

**Resultado esperado:**
- HTTP 201
- `admin_password_generated: false`
- El admin puede hacer login con "ManualPass1!"

---

### TC-SAPI-012: La contraseña generada NO aparece en la respuesta de la API

**Acción:** Crear tenant sin `admin_password`

**Verificación:**
- El response JSON **no contiene** la contraseña generada
- `admin_password_generated: true` en el response (señal para el cliente de usar el CLI)

---

### TC-SAPI-013: El endpoint no requiere JWT de tenant

**Verificación:**
- El endpoint no incluye la dependency `CurrentUser` ni `TenantId`
- Llamar sin `Authorization` header funciona (autenticado solo por API key)

---

### TC-SAPI-014: Endpoint superadmin no aparece en el scope de tenant JWT

**Acción:** Usar un JWT de tenant válido (sin header `X-API-Key`) en el endpoint

**Resultado esperado:** HTTP 422 (header requerido ausente) — el JWT de tenant no da acceso

---

## 42. FASE 6 — Verificación del Tenant Provisionado

### TC-PROV-001: Admin puede hacer login inmediatamente

**Precondición:** Tenant creado por script o API con contraseña conocida

**Request:**
```http
POST /api/v1/auth/login
Content-Type: application/json
X-Tenant-Slug: empresa-demo

{
  "email": "admin@empresademo.com",
  "password": "<contraseña_del_onboarding>"
}
```

**Resultado esperado:**
- HTTP 200
- `access_token` y `refresh_token` válidos
- `role` = "admin"

---

### TC-PROV-002: Admin puede acceder al panel de configuración

**Precondición:** Token obtenido en TC-PROV-001

**Request:** `GET /api/v1/admin/config` con JWT del admin del nuevo tenant

**Resultado esperado:**
- HTTP 200
- `timezone` = "America/Bogota" (valor de la plantilla)
- `working_hours_start` = "08:00:00"
- `auto_close_days` = 3

---

### TC-PROV-003: Áreas del nuevo tenant son accesibles

**Request:** `GET /api/v1/areas` con JWT del admin del nuevo tenant

**Resultado esperado:**
- HTTP 200
- 5 áreas: Soporte TI, Recursos Humanos, Administración, Compras, Operaciones

---

### TC-PROV-004: Categorías del nuevo tenant son accesibles

**Request:** `GET /api/v1/admin/categories` con JWT del admin del nuevo tenant

**Resultado esperado:**
- HTTP 200
- 7 categorías, cada una con su `default_area_id` correcto

---

### TC-PROV-005: SLAs del nuevo tenant son accesibles

**Request:** `GET /api/v1/admin/slas` con JWT del admin del nuevo tenant

**Resultado esperado:**
- 4 SLAs con prioridades: urgent, high, medium, low
- Horas correctas según la plantilla

---

### TC-PROV-006: Aislamiento multi-tenant post-onboarding

**Precondición:** Tenant 1 (Smart Security) y Tenant 2 (Empresa Demo) ambos creados

**Acción:** Con el JWT del admin de Empresa Demo, intentar ver datos de Smart Security

**Verificación:**
```sql
-- Los tickets de Smart Security no deben aparecer en consultas de Empresa Demo
SELECT COUNT(*) FROM tickets WHERE tenant_id = '<empresa_demo_id>'
  AND tenant_id != '<smart_security_id>';
```

- `GET /api/v1/tickets` del admin de Empresa Demo → solo tickets de ese tenant
- `GET /api/v1/users` del admin de Empresa Demo → solo usuarios de ese tenant

---

### TC-PROV-007: Admin del nuevo tenant puede crear su primer ticket

**Precondición:** Autenticado como admin de Empresa Demo

**Request:**
```http
POST /api/v1/tickets
X-Tenant-Slug: empresa-demo

{
  "title": "Primer ticket de prueba",
  "description": "Verificación de funcionamiento",
  "priority": "low"
}
```

**Resultado esperado:**
- HTTP 201
- `tenant_id` = `<empresa_demo_id>`
- El ticket no aparece en `GET /api/v1/tickets` del admin de Smart Security

---

### TC-PROV-008: SLA se asigna automáticamente al nuevo ticket

**Precondición:** Ticket creado con `priority = "urgent"` en el nuevo tenant

**Verificación:**
- `sla_due_at` calculado según el SLA de urgente: `resolution_hours = 4`
- El SLA referenciado pertenece al tenant correcto (no al de otro tenant)

---

## 43. FASE 6 — Plantilla YAML y Configuración

### TC-YAML-001: Estructura del YAML de plantilla es válida

**Verificación:**
```bash
python -c "import yaml; data = yaml.safe_load(open('scripts/templates/default_tenant.yaml')); print(list(data.keys()))"
```

**Resultado esperado:** `['areas', 'categories', 'slas', 'tenant_config']` (sin errores de parseo)

---

### TC-YAML-002: Categorías del YAML referencian áreas existentes en el mismo YAML

**Verificación manual del `default_tenant.yaml`:**
- Cada `area` referenciada en `categories` existe en la sección `areas`
- No hay referencias huérfanas

---

### TC-YAML-003: YAML personalizado — áreas sin categorías relacionadas

**Precondición:** YAML con áreas pero sin categorías

**Acción:** Ejecutar `create_tenant.py` con ese YAML

**Resultado esperado:**
- El tenant se crea con áreas pero 0 categorías
- Sin errores en el script

---

### TC-YAML-004: YAML con horario laboral fuera de rango

**Acción:** YAML con `working_hours_start: "25:00"` (hora inválida)

**Resultado esperado:**
- El script falla con error al parsear `time(*map(int, "25:00".split(":")))` → `ValueError`
- Mensaje de error claro en consola

---

### TC-YAML-005: Tenant creado sin sección `tenant_config` en el YAML

**Precondición:** YAML sin la clave `tenant_config`

**Resultado esperado:**
- Se usan valores por defecto (definidos en el código: `auto_close_days=3`, `timezone="America/Bogota"`, etc.)
- El tenant se crea correctamente

---

## 44. FASE 6 — Seguridad del Endpoint Superadmin

### TC-SEC-SA-001: La API key usa comparación de tiempo constante

**Verificación en código:**
- `secrets.compare_digest(x_api_key, settings.SUPERADMIN_API_KEY)` (no `==`)
- Protege contra timing attacks

---

### TC-SEC-SA-002: El endpoint superadmin no está en el scope del middleware de tenant

**Verificación:**
- Las requests a `/api/v1/superadmin/*` no requieren ni validan `X-Tenant-Slug`
- El endpoint opera a nivel de sistema, sin contexto de tenant

---

### TC-SEC-SA-003: SUPERADMIN_API_KEY por defecto es insegura en dev pero se documenta como tal

**Verificación en `docker-compose.yml`:**
```
SUPERADMIN_API_KEY=dev-superadmin-key-change-in-production
```
- El valor explícita que debe cambiarse en producción
- La guía `docs/onboarding.md` menciona este prerrequisito

---

### TC-SEC-SA-004: El endpoint no expone la contraseña del admin en la respuesta

**Acción:** Crear tenant vía API sin `admin_password` (se genera automáticamente)

**Verificación:**
- El response body no contiene ningún campo `admin_password`
- `admin_password_generated: true` indica al operador que debe obtener la contraseña por otro medio (usar el CLI)

---

### TC-SEC-SA-005: Logs no exponen la contraseña del admin

**Acción:** Revisar los logs del servidor durante la creación de un tenant

**Verificación:**
- No aparece la contraseña en texto plano en los logs de FastAPI/Uvicorn
- No aparece en el body del request logueado

---

### TC-SEC-SA-006: El endpoint superadmin no aparece en `/docs` (producción)

**Precondición:** `ENVIRONMENT = "production"` (que desactiva `/docs`)

**Verificación:**
- `GET /docs` retorna 404
- El endpoint existe y funciona, pero no está documentado públicamente

---

## 45. Matriz de Cobertura — Fase 6

| Funcionalidad | Script CLI | API Superadmin |
|---|---|---|
| Crear tenant + config | ✅ | ✅ |
| Crear usuario admin inicial | ✅ | ✅ |
| Crear áreas desde plantilla | ✅ | ✅ |
| Crear categorías desde plantilla | ✅ | ✅ |
| Crear SLAs desde plantilla | ✅ | ✅ |
| Generar contraseña segura automáticamente | ✅ | ✅ |
| Contraseña manual | ✅ | ✅ |
| Envío de correo de bienvenida | ✅ | ✅ (best-effort) |
| Plantilla YAML personalizable | ✅ | ❌ (usa default) |
| Validar slug único | ✅ (BD) | ✅ (HTTP 409) |
| Validar subdominio único | ✅ (BD) | ✅ (HTTP 409) |
| Autenticación por API key | N/A | ✅ |
| Timing-safe API key comparison | N/A | ✅ |
| Contraseña no expuesta en response | N/A | ✅ |
| Aislamiento multi-tenant post-creación | ✅ | ✅ |

### Criterios de aceptación para Fase 6

Para considerar la Fase 6 como **APROBADA**, se requiere:

| Criterio | Umbral |
|---|---|
| Script `create_tenant.py` crea tenant completo en un solo comando | 100% |
| Los 5 elementos provisionados (tenant, config, admin, áreas, categorías, SLAs) son correctos | 100% |
| Admin puede hacer login inmediatamente tras el onboarding | 100% |
| API superadmin rechaza requests sin API key válida | 100% |
| Slug y subdominio duplicados son rechazados (409) | 100% |
| Contraseña generada cumple política de seguridad | 100% |
| Contraseña NO expuesta en response de la API | 100% |
| Aislamiento multi-tenant: el nuevo tenant no ve datos de otros | 100% |
| SLA se asigna correctamente en tickets del nuevo tenant | 100% |
| Plantilla YAML personalizada funciona correctamente | 100% |
| Script maneja errores (plantilla no encontrada, SMTP caído) gracefully | 100% |

---

## Apéndice A: Comandos útiles para pruebas

### Levantar ambiente
```bash
make dev                                          # Inicia todos los servicios
docker compose exec backend alembic upgrade head  # Aplica migraciones
docker compose exec backend python seed.py        # Carga datos de prueba
```

### Ejecutar tests automatizados
```bash
make test                                         # Todos los tests
docker compose exec backend pytest tests/ -v      # Verboso
docker compose exec backend pytest tests/test_tickets.py -v  # Solo tickets
docker compose exec backend pytest tests/test_sla.py -v      # Solo SLA
docker compose exec backend pytest -k "TC-AUTH"  # Por nombre de test
```

### Inspeccionar BD
```bash
docker compose exec postgres psql -U postgres -d tickets_dev
\dt                          # Listar tablas
SELECT * FROM tickets LIMIT 5;
```

### Inspeccionar Redis
```bash
docker compose exec redis redis-cli
KEYS refresh:*              # Ver tokens activos
TTL refresh:<user>:<jti>    # Ver tiempo restante
```

### Logs de Celery
```bash
docker compose logs celery_worker -f
```

---

### Comandos Fase 4 adicionales

```bash
# Tareas Celery Fase 4
docker compose exec celery_worker celery -A app.tasks.celery_app call app.tasks.recurring_tasks.process_recurring_tickets
docker compose exec celery_worker celery -A app.tasks.celery_app call app.tasks.report_tasks.send_weekly_report --args='["<tenant_id>"]'

# Tests Fase 4
docker compose exec backend pytest tests/test_recurring.py -v
docker compose exec backend pytest tests/test_dashboard.py -v
docker compose exec backend pytest tests/test_admin.py -v
docker compose exec backend pytest tests/test_users.py -v
```

### Comandos Fase 6 — Onboarding

```bash
# Onboarding vía script CLI (dentro del contenedor)
docker exec -it aplicativotickets-backend-1 bash
python -m scripts.create_tenant \
  --name "Empresa Demo S.A.S" \
  --slug "empresa-demo" \
  --subdomain "tickets.empresademo.com" \
  --admin-email "admin@empresademo.com" \
  --admin-name "Juan García" \
  --auth-method local \
  --primary-color "#1565C0" \
  --send-welcome

# Onboarding vía API (desde fuera del contenedor)
curl -X POST http://localhost:8000/api/v1/superadmin/tenants \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev-superadmin-key-change-in-production" \
  -d '{
    "name": "TechCorp S.A.S",
    "slug": "techcorp",
    "subdomain": "tickets.techcorp.com",
    "admin_email": "admin@techcorp.com",
    "auth_method": "local",
    "primary_color": "#2E7D32"
  }'

# Verificar tenant en BD
docker compose exec postgres psql -U postgres -d tickets_dev \
  -c "SELECT id, slug, name FROM tenants ORDER BY created_at DESC LIMIT 5;"

# Verificar datos provisionados
docker compose exec postgres psql -U postgres -d tickets_dev \
  -c "SELECT 'áreas' as tipo, COUNT(*) FROM areas WHERE tenant_id='<id>'
      UNION ALL SELECT 'categorías', COUNT(*) FROM categories WHERE tenant_id='<id>'
      UNION ALL SELECT 'SLAs', COUNT(*) FROM slas WHERE tenant_id='<id>'
      UNION ALL SELECT 'usuarios', COUNT(*) FROM users WHERE tenant_id='<id>';"

# Validar YAML de plantilla
python -c "import yaml; data = yaml.safe_load(open('scripts/templates/default_tenant.yaml')); \
  print(f'Áreas: {len(data[\"areas\"])}, Categorías: {len(data[\"categories\"])}, SLAs: {len(data[\"slas\"])}')"
```

### Comandos Fase 5 — Frontend

```bash
# Levantar el frontend
cd frontend && npm run dev          # Dev server en http://localhost:3000
npm run build && npm start          # Build de producción

# Verificar llamadas al backend (en navegador)
# DevTools → Network → filtrar por "api/v1"

# Cypress / Playwright (si configurado)
npx cypress open                    # Suite de tests E2E interactivos
npx playwright test                 # Suite headless

# Verificar WebSocket
# DevTools → Network → WS → ver frames del canal /api/v1/ws

# Probar roles distintos (abrir sesión en incógnito con distintas cuentas)
# Admin:       admin@smartsecurity.co
# Supervisor:  supervisor@smartsecurity.co
# Agent:       agent1@smartsecurity.co
# Requester:   requester1@smartsecurity.co
```

---

## Apéndice B: Criterios de Aceptación

### Fases 1 y 2

Para considerar las Fases 1 y 2 como **APROBADAS**, se requiere:

| Criterio | Umbral |
|---|---|
| Tests automatizados pasando | 100% (sin errores) |
| Casos críticos de RBAC | 100% (ningún bypass de permisos) |
| Aislamiento multi-tenant | 100% (cero cross-tenant data leaks) |
| Transiciones de estado válidas | 100% |
| Transiciones de estado inválidas rechazadas | 100% |
| Validaciones de entrada | > 95% |
| Cálculo de SLA en horas de negocio | 100% |
| Adjuntos: MIME y tamaño rechazados | 100% |

### Fase 4

Para considerar la Fase 4 como **APROBADA**, se requiere adicionalmente:

| Criterio | Umbral |
|---|---|
| CRUD usuarios (crear, actualizar, archivar) | 100% |
| Archivado de usuario revoca tokens y desasigna tickets | 100% |
| CRUD áreas y gestión de miembros | 100% |
| CRUD categorías con enrutamiento | 100% |
| CRUD SLAs sin duplicados | 100% |
| Configuración de tenant actualizable | 100% |
| Plantillas recurrentes — calculate_next_run correcto | 100% |
| Plantilla correcta genera ticket con campos heredados | 100% |
| Tarea `process_recurring_tickets` idempotente | 100% |
| Dashboard — aislamiento multi-tenant en métricas | 100% |
| Dashboard urgency abuse — control de acceso especial | 100% |
| Reporte semanal — solo supervisor/admin | 100% |

### Fase 6

Para considerar la Fase 6 como **APROBADA**, se requiere adicionalmente:

| Criterio | Umbral |
|---|---|
| Script CLI crea tenant completo en un solo comando | 100% |
| Provisiona exactamente: 5 áreas, 7 categorías, 4 SLAs (plantilla default) | 100% |
| Admin puede hacer login inmediatamente tras onboarding | 100% |
| API superadmin rechaza sin API key válida (401/422) | 100% |
| Slug y subdominio duplicados reciben HTTP 409 | 100% |
| Contraseña generada cumple política (mayúscula+minúscula+dígito+símbolo) | 100% |
| Contraseña NO expuesta en response de la API | 100% |
| Nuevo tenant aislado de datos de otros tenants | 100% |
| SLA heredado correctamente en tickets del nuevo tenant | 100% |
| Plantilla YAML personalizada reemplaza la default | 100% |
| Errores (plantilla no encontrada, SMTP caído) manejados gracefully | 100% |

### Fase 5

Para considerar la Fase 5 como **APROBADA**, se requiere adicionalmente:

| Criterio | Umbral |
|---|---|
| Login / Logout funcional | 100% |
| Protección de rutas (sin sesión → redirige a login) | 100% |
| Control de acceso por rol en UI (rutas admin bloqueadas) | 100% |
| Dashboard carga métricas reales del backend | 100% |
| Lista de tickets con filtros operativos | ≥ 95% |
| Detalle de ticket — comentarios, adjuntos, historial | 100% |
| Crear ticket con auto-enrutamiento visible en UI | 100% |
| CRUD completo de usuarios en frontend | 100% |
| CRUD completo de áreas con panel de miembros | 100% |
| CRUD completo de categorías con toggle estado | 100% |
| CRUD completo de SLAs con confirmación de eliminación | 100% |
| CRUD completo de plantillas recurrentes | 100% |
| Configuración de tenant — color picker, horario, días | 100% |
| Reportes — SLA compliance + agent performance | 100% |
| Notificaciones — marcar leídas / marcar todas | 100% |
| WebSocket — notificación en tiempo real | ≥ 90% |
| Sin errores de consola en flujos principales | 100% |

---

*Documento generado para el proyecto Smart Security Tickets — © 2026*
