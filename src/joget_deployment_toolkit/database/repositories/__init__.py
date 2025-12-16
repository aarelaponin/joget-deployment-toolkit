"""
Repository package for database access patterns.

Provides repository classes following the Repository pattern for clean
separation between business logic and data access.

Available repositories:
- BaseRepository: Abstract base class for all repositories
- FormRepository: Form data access
- ApplicationRepository: Application data access
"""

from .application_repository import ApplicationRepository
from .base import BaseRepository
from .form_repository import FormRepository

__all__ = [
    "BaseRepository",
    "FormRepository",
    "ApplicationRepository",
]
