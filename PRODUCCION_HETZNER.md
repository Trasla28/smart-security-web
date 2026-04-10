# Despliegue en Producción — Hetzner CX33

## Información del servidor

| Campo | Valor |
|-------|-------|
| Proveedor | Hetzner Cloud |
| Plan | CX33 (4 vCPU / 8GB RAM / 80GB SSD / 20TB tráfico) |
| OS | Ubuntu 24.04 |
| Datacenter | Helsinki, Finlandia |
| IP pública | 178.104.130.113 |
| URL actual | http://178.104.130.113 |

## Acceso SSH

```bash
ssh root@178.104.130.113
# o con el usuario deploy:
ssh deploy@178.104.130.113
```

La clave SSH está en: `C:\Users\Home\.ssh\id_ed25519`

## Credenciales de la aplicación

| Rol | Email | Contraseña |
|-----|-------|-----------|
| Admin | admin@smartsecurity.com | Admin1234! |

> **Importante:** Cambia la contraseña del admin desde el panel lo antes posible.

## Repositorio

- GitHub: https://github.com/Trasla28/smart-security-web
- Rama principal: `master`
- Ruta en servidor: `/home/deploy/app`

## Arquitectura desplegada

```
Internet
   │
   ▼
Nginx (puerto 80)
   │
   ├── /api/auth/  → Frontend Next.js (puerto 3000)  [rutas NextAuth]
   ├── /api/       → Backend FastAPI  (puerto 8000)
   ├── /ws/        → Backend FastAPI  (puerto 8000)  [WebSockets]
   └── /           → Frontend Next.js (puerto 3000)
```

### Contenedores Docker activos

| Contenedor | Imagen | Puerto |
|------------|--------|--------|
| app-backend-1 | app-backend | 8000 |
| app-frontend-1 | app-frontend | 3000 |
| app-worker-1 | app-worker | — |
| app-beat-1 | app-beat | — |
| app-db-1 | postgres:16-alpine | 5432 (interno) |
| app-redis-1 | redis:7-alpine | 6379 (interno) |
| app-mailhog-1 | mailhog/mailhog | 8025 |

## Variables de entorno

Archivo: `/home/deploy/app/.env.production`

```env
POSTGRES_DB=tickets_db
POSTGRES_USER=tickets_user
POSTGRES_PASSWORD=Atenama1328.
DATABASE_URL=postgresql+asyncpg://tickets_user:Atenama1328.@db:5432/tickets_db
REDIS_URL=redis://redis:6379/0
SECRET_KEY=4647d011df6feb63f5e2dbcdfaeafb149caa8b68f9910b2b5504c6fb3d2b2c18
ENVIRONMENT=production
STORAGE_PATH=/app/storage
SUPERADMIN_API_KEY=acf60810872b71fd577320bc0dae35c4c8e62ce330ab29fab65c878650ead0d2
NEXTAUTH_URL=http://178.104.130.113
NEXTAUTH_SECRET=21966e581e8331a465fc1ce19f8bc981e9095aa28c0d22ee60fbee3dd0483fd8
NEXT_PUBLIC_API_URL=http://178.104.130.113/api
NEXT_PUBLIC_WS_URL=ws://178.104.130.113
API_URL=http://backend:8000
SMTP_HOST=mailhog
SMTP_PORT=1025
SMTP_USER=
SMTP_PASSWORD=
SMTP_FROM=noreply@tickets.local
FRONTEND_URL=http://178.104.130.113
```

## Comandos útiles en el servidor

### Ver estado de los contenedores
```bash
cd /home/deploy/app
docker compose -f docker-compose.prod.yml --env-file .env.production ps
```

### Ver logs de un servicio
```bash
docker logs app-backend-1 --tail 50
docker logs app-frontend-1 --tail 50
docker logs app-worker-1 --tail 50
```

### Reiniciar un servicio
```bash
docker compose -f docker-compose.prod.yml --env-file .env.production restart backend
docker compose -f docker-compose.prod.yml --env-file .env.production restart frontend
```

### Apagar todo
```bash
docker compose -f docker-compose.prod.yml --env-file .env.production down
```

### Actualizar la app con nuevos cambios del repositorio
```bash
cd /home/deploy/app
git pull origin master
docker compose -f docker-compose.prod.yml --env-file .env.production up -d --build
```

### Correr migraciones de base de datos
```bash
docker exec app-backend-1 alembic upgrade head
```

## API Superadmin

La API de superadmin permite crear nuevos tenants.

### Crear un tenant
```bash
curl -X POST http://localhost:8000/api/v1/superadmin/tenants \
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

## Configuración Nginx

Archivo: `/etc/nginx/sites-available/tickets`

```nginx
server {
    listen 80;
    server_name 178.104.130.113;

    location /api/auth/ {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /api/ {
        rewrite ^/api/(.*) /$1 break;
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
}
```

### Recargar Nginx
```bash
nginx -t && systemctl reload nginx
```

## Pendientes para completar el ambiente

- [ ] **Dominio propio** — comprar un dominio y apuntar un registro A a `178.104.130.113`
- [ ] **HTTPS / SSL** — instalar certificado Let's Encrypt con certbot:
  ```bash
  certbot --nginx -d tudominio.com
  ```
- [ ] **SMTP real** — reemplazar MailHog con SendGrid, Gmail u otro proveedor. Actualizar en `.env.production`:
  ```
  SMTP_HOST=smtp.sendgrid.net
  SMTP_PORT=587
  SMTP_USER=apikey
  SMTP_PASSWORD=tu_api_key_sendgrid
  SMTP_FROM=noreply@tudominio.com
  ```
- [ ] **Actualizar URLs** — cuando tengas dominio, actualizar en `.env.production`:
  ```
  NEXTAUTH_URL=https://tudominio.com
  NEXT_PUBLIC_API_URL=https://tudominio.com/api
  NEXT_PUBLIC_WS_URL=wss://tudominio.com
  FRONTEND_URL=https://tudominio.com
  ```
- [ ] **Cambiar contraseña del admin** desde el panel
- [ ] **Crear usuarios** — agregar agentes y usuarios desde el panel de administración
- [ ] **Configurar backups** — automatizar backups de la base de datos PostgreSQL
