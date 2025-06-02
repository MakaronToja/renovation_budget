from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from renovation_cost_tracker.application.services import ExpenseService
from renovation_cost_tracker.presentation.schemas import ExpenseCreate, ExpenseOut

router = APIRouter(prefix="/projects/{project_id}/expenses", tags=["Expenses"])


def get_expense_service() -> ExpenseService: 
    return router.dependencies[0].dependency


@router.post(
    "",
    response_model=ExpenseOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_expense(
    project_id: UUID,
    payload: ExpenseCreate,
    service: ExpenseService = Depends(get_expense_service),
):
    try:
        exp_id = await service.record_expense(project_id, **payload.dict())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return ExpenseOut(id=exp_id, **payload.dict())
