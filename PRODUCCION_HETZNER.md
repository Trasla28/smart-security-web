# Despliegue en Producción — Hetzner CX33

## Información del servidor

| Campo | Valor |
|-------|-------|
| Proveedor | Hetzner Cloud |
| Plan | CX33 (4 vCPU / 8GB RAM / 80GB SSD / 20TB tráfico) |
| OS | Ubuntu 24.04 |
| Datacenter | Helsinki, Finlandia |
| IP pública | 178.104.130.113 |
| Dominio | https://tickets.smarts.com.co |
| SSL | Let's Encrypt (vence 2026-07-19, auto-renovación activa) |

## Acceso SSH

```bash
ssh deploy@178.104.130.113
```

- Clave SSH local: `C:\Users\Home\.ssh\id_ed25519`
- Usuario principal: `deploy`
- Ruta del proyecto: `/home/deploy/app`

> Para comandos que requieren sudo, la contraseña del usuario `deploy` es necesaria.

## Credenciales de la aplicación

| Rol | Email | Contraseña |
|-----|-------|-----------|
| Admin | admin@smartsecurity.com | Admin1234! |

> **Importante:** Cambiar la contraseña del admin desde el panel.

## Base de datos PostgreSQL

| Campo | Valor |
|-------|-------|
| Motor | PostgreSQL 16 (Alpine) |
| Base de datos | tickets_db |
| Usuario | tickets_user |
| Contraseña | Atenama1328. |
| Puerto interno | 5432 (solo accesible dentro de la red Docker) |
| IP contenedor | 172.18.0.4 |

> El puerto 5432 NO está expuesto al exterior. Para acceder remotamente usar túnel SSH.

### Conectarse a la base de datos desde terminal (en el servidor)

```bash
docker compose -f /home/deploy/app/docker-compose.prod.yml exec db psql -U tickets_user -d tickets_db
```

### Conectarse con DBeaver desde tu PC (túnel SSH)

**Paso 1** — Abrí una terminal en tu PC y ejecutá (dejala abierta):
```bash
ssh -L 15432:172.18.0.4:5432 deploy@178.104.130.113
```

**Paso 2** — En DBeaver creá una conexión PostgreSQL con:

| Campo | Valor |
|-------|-------|
| Host | localhost |
| Puerto | 15432 |
| Base de datos | tickets_db |
| Usuario | tickets_user |
| Contraseña | Atenama1328. |

> Nota: Usar puerto 15432 (no 5432 ni 5433) porque Windows bloquea puertos bajos sin permisos de admin.

## Repositorio

- GitHub: https://github.com/Trasla28/smart-security-web
- Rama principal: `master`
- Ruta en servidor: `/home/deploy/app`

> Para hacer git pull en el servidor usar: `sudo git pull`

## Variables de entorno

Archivo: `/home/deploy/app/.env`

```env
DATABASE_URL=postgresql+asyncpg://tickets_user:Atenama1328.@db:5432/tickets_db
POSTGRES_DB=tickets_db
POSTGRES_USER=tickets_user
POSTGRES_PASSWORD=Atenama1328.
REDIS_URL=redis://redis:6379/0
SECRET_KEY=4647d011df6feb63f5e2dbcdfaeafb149caa8b68f9910b2b5504c6fb3d2b2c18
SUPERADMIN_API_KEY=acf60810872b71fd577320bc0dae35c4c8e62ce330ab29fab65c878650ead0d2
ENVIRONMENT=production
STORAGE_PATH=/app/storage
API_BASE_URL=https://tickets.smarts.com.co
FRONTEND_URL=https://tickets.smarts.com.co
NEXTAUTH_URL=https://tickets.smarts.com.co
NEXTAUTH_SECRET=21966e581e8331a465fc1ce19f8bc981e9095aa28c0d22ee60fbee3dd0483fd8
NEXT_PUBLIC_API_URL=https://tickets.smarts.com.co
NEXT_PUBLIC_WS_URL=wss://tickets.smarts.com.co
API_URL=http://backend:8000
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=tucorreo@gmail.com
SMTP_PASSWORD=xxxx xxxx xxxx xxxx
SMTP_FROM=tucorreo@gmail.com
SMTP_TLS=true
AZURE_CLIENT_ID=<ver portal.azure.com>
AZURE_TENANT_ID=<ver portal.azure.com>
AZURE_CLIENT_SECRET=<ver portal.azure.com>
```

> **Importante:** Si se edita el .env con nano y tiene líneas muy largas, usar Python para recrearlo:
> ```bash
> python3 -c "open('/home/deploy/app/.env','w').write('...')"
> ```

## Azure AD (Microsoft Login)

| Campo | Valor |
|-------|-------|
| Client ID | b6802fa1-6585-470c-a312-10a0ae8fc16f |
| Tenant ID | 20bc6f88-ce9a-4161-8ef6-cd275a000463 |
| Redirect URI registrada | https://tickets.smarts.com.co/api/v1/auth/callback/azure |

