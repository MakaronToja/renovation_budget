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

from .dependencies import DependencyContainer
from .schemas import (
    ExpenseCreate, ExpenseUpdate, ExpenseOut,
    ProjectCreate, ProjectOut,
    UserCreate, UserOut,
    Token
)

__all__ = [
    "DependencyContainer",
    "ExpenseCreate", "ExpenseUpdate", "ExpenseOut",
    "ProjectCreate", "ProjectOut", 
    "UserCreate", "UserOut",
    "Token"
]
