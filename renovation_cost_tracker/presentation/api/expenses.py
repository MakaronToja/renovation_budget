import csv
import io
from datetime import date
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from renovation_cost_tracker.application.services import ExpenseService, ProjectService
from renovation_cost_tracker.presentation.dependencies import (
    get_expense_service,
    get_project_service,
    get_current_active_user
)
from renovation_cost_tracker.domain.models import User, Category
from renovation_cost_tracker.presentation.schemas import ExpenseCreate, ExpenseOut


router = APIRouter()


# Additional Pydantic schemas for expenses
class ExpenseUpdate(BaseModel):
    """Expense update request schema"""
    amount: Optional[Decimal] = Field(None, gt=0, description="Expense amount")
    category: Optional[Category] = Field(None, description="Expense category")
    vendor: Optional[str] = Field(None, min_length=1, max_length=255, description="Vendor name")
    date: Optional[date] = Field(None, description="Expense date")
    description: Optional[str] = Field(None, max_length=500, description="Expense description")
    
    class Config:
        json_schema_extra = {
            "example": {
                "amount": 1750.00,
                "category": "MATERIAL",
                "vendor": "Updated BuildStore",
                "date": "2024-01-20",
                "description": "Updated description"
            }
        }


class ExpenseFilter(BaseModel):
    """Expense filtering parameters"""
    category: Optional[Category] = None
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    min_amount: Optional[Decimal] = Field(None, ge=0)
    max_amount: Optional[Decimal] = Field(None, ge=0)
    vendor: Optional[str] = None


class ExpenseListResponse(BaseModel):
    """Response schema for expense list with metadata"""
    expenses: List[ExpenseOut]
    total_count: int
    filtered_count: int
    total_amount: Decimal
    currency: str = "PLN"


async def verify_project_ownership(
    project_id: UUID,
    current_user: User,
    project_service: ProjectService
) -> None:
    """
    Verify that project belongs to current user.
    
    Args:
        project_id: Project to verify
        current_user: Current authenticated user
        project_service: Project service instance
        
    Raises:
        HTTPException: If project not found or doesn't belong to user
    """
    try:
        project = await project_service.get_project(project_id)
        if project.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )


async def verify_expense_ownership(
    expense_id: UUID,
    current_user: User,
    expense_service: ExpenseService,
    project_service: ProjectService
) -> None:
    """
    Verify that expense belongs to current user's project.
    
    Args:
        expense_id: Expense to verify
        current_user: Current authenticated user
        expense_service: Expense service instance
        project_service: Project service instance
        
    Raises:
        HTTPException: If expense not found or doesn't belong to user's project
    """
    try:
        expense = await expense_service.get_expense(expense_id)
        await verify_project_ownership(expense.project_id, current_user, project_service)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Expense not found"
        )


@router.post(
    "/projects/{project_id}/expenses",
    response_model=ExpenseOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create new expense",
    description="Add a new expense to a project"
)
async def create_expense(
    project_id: UUID,
    expense_data: ExpenseCreate,
    current_user: User = Depends(get_current_active_user),
    expense_service: ExpenseService = Depends(get_expense_service),
    project_service: ProjectService = Depends(get_project_service)
):
    """
    Create a new expense for a project.
    
    **Requirements:**
    - User must be authenticated
    - Project must belong to the current user
    - All expense data must be valid
    
    **Business Rules:**
    - Amount must be positive
    - Date cannot be in the future
    - Vendor name is required
    
    **Returns:**
    - Created expense information
    - HTTP 201 on success
    - HTTP 400 on validation errors
    - HTTP 404 if project not found
    """
    # Verify project ownership
    await verify_project_ownership(project_id, current_user, project_service)
    
    try:
        # Create expense through service
        expense_id = await expense_service.record_expense(
            project_id=project_id,
            amount=expense_data.amount,
            category=expense_data.category,
            vendor=expense_data.vendor,
            date=expense_data.date,
            description=expense_data.description or ""
        )
        
        # Return created expense data
        return ExpenseOut(
            id=expense_id,
            amount=expense_data.amount,
            category=expense_data.category,
            vendor=expense_data.vendor,
            date=expense_data.date,
            description=expense_data.description or ""
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create expense"
        )