- Configuración en: portal.azure.com → App registrations → Authentication → Redirect URIs
- El tenant en la BD debe tener `azure_tenant_id` configurado en la tabla `tenant_configs`

### Verificar configuración Azure en BD
```bash
docker compose -f docker-compose.prod.yml exec db psql -U tickets_user -d tickets_db \
  -c "SELECT id, tenant_id, azure_tenant_id FROM tenant_configs;"
```

### Actualizar azure_tenant_id si está vacío
```bash
docker compose -f docker-compose.prod.yml exec db psql -U tickets_user -d tickets_db \
  -c "UPDATE tenant_configs SET azure_tenant_id = '20bc6f88-ce9a-4161-8ef6-cd275a000463' WHERE tenant_id = '0c0a04c7-4eeb-43d5-a131-8cbaa74b12ff';"
```

## Arquitectura desplegada

```
Internet (HTTPS)
      │
      ▼
   Nginx (443/80)
   /etc/nginx/sites-enabled/tickets
      │
      ├── /api/auth/  → Frontend Next.js (localhost:3000)  [rutas NextAuth]
      ├── /api/       → Backend FastAPI  (localhost:8000)  [SIN rewrite de /api]
      ├── /ws/        → Backend FastAPI  (localhost:8000)  [WebSockets]
      └── /           → Frontend Next.js (localhost:3000)
```

## Contenedores Docker

| Contenedor | Imagen | Puerto expuesto |
|------------|--------|----------------|
| app-backend-1 | app-backend | 0.0.0.0:8000 |
| app-frontend-1 | app-frontend | 0.0.0.0:3000 |
| app-worker-1 | app-worker | — |
| app-beat-1 | app-beat | — |
| app-db-1 | postgres:16-alpine | interno 5432 |
| app-redis-1 | redis:7-alpine | interno 6379 |
| app-mailhog-1 | mailhog/mailhog | 0.0.0.0:8025 |

## Configuración Nginx actual

Archivo: `/etc/nginx/sites-enabled/tickets`

```nginx
server {
    server_name tickets.smarts.com.co;

    location /api/auth/ {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /api/ {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    location /ws/ {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "Upgrade";
        proxy_set_header Host $host;
    }

    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }

    listen 443 ssl;
    ssl_certificate /etc/letsencrypt/live/tickets.smarts.com.co/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/tickets.smarts.com.co/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;
}

server {
    listen 80;
    server_name tickets.smarts.com.co;
    return 301 https://$host$request_uri;
}
```

> **Importante:** La sección `/api/` NO debe tener `rewrite ^/api/(.*) /$1 break;`
> porque el backend FastAPI registra sus rutas con el prefijo `/api/v1/...`.

## Comandos útiles en el servidor

### Ver estado de los contenedores
```bash
cd /home/deploy/app
docker compose -f docker-compose.prod.yml ps
```

### Ver logs de un servicio
```bash
cd /home/deploy/app
docker compose -f docker-compose.prod.yml logs backend --tail=50
docker compose -f docker-compose.prod.yml logs frontend --tail=50
docker compose -f docker-compose.prod.yml logs db --tail=50
```

### Reiniciar un servicio
```bash
cd /home/deploy/app
docker compose -f docker-compose.prod.yml restart backend
```

### Bajar y subir todo
```bash
cd /home/deploy/app
docker compose -f docker-compose.prod.yml down
docker compose -f docker-compose.prod.yml up -d
```

### Actualizar con cambios del repositorio
```bash
cd /home/deploy/app
sudo git pull
docker compose -f docker-compose.prod.yml up -d --build
```

### Reconstruir solo el frontend (cuando cambian vars NEXT_PUBLIC_*)
```bash
cd /home/deploy/app
docker compose -f docker-compose.prod.yml up -d --build frontend
```

### Correr migraciones de base de datos
```bash
docker exec app-backend-1 alembic upgrade head
```

### Recargar Nginx
```bash
sudo nginx -t && sudo systemctl reload nginx
```

## API Superadmin

### Crear un tenant
```bash
curl -X POST https://tickets.smarts.com.co/api/v1/superadmin/tenants \
  -H "Content-Type: application/json" \
  -H "X-API-Key: acf60810872b71fd577320bc0dae35c4c8e62ce330ab29fab65c878650ead0d2" \
  -d '{
    "name": "Nombre Empresa",
    "slug": "nombre-empresa",
    "subdomain": "nombre-empresa",
    "admin_email": "admin@empresa.com",
    "admin_name": "Administrador",
    "admin_password": "Password123!"
  }'
```

## Pendientes

- [x] **SMTP real** — Gmail configurado (usar App Password, no la contraseña de cuenta)
- [ ] **Cambiar contraseña del admin** desde el panel
- [ ] **Configurar backups** automáticos de PostgreSQL
