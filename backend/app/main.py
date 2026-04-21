from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.middleware.tenant import TenantMiddleware
from app.routers import auth, tickets, users, areas, admin, dashboard, notifications, superadmin, files

app = FastAPI(
    title="Smart Security Tickets API",
    version="1.0.0",
    docs_url="/docs" if settings.ENVIRONMENT != "production" else None,
    redoc_url="/redoc" if settings.ENVIRONMENT != "production" else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"] if settings.ENVIRONMENT == "development" else [],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(TenantMiddleware)

app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(tickets.router, prefix="/api/v1/tickets", tags=["tickets"])
app.include_router(users.router, prefix="/api/v1/users", tags=["users"])
app.include_router(areas.router, prefix="/api/v1/areas", tags=["areas"])
app.include_router(admin.router, prefix="/api/v1/admin", tags=["admin"])
app.include_router(dashboard.router, prefix="/api/v1/dashboard", tags=["dashboard"])
app.include_router(notifications.router, prefix="/api/v1/notifications", tags=["notifications"])
app.include_router(superadmin.router, prefix="/api/v1/superadmin", tags=["superadmin"])
app.include_router(files.router, prefix="/api/v1/files", tags=["files"])


@app.get("/health", tags=["system"])
async def health_check():
    return {"status": "ok"}
