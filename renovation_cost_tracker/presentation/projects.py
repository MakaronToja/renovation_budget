from decimal import Decimal
from datetime import datetime
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from renovation_cost_tracker.application.services import ProjectService, ExpenseService
from renovation_cost_tracker.presentation.dependencies import (
    get_project_service,
    get_expense_service,
    get_current_active_user
)
from renovation_cost_tracker.domain.models import User, Project, Money


router = APIRouter()


# Pydantic schemas
class MoneySchema(BaseModel):
    """Money value object schema"""
    amount: Decimal = Field(..., description="Amount in decimal format", example=10000.50)
    currency: str = Field(default="PLN", description="Currency code", example="PLN")


class ProjectCreate(BaseModel):
    """Project creation request schema"""
    name: str = Field(..., min_length=1, max_length=255, description="Project name", example="Bathroom Renovation")
    budget: Decimal = Field(..., gt=0, description="Project budget amount", example=15000.00)
    currency: str = Field(default="PLN", description="Budget currency", example="PLN")
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "Kitchen Renovation",
                "budget": 20000.50,
                "currency": "PLN"
            }
        }


class ProjectResponse(BaseModel):
    """Project response schema"""
    id: str
    name: str
    budget: MoneySchema
    created_at: datetime
    total_cost: MoneySchema
    remaining_budget: MoneySchema
    expense_count: int = 0
    
    class Config:
        from_attributes = True


class ProjectSummary(BaseModel):
    """Project financial summary schema"""
    total_cost: MoneySchema
    budget: MoneySchema
    remaining_budget: MoneySchema
    budget_utilization_percent: float = Field(..., description="Percentage of budget used")
    by_category: dict = Field(..., description="Costs grouped by category")
    expense_count: int
    
    class Config:
        json_schema_extra = {
            "example": {
                "total_cost": {"amount": 8500.75, "currency": "PLN"},
                "budget": {"amount": 15000.00, "currency": "PLN"},
                "remaining_budget": {"amount": 6499.25, "currency": "PLN"},
                "budget_utilization_percent": 56.67,
                "by_category": {
                    "MATERIAL": {"amount": 5500.00, "currency": "PLN"},
                    "LABOR": {"amount": 3000.75, "currency": "PLN"}
                },
                "expense_count": 12
            }
        }


def project_to_response(project: Project) -> ProjectResponse:
    """Convert Project entity to response schema"""
    return ProjectResponse(
        id=str(project.id),
        name=project.name,
        budget=MoneySchema(amount=project.budget.amount, currency=project.budget.currency),
        created_at=project.created_at,
        total_cost=MoneySchema(amount=project.total_cost.amount, currency=project.total_cost.currency),
        remaining_budget=MoneySchema(
            amount=project.remaining_budget().amount,
            currency=project.remaining_budget().currency
        ),
        expense_count=len(project.expenses)
    )


@router.post(
    "/",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create new project",
    description="Create a new renovation project with name and budget"
)
async def create_project(
    project_data: ProjectCreate,
    current_user: User = Depends(get_current_active_user),
    project_service: ProjectService = Depends(get_project_service)
):
    """
    Create a new renovation project.
    
    **Requirements:**
    - User must be authenticated
    - Project name must be unique for the user
    - Budget must be positive
    
    **Process:**
    1. Validate project data
    2. Create project associated with current user
    3. Return project details with generated ID
    
    **Returns:**
    - Created project information
    - HTTP 201 on success
    - HTTP 400 on validation errors
    """
    try:
        # Create project through service
        project_id = await project_service.create_project(
            user_id=current_user.id,
            name=project_data.name,
            budget=project_data.budget,
            currency=project_data.currency
        )
        
        # Fetch created project to return full data
        project = await project_service.get_project(project_id)
        
        return project_to_response(project)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create project"
        )


@router.get(
    "/",
    response_model=List[ProjectResponse],
    summary="List user projects",
    description="Get list of all projects belonging to the current user"
)
async def list_user_projects(
    current_user: User = Depends(get_current_active_user),
    project_service: ProjectService = Depends(get_project_service)
):
    """
    Get list of user's projects.
    
    **Requirements:**
    - User must be authenticated
    
    **Returns:**
    - List of user's projects with basic information
    - Empty list if user has no projects
    - HTTP 200 always (even for empty list)
    """
    try:
        projects = await project_service.list_user_projects(current_user.id)
        return [project_to_response(project) for project in projects]
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch projects"
        )


@router.get(
    "/{project_id}",
    response_model=ProjectResponse,
    summary="Get project details",
    description="Get detailed information about a specific project"
)
async def get_project_details(
    project_id: UUID,
    current_user: User = Depends(get_current_active_user),
    project_service: ProjectService = Depends(get_project_service)
):
    """
    Get project details by ID.
    
    **Requirements:**
    - User must be authenticated
    - Project must belong to the current user
    
    **Returns:**
    - Project details including costs and budget status
    - HTTP 200 on success
    - HTTP 404 if project not found or doesn't belong to user
    """
    try:
        project = await project_service.get_project(project_id)
        
        # Verify project ownership
        if project.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )
        
        return project_to_response(project)
        
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get project summary"
        )


@router.get(
    "/{project_id}/summary",
    response_model=ProjectSummary,
    summary="Get project financial summary",
    description="Get comprehensive financial summary of the project including category breakdown"
)
async def get_project_summary(
    project_id: UUID,
    current_user: User = Depends(get_current_active_user),
    project_service: ProjectService = Depends(get_project_service),
    expense_service: ExpenseService = Depends(get_expense_service)
):
    """
    Get project financial summary.
    
    **Requirements:**
    - User must be authenticated
    - Project must belong to the current user
    
    **Returns:**
    - Comprehensive financial summary including:
      - Total costs and remaining budget
      - Budget utilization percentage
      - Costs breakdown by category
      - Number of expenses
    - HTTP 200 on success
    - HTTP 404 if project not found or doesn't belong to user
    """
    try:
        # Verify project exists and belongs to user
        project = await project_service.get_project(project_id)
        if project.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )
        
        # Get detailed summary from expense service
        summary_data = await expense_service.summarize(project_id)
        
        # Calculate budget utilization percentage
        budget_utilization = 0.0
        if project.budget.amount > 0:
            budget_utilization = float(
                (summary_data["total_cost"].amount / project.budget.amount) * 100
            )
        
        # Convert Money objects in category breakdown to schema format
        by_category = {}
        for category, money in summary_data["by_category"].items():
            by_category[category.value] = MoneySchema(
                amount=money.amount,
                currency=money.currency
            )
        
        return ProjectSummary(
            total_cost=MoneySchema(
                amount=summary_data["total_cost"].amount,
                currency=summary_data["total_cost"].currency
            ),
            budget=MoneySchema(
                amount=summary_data["budget"].amount,
                currency=summary_data["budget"].currency
            ),
            remaining_budget=MoneySchema(
                amount=summary_data["remaining_budget"].amount,
                currency=summary_data["remaining_budget"].currency
            ),
            budget_utilization_percent=round(budget_utilization, 2),
            by_category=by_category,
            expense_count=summary_data["expense_count"]
        )