"""
Presentation layer package.

This package contains all presentation-related modules:
- API routes and endpoints
- Request/response schemas
- Dependency injection setup
- Authentication and authorization

Structure:
- api/ - API endpoint modules
- dependencies.py - Dependency injection container
- schemas.py - Pydantic models for request/response
"""

# Import only the dependency container to avoid circular imports
from .dependencies import DependencyContainer

__all__ = [
    "DependencyContainer"
]