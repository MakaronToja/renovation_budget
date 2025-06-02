from decimal import Decimal
from datetime import datetime
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from renovation_cost_tracker.application.services import ProjectService, ExpenseService
from renovation_cost_tracker.presentation.dependencies import (
    get_project_service,
    get_expense_service,
    get_current_active_user
)
from renovation_cost_tracker.domain.models import User, Project
from renovation_cost_tracker.presentation.schemas import (
    ProjectCreate, ProjectOut, MoneySchema
)


router = APIRouter()


class ProjectSummary(ProjectOut):
    """Extended project summary with financial analytics"""
    budget_utilization_percent: float
    by_category: dict
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "name": "Kitchen Renovation",
                "budget": {"amount": 15000.00, "currency": "PLN"},
                "created_at": "2024-01-15T10:30:00Z",
                "total_cost": {"amount": 8500.75, "currency": "PLN"},
                "remaining_budget": {"amount": 6499.25, "currency": "PLN"},
                "expense_count": 12,
                "budget_utilization_percent": 56.67,
                "by_category": {
                    "MATERIAL": {"amount": 5500.00, "currency": "PLN"},
                    "LABOR": {"amount": 3000.75, "currency": "PLN"}
                }
            }
        }
    }


def project_to_response(project: Project) -> ProjectOut:
    """Convert Project entity to response schema"""
    return ProjectOut(
        id=project.id,
        name=project.name,
        budget=MoneySchema(amount=project.budget.amount, currency=project.budget.currency),
        created_at=project.created_at.isoformat(),
        total_cost=MoneySchema(amount=project.total_cost.amount, currency=project.total_cost.currency),
        remaining_budget=MoneySchema(
            amount=project.remaining_budget().amount,
            currency=project.remaining_budget().currency
        ),
        expense_count=len(project.expenses)
    )


@router.post(
    "/",
    response_model=ProjectOut,
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
    response_model=List[ProjectOut],
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
    response_model=ProjectOut,
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
            detail="Failed to get project details"
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
            by_category[category.value] = {
                "amount": money.amount,
                "currency": money.currency
            }
        
        # Create response using the base project response plus summary fields
        base_response = project_to_response(project)
        
        return ProjectSummary(
            id=base_response.id,
            name=base_response.name,
            budget=base_response.budget,
            created_at=base_response.created_at,
            total_cost=base_response.total_cost,
            remaining_budget=base_response.remaining_budget,
            expense_count=base_response.expense_count,
            budget_utilization_percent=round(budget_utilization, 2),
            by_category=by_category
        )
        
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