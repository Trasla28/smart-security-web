"""Repository package – data-access layer."""
from app.repositories.ticket_repository import TicketRepository
from app.repositories.comment_repository import CommentRepository

__all__ = ["TicketRepository", "CommentRepository"]
