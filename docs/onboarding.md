# Guía de Onboarding — Incorporación de Nuevos Clientes

Este documento describe el proceso completo para dar de alta un nuevo cliente (tenant) en el sistema de tickets.

---

## Prerrequisitos

- El stack de producción está corriendo (`docker compose up -d`)
- Tienes acceso SSH al servidor o acceso al contenedor `backend`
- Tienes el `SUPERADMIN_API_KEY` configurado en las variables de entorno

---

## Opción A — Script CLI (recomendado para consola)

Ejecuta el script desde dentro del contenedor backend:

```bash
docker exec -it aplicativotickets-backend-1 bash

# Dentro del contenedor:
python -m scripts.create_tenant \
  --name "Empresa Demo S.A.S" \
  --slug "empresa-demo" \
  --subdomain "tickets.empresademo.com" \
  --admin-email "admin@empresademo.com" \
  --admin-name "Juan García" \
  --auth-method local \
  --primary-color "#1565C0" \
  --send-welcome
```

### Parámetros disponibles

| Parámetro | Requerido | Descripción |
|-----------|-----------|-------------|
| `--name` | Sí | Nombre visible del cliente |
| `--slug` | Sí | Identificador único (solo minúsculas, números y guiones) |
| `--subdomain` | Sí | Subdominio asignado al cliente |
| `--admin-email` | Sí | Email del administrador inicial |
| `--admin-name` | No | Nombre completo del admin (default: "Administrador") |
| `--admin-password` | No | Contraseña manual (se genera automáticamente si se omite) |
| `--auth-method` | No | `local` o `azure` (default: `local`) |
| `--primary-color` | No | Color primario en hex (default: `#1565C0`) |
| `--template` | No | Ruta a un YAML de plantilla personalizado |
| `--send-welcome` | No | Envía correo de bienvenida al admin |

### Ejemplo de salida exitosa

```
============================================================
  Tenant creado exitosamente: Empresa Demo S.A.S
============================================================
  Slug:       empresa-demo
  Subdominio: tickets.empresademo.com
  Auth:       local
  Áreas:      5
  Categorías: 7
  SLAs:       4

  CREDENCIALES DE ACCESO
  Email:      admin@empresademo.com
  Contraseña: xK3!mP9@nZ  ← GUARDAR AHORA
============================================================
```

---

## Opción B — API REST (para integraciones programáticas)

El endpoint `POST /api/v1/superadmin/tenants` permite crear tenants vía HTTP.

### Autenticación

Incluir el header `X-API-Key` con la clave de superadmin:

```
X-API-Key: <SUPERADMIN_API_KEY>
```

### Request

```http
POST /api/v1/superadmin/tenants
Content-Type: application/json
X-API-Key: dev-superadmin-key-change-in-production

{
  "name": "Empresa Demo S.A.S",
  "slug": "empresa-demo",
  "subdomain": "tickets.empresademo.com",
  "admin_email": "admin@empresademo.com",
  "admin_name": "Juan García",
  "auth_method": "local",
  "primary_color": "#1565C0",
  "send_welcome": false
}
```

### Campos del body

| Campo | Tipo | Requerido | Descripción |
|-------|------|-----------|-------------|
| `name` | string | Sí | Nombre del tenant |
| `slug` | string | Sí | Slug único (regex: `^[a-z0-9]+(-[a-z0-9]+)*$`) |
| `subdomain` | string | Sí | Subdominio |
| `admin_email` | email | Sí | Email del admin |
| `admin_name` | string | No | Nombre del admin |
| `admin_password` | string | No | Contraseña (mínimo 8 caracteres; se genera si se omite) |
| `auth_method` | `local`\|`azure` | No | Método de auth (default: `local`) |
| `primary_color` | string | No | Color hex (default: `#1565C0`) |
| `send_welcome` | boolean | No | Enviar correo al admin (default: `false`) |

### Response `201 Created`

```json
{
  "tenant_id": "550e8400-e29b-41d4-a716-446655440000",
  "slug": "empresa-demo",
  "admin_email": "admin@empresademo.com",
  "admin_password_generated": true,
  "message": "Tenant 'Empresa Demo S.A.S' creado exitosamente. La contraseña generada se incluye en la respuesta — guárdala ahora."
}
```

> ⚠ **Importante:** Si `admin_password_generated` es `true`, la contraseña NO se incluye en la respuesta por seguridad. Usa `--admin-password` para definirla o emplea el script CLI que la muestra en consola.

### Errores comunes

| Código | Causa |
|--------|-------|
| `401` | API key inválida o ausente |
| `409` | El slug o subdominio ya existe |
| `422` | Datos inválidos (slug con caracteres inválidos, email mal formado, etc.) |
| `503` | `SUPERADMIN_API_KEY` no configurada en el servidor |

---

## Lo que se crea automáticamente

Al crear un tenant (por script o API), el sistema provisiona:

### Áreas (5)
- Soporte TI
- Recursos Humanos
- Administración
- Compras
- Operaciones

### Categorías (7)
- Soporte TI → área: Soporte TI
- Mantenimiento → área: Operaciones
- Nómina → área: Recursos Humanos
- Vacaciones y Permisos → área: Recursos Humanos
- Compras → área: Compras
- Administración → área: Administración
- General → área: Operaciones

### SLAs por defecto
| Prioridad | Respuesta | Resolución |
|-----------|-----------|------------|
| Urgente | 1 hora | 4 horas |
| Alta | 4 horas | 8 horas |
| Media | 8 horas | 24 horas |
| Baja | 24 horas | 72 horas |

### Usuario admin
- Rol: `admin`
- Puede gestionar todo el tenant desde el panel `/admin`

---

## Pasos posteriores al onboarding

Una vez creado el tenant, el administrador debe:

1. **Ingresar al sistema** en `http://<subdomain>/login` (o `http://localhost:3000` en dev)
2. **Cambiar la contraseña** inicial
3. **Personalizar la configuración** en `/admin/config`:
   - Logo y colores
   - Horario laboral y zona horaria
   - Días de trabajo
   - Umbral de abuso de urgencia
4. **Crear usuarios** en `/admin/users` (agentes, supervisores, solicitantes)
5. **Ajustar áreas** en `/admin/areas` — asignar managers y miembros
6. **Revisar categorías** en `/admin/categories` — ajustar enrutamiento automático
7. **Ajustar SLAs** en `/admin/slas` si los valores por defecto no aplican

---

## Configuración de Azure AD (opcional)

Si el cliente usa Microsoft 365:

1. Registrar la aplicación en [portal.azure.com](https://portal.azure.com) → Azure Active Directory → App registrations
2. Configurar Redirect URI: `https://<tu-dominio>/api/v1/auth/callback/azure`
3. Anotar: `Application (client) ID`, `Directory (tenant) ID`, y crear un `Client Secret`
4. En `/admin/config`, cambiar `auth_method` a `azure` e ingresar los valores anteriores
5. Probar el flujo con "Ingresar con Microsoft" en la página de login

---

## Personalizar la plantilla de onboarding

Puedes crear una plantilla YAML personalizada para clientes con estructura diferente:

```bash
cp scripts/templates/default_tenant.yaml scripts/templates/mi_cliente.yaml
# Editar mi_cliente.yaml con las áreas y categorías específicas
python -m scripts.create_tenant \
  --name "Mi Cliente" \
  --slug "mi-cliente" \
  --subdomain "tickets.micliente.com" \
  --admin-email "admin@micliente.com" \
  --template scripts/templates/mi_cliente.yaml
```
