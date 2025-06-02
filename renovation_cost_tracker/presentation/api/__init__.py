"""
API endpoints package.

Contains modular API routers:
- auth.py - Authentication endpoints (register, login, token)
- projects.py - Project management endpoints
- expenses.py - Expense CRUD and export endpoints

Each module is self-contained with its own schemas and dependencies.
"""

from .auth import router as auth_router
from .projects import router as projects_router  
from .expenses import router as expenses_router

__all__ = [
    "auth_router",
    "projects_router", 
    "expenses_router"
]