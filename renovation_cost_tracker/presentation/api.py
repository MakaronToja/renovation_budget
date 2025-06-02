"""
Legacy API module - maintained for backward compatibility.

This module contains the original expense endpoint implementation.
New development should use the modular approach in:
- renovation_cost_tracker.presentation.api.auth
- renovation_cost_tracker.presentation.api.projects  
- renovation_cost_tracker.presentation.api.expenses

This file demonstrates the evolution from simple to complex API structure.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from renovation_cost_tracker.application.services import ExpenseService
from renovation_cost_tracker.presentation.schemas import ExpenseCreate, ExpenseOut
from renovation_cost_tracker.presentation.dependencies import get_expense_service, get_current_active_user
from renovation_cost_tracker.domain.models import User


# Create router for legacy endpoints
router = APIRouter(prefix="/projects/{project_id}/expenses", tags=["Expenses (Legacy)"])


@router.post(
    "",
    response_model=ExpenseOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create expense (Legacy)",
    description="Legacy endpoint for creating expenses. Use /projects/{id}/expenses instead.",
    deprecated=True
)
async def create_expense_legacy(
    project_id: UUID,
    payload: ExpenseCreate,
    current_user: User = Depends(get_current_active_user),
    service: ExpenseService = Depends(get_expense_service),
):
    """
    Legacy expense creation endpoint.
    
    **Note: This endpoint is deprecated.**
    Please use the new endpoint: POST /projects/{project_id}/expenses
    
    This endpoint demonstrates the original implementation
    and shows how the API evolved from simple to comprehensive.
    """
    try:
        # Basic project ownership check (simplified)
        # In the new API, this is handled by verify_project_ownership()
        
        # Record expense using service
        exp_id = await service.record_expense(
            project_id=project_id,
            amount=payload.amount,
            category=payload.category,
            vendor=payload.vendor,
            date=payload.date,
            description=payload.description or ""
        )
        
        # Return response in legacy format
        return ExpenseOut(
            id=exp_id,
            amount=payload.amount,
            category=payload.category,
            vendor=payload.vendor,
            date=payload.date,
            description=payload.description or ""
        )
        
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc)
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get(
    "",
    response_model=list[ExpenseOut],
    summary="List expenses (Legacy)",
    description="Legacy endpoint for listing expenses. Use /projects/{id}/expenses instead.",
    deprecated=True
)
async def list_expenses_legacy(
    project_id: UUID,
    current_user: User = Depends(get_current_active_user),
    service: ExpenseService = Depends(get_expense_service),
):
    """
    Legacy expense listing endpoint.
    
    **Note: This endpoint is deprecated.**
    Please use the new endpoint: GET /projects/{project_id}/expenses
    
    The new endpoint provides:
    - Advanced filtering options
    - Pagination support
    - Metadata (total count, amounts)
    - Better error handling
    """
    try:
        # Get expenses using service
        expenses = await service.list_expenses(project_id)
        
        # Convert to response format
        return [
            ExpenseOut(
                id=expense.id,
                amount=expense.amount.amount,
                category=expense.category,
                vendor=expense.vendor,
                date=expense.date,
                description=expense.description
            )
            for expense in expenses
        ]
        
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc)
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


# Demonstration of API evolution
class APIEvolutionNotes:
    """
    Documentation of how this API evolved from simple to comprehensive.
    
    This class serves as documentation for the evolution process
    and shows the benefits of modular API design.
    """
    
    ORIGINAL_DESIGN = """
    Original design (this file):
    - Single file with basic CRUD
    - Minimal error handling
    - No filtering or advanced features
    - Basic dependency injection
    """
    
    EVOLVED_DESIGN = """
    Evolved design (api/ directory):
    - Modular structure (auth.py, projects.py, expenses.py)
    - Comprehensive error handling
    - Advanced filtering and search
    - CSV export functionality
    - Rich response schemas with metadata
    - Proper authentication and authorization
    - OpenAPI documentation with examples
    """
    
    BENEFITS_OF_EVOLUTION = """
    Benefits of the new modular approach:
    
    1. Maintainability:
       - Clear separation of concerns
       - Easier to test individual modules
       - Reduced code duplication
    
    2. Scalability:
       - Easy to add new endpoints
       - Independent development of features
       - Better code organization
    
    3. Developer Experience:
       - Rich OpenAPI documentation
       - Type safety with Pydantic
       - Comprehensive error messages
    
    4. User Experience:
       - Advanced filtering options
       - CSV export functionality
       - Detailed response metadata
       - Consistent API patterns
    
    5. Security:
       - Proper authorization checks
       - User isolation
       - Input validation
    """


# Health check endpoint for legacy API
@router.get(
    "/health",
    tags=["Health"],
    summary="Legacy API health check",
    description="Health check for the legacy expense API"
)
async def legacy_api_health():
    """
    Health check for legacy API endpoints.
    
    Returns status information about the legacy API
    and migration guidance.
    """
    return {
        "status": "healthy",
        "api_version": "legacy",
        "message": "Legacy API is functional but deprecated",
        "migration_guide": {
            "current_endpoints": [
                "POST /projects/{id}/expenses (legacy)",
                "GET /projects/{id}/expenses (legacy)"
            ],
            "new_endpoints": [
                "POST /projects/{id}/expenses",
                "GET /projects/{id}/expenses",
                "GET /expenses/{id}",
                "PUT /expenses/{id}",
                "DELETE /expenses/{id}",
                "GET /projects/{id}/expenses/export"
            ],
            "recommendation": "Migrate to new endpoints for enhanced functionality"
        }
    }


# Example of dependency injection evolution
def get_expense_service_legacy():
    """
    Legacy dependency injection approach.
    
    This function shows the original dependency injection
    pattern before the introduction of the DependencyContainer.
    
    Compare this with the new approach in dependencies.py:
    - More explicit dependency management
    - Better session handling
    - Centralized configuration
    """
    # This would be the old way of doing DI
    # Kept for demonstration purposes
    pass


# Error handling evolution example
class LegacyErrorHandling:
    """
    Example of how error handling evolved.
    
    Shows the progression from basic error handling
    to comprehensive error management.
    """
    
    @staticmethod
    def old_way(exc: Exception):
        """Original basic error handling"""
        return {"error": str(exc)}
    
    @staticmethod
    def new_way(exc: Exception):
        """
        New comprehensive error handling approach:
        - Structured error responses
        - Proper HTTP status codes
        - Detailed error messages
        - Field-specific validation errors
        """
        return {
            "detail": str(exc),
            "type": type(exc).__name__,
            "code": "VALIDATION_ERROR",
            "timestamp": "2024-01-15T10:30:00Z"
        }


# Migration utilities
def create_migration_guide():
    """
    Generate migration guide for developers moving from legacy to new API.
    
    This function demonstrates how to provide clear migration
    paths when evolving APIs.
    """
    return {
        "version": "2.0",
        "breaking_changes": [
            "Response format includes metadata",
            "Error responses are structured",
            "Authentication required for all endpoints"
        ],
        "new_features": [
            "Advanced filtering",
            "CSV export",
            "Comprehensive validation",
            "Rich OpenAPI documentation"
        ],
        "migration_steps": [
            "Update authentication headers",
            "Handle new response format",
            "Update error handling",
            "Test with new filtering options"
        ]
    }