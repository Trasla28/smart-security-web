"""Seed script to create test data for development."""
import asyncio
import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.models.tenant import Tenant, TenantConfig
from app.models.user import User
from app.models.area import Area, UserArea
from app.models.category import Category
from app.models.sla import SLA
from app.models.ticket import Ticket, TicketHistory

engine = create_async_engine(settings.DATABASE_URL)
session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def seed():
    async with session_factory() as db:
        # Create tenant
        tenant_id = uuid.uuid4()
        tenant = Tenant(
            id=tenant_id,
            slug="smart-security",
            name="Smart Security",
            subdomain="tickets.smartsecurity.com.co",
        )
        db.add(tenant)

        tenant_config = TenantConfig(
            tenant_id=tenant_id,
            primary_color="#1565C0",
            auth_method="local",
            auto_close_days=3,
            urgency_abuse_threshold=50,
        )
        db.add(tenant_config)

        # Create users
        from passlib.context import CryptContext
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

        admin_id = uuid.uuid4()
        admin = User(
            id=admin_id,
            tenant_id=tenant_id,
            email="admin@smartsecurity.com.co",
            full_name="Administrador Sistema",
            password_hash=pwd_context.hash("Admin123!"),
            role="admin",
        )
        db.add(admin)

        supervisor_id = uuid.uuid4()
        supervisor = User(
            id=supervisor_id,
            tenant_id=tenant_id,
            email="supervisor@smartsecurity.com.co",
            full_name="Supervisor General",
            password_hash=pwd_context.hash("Super123!"),
            role="supervisor",
        )
        db.add(supervisor)

        agent1_id = uuid.uuid4()
        agent1 = User(
            id=agent1_id,
            tenant_id=tenant_id,
            email="agente.ti@smartsecurity.com.co",
            full_name="Agente TI",
            password_hash=pwd_context.hash("Agent123!"),
            role="agent",
        )
        db.add(agent1)

        agent2_id = uuid.uuid4()
        agent2 = User(
            id=agent2_id,
            tenant_id=tenant_id,
            email="agente.rrhh@smartsecurity.com.co",
            full_name="Agente RRHH",
            password_hash=pwd_context.hash("Agent123!"),
            role="agent",
        )
        db.add(agent2)

        requester_id = uuid.uuid4()
        requester = User(
            id=requester_id,
            tenant_id=tenant_id,
            email="solicitante@smartsecurity.com.co",
            full_name="Juan Pérez",
            password_hash=pwd_context.hash("User123!"),
            role="requester",
        )
        db.add(requester)

        # Create areas
        area_ti_id = uuid.uuid4()
        area_ti = Area(
            id=area_ti_id,
            tenant_id=tenant_id,
            name="Tecnología",
            description="Área de TI y soporte técnico",
            manager_id=supervisor_id,
        )
        db.add(area_ti)

        area_rrhh_id = uuid.uuid4()
        area_rrhh = Area(
            id=area_rrhh_id,
            tenant_id=tenant_id,
            name="Recursos Humanos",
            description="Área de gestión humana",
            manager_id=supervisor_id,
        )
        db.add(area_rrhh)

        area_ops_id = uuid.uuid4()
        area_ops = Area(
            id=area_ops_id,
            tenant_id=tenant_id,
            name="Operaciones",
            description="Área operativa",
            manager_id=supervisor_id,
        )
        db.add(area_ops)

        # Assign users to areas
        db.add(UserArea(tenant_id=tenant_id, user_id=agent1_id, area_id=area_ti_id, is_primary=True))
        db.add(UserArea(tenant_id=tenant_id, user_id=agent2_id, area_id=area_rrhh_id, is_primary=True))
        db.add(UserArea(tenant_id=tenant_id, user_id=supervisor_id, area_id=area_ti_id, is_primary=True))

        # Create categories
        cat_hardware_id = uuid.uuid4()
        cat_hardware = Category(
            id=cat_hardware_id,
            tenant_id=tenant_id,
            name="Hardware",
            description="Problemas con equipos físicos",
            default_area_id=area_ti_id,
            default_agent_id=agent1_id,
        )
        db.add(cat_hardware)

        cat_software_id = uuid.uuid4()
        cat_software = Category(
            id=cat_software_id,
            tenant_id=tenant_id,
            name="Software",
            description="Problemas con aplicaciones",
            default_area_id=area_ti_id,
        )
        db.add(cat_software)

        cat_nomina_id = uuid.uuid4()
        cat_nomina = Category(
            id=cat_nomina_id,
            tenant_id=tenant_id,
            name="Nómina",
            description="Solicitudes relacionadas con nómina",
            default_area_id=area_rrhh_id,
            default_agent_id=agent2_id,
        )
        db.add(cat_nomina)

        cat_vacaciones_id = uuid.uuid4()
        cat_vacaciones = Category(
            id=cat_vacaciones_id,
            tenant_id=tenant_id,
            name="Vacaciones",
            description="Solicitudes de vacaciones",
            default_area_id=area_rrhh_id,
        )
        db.add(cat_vacaciones)

        cat_general_id = uuid.uuid4()
        cat_general = Category(
            id=cat_general_id,
            tenant_id=tenant_id,
            name="General",
            description="Solicitudes generales",
            default_area_id=area_ops_id,
        )
        db.add(cat_general)

        # Create SLAs
        db.add(SLA(
            tenant_id=tenant_id,
            category_id=None,
            priority="urgent",
            response_hours=1,
            resolution_hours=4,
        ))
        db.add(SLA(
            tenant_id=tenant_id,
            category_id=None,
            priority="high",
            response_hours=4,
            resolution_hours=8,
        ))
        db.add(SLA(
            tenant_id=tenant_id,
            category_id=None,
            priority="medium",
            response_hours=8,
            resolution_hours=24,
        ))
        db.add(SLA(
            tenant_id=tenant_id,
            category_id=None,
            priority="low",
            response_hours=24,
            resolution_hours=72,
        ))

        # Create 20 sample tickets
        statuses = ["open", "in_progress", "pending", "escalated", "resolved", "closed"]
        priorities = ["low", "medium", "high", "urgent"]
        categories = [cat_hardware_id, cat_software_id, cat_nomina_id, cat_vacaciones_id, cat_general_id]
        areas = [area_ti_id, area_rrhh_id, area_ops_id]

        for i in range(1, 21):
            ticket_id = uuid.uuid4()
            status = statuses[i % len(statuses)]
            ticket = Ticket(
                id=ticket_id,
                tenant_id=tenant_id,
                ticket_number=f"#TK-{i:04d}",
                title=f"Solicitud de prueba #{i}",
                description=f"Descripción detallada de la solicitud de prueba número {i}.",
                status=status,
                priority=priorities[i % len(priorities)],
                category_id=categories[i % len(categories)],
                area_id=areas[i % len(areas)],
                requester_id=requester_id,
                assigned_to=agent1_id if i % 2 == 0 else None,
            )
            db.add(ticket)
            db.add(TicketHistory(
                tenant_id=tenant_id,
                ticket_id=ticket_id,
                actor_id=requester_id,
                action="created",
                new_value={"status": "open", "priority": ticket.priority},
            ))

        await db.commit()
        print("Seed data created successfully!")
        print("\nCredentials:")
        print("  Admin:      admin@smartsecurity.com.co / Admin123!")
        print("  Supervisor: supervisor@smartsecurity.com.co / Super123!")
        print("  Agent TI:   agente.ti@smartsecurity.com.co / Agent123!")
        print("  Agent RRHH: agente.rrhh@smartsecurity.com.co / Agent123!")
        print("  Requester:  solicitante@smartsecurity.com.co / User123!")


if __name__ == "__main__":
    asyncio.run(seed())