@router.get(
    "/projects/{project_id}/expenses",
    response_model=ExpenseListResponse,
    summary="List project expenses",
    description="Get list of expenses for a project with optional filtering"
)
async def list_project_expenses(
    project_id: UUID,
    category: Optional[Category] = Query(None, description="Filter by category"),
    date_from: Optional[date] = Query(None, description="Filter expenses from this date"),
    date_to: Optional[date] = Query(None, description="Filter expenses to this date"),
    min_amount: Optional[Decimal] = Query(None, ge=0, description="Minimum expense amount"),
    max_amount: Optional[Decimal] = Query(None, ge=0, description="Maximum expense amount"),
    vendor: Optional[str] = Query(None, description="Filter by vendor name (partial match)"),
    current_user: User = Depends(get_current_active_user),
    expense_service: ExpenseService = Depends(get_expense_service),
    project_service: ProjectService = Depends(get_project_service)
):
    """
    List expenses for a project with filtering options.
    
    **Requirements:**
    - User must be authenticated
    - Project must belong to the current user
    
    **Filtering options:**
    - category: Filter by expense category
    - date_from/date_to: Date range filter
    - min_amount/max_amount: Amount range filter
    - vendor: Partial vendor name match
    
    **Returns:**
    - List of expenses with metadata
    - Total count and filtered count
    - Total amount of filtered expenses
    """
    # Verify project ownership
    await verify_project_ownership(project_id, current_user, project_service)
    
    try:
        # Get all expenses for the project
        all_expenses = await expense_service.list_expenses(project_id)
        
        # Apply filters
        filtered_expenses = all_expenses
        
        if category:
            filtered_expenses = [e for e in filtered_expenses if e.category == category]
        
        if date_from:
            filtered_expenses = [e for e in filtered_expenses if e.date >= date_from]
        
        if date_to:
            filtered_expenses = [e for e in filtered_expenses if e.date <= date_to]
        
        if min_amount is not None:
            filtered_expenses = [e for e in filtered_expenses if e.amount.amount >= min_amount]
        
        if max_amount is not None:
            filtered_expenses = [e for e in filtered_expenses if e.amount.amount <= max_amount]
        
        if vendor:
            vendor_lower = vendor.lower()
            filtered_expenses = [e for e in filtered_expenses if vendor_lower in e.vendor.lower()]
        
        # Calculate total amount of filtered expenses
        total_amount = sum((e.amount.amount for e in filtered_expenses), Decimal('0'))
        currency = filtered_expenses[0].amount.currency if filtered_expenses else "PLN"
        
        # Convert to response format
        expense_responses = [
            ExpenseOut(
                id=expense.id,
                amount=expense.amount.amount,
                category=expense.category,
                vendor=expense.vendor,
                date=expense.date,
                description=expense.description
            )
            for expense in filtered_expenses
        ]
        
        return ExpenseListResponse(
            expenses=expense_responses,
            total_count=len(all_expenses),
            filtered_count=len(filtered_expenses),
            total_amount=total_amount,
            currency=currency
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch expenses"
        )


@router.get(
    "/expenses/{expense_id}",
    response_model=ExpenseOut,
    summary="Get expense details",
    description="Get detailed information about a specific expense"
)
async def get_expense_details(
    expense_id: UUID,
    current_user: User = Depends(get_current_active_user),
    expense_service: ExpenseService = Depends(get_expense_service),
    project_service: ProjectService = Depends(get_project_service)
):
    """
    Get expense details by ID.
    
    **Requirements:**
    - User must be authenticated
    - Expense must belong to user's project
    
    **Returns:**
    - Expense details
    - HTTP 200 on success
    - HTTP 404 if expense not found or doesn't belong to user
    """
    # Verify expense ownership
    await verify_expense_ownership(expense_id, current_user, expense_service, project_service)
    
    try:
        expense = await expense_service.get_expense(expense_id)
        
        return ExpenseOut(
            id=expense.id,
            amount=expense.amount.amount,
            category=expense.category,
            vendor=expense.vendor,
            date=expense.date,
            description=expense.description
        )
        
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Expense not found"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch expense details"
        )


@router.put(
    "/expenses/{expense_id}",
    response_model=ExpenseOut,
    summary="Update expense",
    description="Update an existing expense"
)
async def update_expense(
    expense_id: UUID,
    expense_data: ExpenseUpdate,
    current_user: User = Depends(get_current_active_user),
    expense_service: ExpenseService = Depends(get_expense_service),
    project_service: ProjectService = Depends(get_project_service)
):
    """
    Update an existing expense.
    
    **Requirements:**
    - User must be authenticated
    - Expense must belong to user's project
    - Only provided fields will be updated
    
    **Returns:**
    - Updated expense information
    - HTTP 200 on success
    - HTTP 400 on validation errors
    - HTTP 404 if expense not found
    """
    # Verify expense ownership
    await verify_expense_ownership(expense_id, current_user, expense_service, project_service)
    
    try:
        # Prepare update data (only include non-None values)
        update_data = {}
        if expense_data.amount is not None:
            update_data['amount'] = expense_data.amount
        if expense_data.category is not None:
            update_data['category'] = expense_data.category
        if expense_data.vendor is not None:
            update_data['vendor'] = expense_data.vendor
        if expense_data.date is not None:
            update_data['date'] = expense_data.date
        if expense_data.description is not None:
            update_data['description'] = expense_data.description
        
        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No fields provided for update"
            )
        
        # Update expense
        await expense_service.update_expense(expense_id, **update_data)
        
        # Return updated expense
        updated_expense = await expense_service.get_expense(expense_id)
        
        return ExpenseOut(
            id=updated_expense.id,
            amount=updated_expense.amount.amount,
            category=updated_expense.category,
            vendor=updated_expense.vendor,
            date=updated_expense.date,
            description=updated_expense.description
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update expense"
        )


@router.delete(
    "/expenses/{expense_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete expense",
    description="Delete an existing expense"
)
async def delete_expense(
    expense_id: UUID,
    current_user: User = Depends(get_current_active_user),
    expense_service: ExpenseService = Depends(get_expense_service),
    project_service: ProjectService = Depends(get_project_service)
):
    """
    Delete an expense.
    
    **Requirements:**
    - User must be authenticated
    - Expense must belong to user's project
    
    **Returns:**
    - No content (HTTP 204)
    - HTTP 404 if expense not found
    """
    # Verify expense ownership
    await verify_expense_ownership(expense_id, current_user, expense_service, project_service)
    
    try:
        await expense_service.delete_expense(expense_id)
        
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Expense not found"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete expense"
        )


@router.get(
    "/projects/{project_id}/expenses/export",
    summary="Export expenses to CSV",
    description="Export project expenses to CSV file with optional filtering"
)
async def export_expenses_csv(
    project_id: UUID,
    category: Optional[Category] = Query(None, description="Filter by category"),
    date_from: Optional[date] = Query(None, description="Filter expenses from this date"),
    date_to: Optional[date] = Query(None, description="Filter expenses to this date"),
    current_user: User = Depends(get_current_active_user),
    expense_service: ExpenseService = Depends(get_expense_service),
    project_service: ProjectService = Depends(get_project_service)
):
    """
    Export project expenses to CSV file.
    
    **Requirements:**
    - User must be authenticated
    - Project must belong to the current user
    
    **Filtering options:**
    - category: Filter by expense category
    - date_from/date_to: Date range filter
    
    **Returns:**
    - CSV file with expenses data
    - Filename: expenses_[project_name]_[date].csv
    """
    # Verify project ownership
    await verify_project_ownership(project_id, current_user, project_service)
    
    try:
        # Get project details for filename
        project = await project_service.get_project(project_id)
        
        # Get filtered expenses
        expenses = await expense_service.get_expenses_for_export(
            project_id=project_id,
            category_filter=category,
            date_from=date_from,
            date_to=date_to
        )
        
        # Create CSV content in memory
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write CSV header
        writer.writerow([
            'Date',
            'Category', 
            'Amount',
            'Currency',
            'Vendor',
            'Description'
        ])
        
        # Write expense data
        for expense in expenses:
            writer.writerow([
                expense.date.strftime('%Y-%m-%d'),
                expense.category.value,
                str(expense.amount.amount),
                expense.amount.currency,
                expense.vendor,
                expense.description
            ])
        
        # Prepare response
        csv_content = output.getvalue()
        output.close()
        
        # Generate filename
        project_name_safe = "".join(c for c in project.name if c.isalnum() or c in (' ', '-', '_')).strip()
        project_name_safe = project_name_safe.replace(' ', '_')
        today = date.today().strftime('%Y%m%d')
        filename = f"expenses_{project_name_safe}_{today}.csv"
        
        # Return CSV as streaming response
        return StreamingResponse(
            io.BytesIO(csv_content.encode('utf-8')),
            media_type='text/csv',
            headers={
                'Content-Disposition': f'attachment; filename="{filename}"'
            }
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to export expenses"
        )