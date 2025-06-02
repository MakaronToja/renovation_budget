import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
import uvicorn

from renovation_cost_tracker.infrastructure.db import get_engine, get_session_factory, Base
from renovation_cost_tracker.infrastructure.repositories import (
    PostgresUserRepository,
    PostgresProjectRepository,
    PostgresExpenseRepository,
)
from renovation_cost_tracker.application.services import (
    AuthService,
    ProjectService,
    ExpenseService,
)
from renovation_cost_tracker.presentation.api.auth import router as auth_router
from renovation_cost_tracker.presentation.api.projects import router as project_router
from renovation_cost_tracker.presentation.api.expenses import router as expense_router
from renovation_cost_tracker.presentation.dependencies import DependencyContainer


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager - startup and shutdown logic"""
    # Startup
    print("🚀 Starting Renovation Cost Tracker...")
    
    # Initialize database tables
    engine = app.state.container.engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    print("✅ Database tables created/verified")
    yield
    
    # Shutdown
    print("🛑 Shutting down Renovation Cost Tracker...")
    await app.state.container.engine.dispose()
    print("✅ Database connections closed")


def create_app() -> FastAPI:
    """Factory function to create and configure FastAPI application"""
    
    app = FastAPI(
        title="Renovation Cost Tracker",
        description="REST API for tracking renovation project expenses",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan
    )
    
    # Setup dependency injection container
    dsn = os.getenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/renovation")
    container = DependencyContainer(dsn)
    app.state.container = container
    
    # Include routers with their respective prefixes
    app.include_router(auth_router, prefix="/auth", tags=["Authentication"])
    app.include_router(project_router, prefix="/projects", tags=["Projects"])
    app.include_router(expense_router, tags=["Expenses"])
    
    @app.get("/", tags=["Health"])
    async def health_check():
        """Health check endpoint"""
        return {
            "status": "healthy",
            "service": "Renovation Cost Tracker",
            "version": "1.0.0"
        }
    
    @app.get("/health", tags=["Health"])
    async def detailed_health():
        """Detailed health check with database connectivity"""
        try:
            # Test database connection
            async with container.get_session() as session:
                await session.execute("SELECT 1")
            
            return {
                "status": "healthy",
                "database": "connected",
                "service": "Renovation Cost Tracker"
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "database": "disconnected",
                "error": str(e)
            }
    
    return app


# Create application instance
app = create_app()


if __name__ == "__main__":
    uvicorn.run(
        "renovation_cost_tracker.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )