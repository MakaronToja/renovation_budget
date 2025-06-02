from fastapi import FastAPI
import uvicorn
import os

from renovation_cost_tracker.infrastructure.db import get_engine, get_session_factory
from renovation_cost_tracker.infrastructure.repositories import (
    PostgresExpenseRepository,
)
from renovation_cost_tracker.application.services import ExpenseService
from renovation_cost_tracker.presentation.api import router as expense_router

dsn = os.getenv("DATABASE_URL")
engine = get_engine(dsn)

def create_app() -> FastAPI:
    app = FastAPI(title="Renovation Cost Tracker")
    # --- infra bootstrapping ---
    engine = get_engine("postgresql+asyncpg://user:pass@db/renovation")
    session_factory = get_session_factory(engine)
    expense_repo = PostgresExpenseRepository(session_factory)
    expense_service = ExpenseService(
        proj_repo=None,  # TODO: wstrzyknąć ProjectRepository
        exp_repo=expense_repo,
    )
    # upychamy service do depends, albo używamy FastAPI DI containers
    expense_router.dependencies = [(Depends(lambda: expense_service),)]
    app.include_router(expense_router)
    return app


if __name__ == "__main__":
    uvicorn.run(create_app(), host="0.0.0.0", port=8000)
