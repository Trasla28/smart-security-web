# Import all models so SQLAlchemy can resolve every relationship
# across the full mapper graph before any query runs.
from app.models.base import BaseModel
from app.models.tenant import Tenant, TenantConfig
from app.models.user import User, UserArea
from app.models.area import Area
from app.models.category import Category
from app.models.sla import SLA
from app.models.ticket import Ticket, TicketComment, TicketHistory, TicketAttachment
from app.models.notification import Notification
from app.models.recurring import RecurringTemplate

__all__ = [
    "BaseModel",
    "Tenant",
    "TenantConfig",
    "User",
    "UserArea",
    "Area",
    "Category",
    "SLA",
    "Ticket",
    "TicketComment",
    "TicketHistory",
    "TicketAttachment",
    "Notification",
    "RecurringTemplate",
]
