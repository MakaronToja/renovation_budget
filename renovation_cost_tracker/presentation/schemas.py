from datetime import date
from decimal import Decimal
from enum import Enum
from uuid import UUID
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, validator

from renovation_cost_tracker.domain.models import Expense, Category as DomainCategory


class ExpenseCategory(str, Enum):
    """
    Expense category enumeration for API schemas.
    
    Mirrors the domain Category enum but as string enum
    for proper OpenAPI documentation and JSON serialization.
    """
    MATERIAL = "MATERIAL"
    LABOR = "LABOR"
    PERMIT = "PERMIT"
    OTHER = "OTHER"


# Base schemas for common patterns
class TimestampMixin(BaseModel):
    """Mixin for models with timestamp fields"""
    created_at: Optional[str] = Field(None, description="Creation timestamp in ISO format")
    

class MoneySchema(BaseModel):
    """Money value object schema for API responses"""
    amount: Decimal = Field(..., description="Amount in decimal format", example=1500.50)
    currency: str = Field(default="PLN", description="Currency code", example="PLN")
    
    class Config:
        json_schema_extra = {
            "example": {
                "amount": 1500.50,
                "currency": "PLN"
            }
        }


# Expense schemas
class ExpenseBase(BaseModel):
    """Base expense schema with common fields"""
    amount: Decimal = Field(..., gt=0, description="Expense amount (must be positive)", example=1500.50)
    category: ExpenseCategory = Field(..., description="Expense category", example=ExpenseCategory.MATERIAL)
    vendor: str = Field(..., min_length=1, max_length=255, description="Vendor or supplier name", example="BuildMart")
    date: date = Field(..., description="Expense date", example="2024-01-15")
    description: Optional[str] = Field(None, max_length=500, description="Optional expense description", example="Bathroom tiles and fixtures")
    
    @validator('date')
    def validate_date_not_future(cls, v):
        """Ensure expense date is not in the future"""
        if v > date.today():
            raise ValueError('Expense date cannot be in the future')
        return v
    
    @validator('vendor')
    def validate_vendor_not_empty(cls, v):
        """Ensure vendor name is not empty or just whitespace"""
        if not v or not v.strip():
            raise ValueError('Vendor name cannot be empty')
        return v.strip()
    
    @validator('description')
    def validate_description(cls, v):
        """Clean up description field"""
        if v is not None:
            return v.strip()
        return v


class ExpenseCreate(ExpenseBase):
    """
    Schema for creating new expenses.
    
    Inherits all validation from ExpenseBase.
    Used in POST /projects/{id}/expenses endpoint.
    """
    
    class Config:
        json_schema_extra = {
            "example": {
                "amount": 1500.50,
                "category": "MATERIAL",
                "vendor": "BuildMart",
                "date": "2024-01-15",
                "description": "Bathroom tiles and ceramic fixtures"
            }
        }


class ExpenseUpdate(BaseModel):
    """
    Schema for updating existing expenses.
    
    All fields are optional to support partial updates.
    Used in PUT /expenses/{id} endpoint.
    """
    amount: Optional[Decimal] = Field(None, gt=0, description="New expense amount")
    category: Optional[ExpenseCategory] = Field(None, description="New expense category")
    vendor: Optional[str] = Field(None, min_length=1, max_length=255, description="New vendor name")
    date: Optional[date] = Field(None, description="New expense date")
    description: Optional[str] = Field(None, max_length=500, description="New expense description")
    
    @validator('date')
    def validate_date_not_future(cls, v):
        """Ensure expense date is not in the future"""
        if v is not None and v > date.today():
            raise ValueError('Expense date cannot be in the future')
        return v
    
    @validator('vendor')
    def validate_vendor_not_empty(cls, v):
        """Ensure vendor name is not empty or just whitespace"""
        if v is not None and (not v or not v.strip()):
            raise ValueError('Vendor name cannot be empty')
        return v.strip() if v else v
    
    @validator('description')
    def validate_description(cls, v):
        """Clean up description field"""
        if v is not None:
            return v.strip()
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "amount": 1750.00,
                "vendor": "Updated BuildMart",
                "description": "Updated: Premium bathroom tiles and fixtures"
            }
        }


class ExpenseOut(ExpenseBase):
    """
    Schema for expense responses.
    
    Includes the expense ID and maintains all base fields.
    Used in all expense response endpoints.
    """
    id: UUID = Field(..., description="Unique expense identifier")
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "amount": 1500.50,
                "category": "MATERIAL",
                "vendor": "BuildMart",
                "date": "2024-01-15",
                "description": "Bathroom tiles and ceramic fixtures"
            }
        }


class ExpenseDTO(BaseModel):
    """
    Data Transfer Object for internal expense operations.
    
    Used for complex operations and data transformations.
    Includes additional metadata fields.
    """
    id: UUID
    project_id: UUID
    category: str
    amount: float  # Note: float for DTO, Decimal for API schemas
    currency: str
    vendor: str
    date: date
    description: str
    
    class Config:
        from_attributes = True


# User schemas  
class UserBase(BaseModel):
    """Base user schema with common fields"""
    email: EmailStr = Field(..., description="User's email address", example="user@example.com")


class UserCreate(UserBase):
    """
    Schema for user registration.
    
    Includes password field with validation.
    """
    password: str = Field(..., min_length=8, description="Password (minimum 8 characters)", example="strongpassword123")
    
    @validator('password')
    def validate_password_strength(cls, v):
        """Basic password strength validation"""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "email": "user@example.com",
                "password": "strongpassword123"
            }
        }


class UserOut(UserBase):
    """
    Schema for user responses.
    
    Excludes sensitive information like password hash.
    """
    id: UUID = Field(..., description="Unique user identifier")
    created_at: str = Field(..., description="Account creation timestamp")
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "email": "user@example.com",
                "created_at": "2024-01-15T10:30:00Z"
            }
        }


# Project schemas
class ProjectBase(BaseModel):
    """Base project schema with common fields"""
    name: str = Field(..., min_length=1, max_length=255, description="Project name", example="Bathroom Renovation")
    
    @validator('name')
    def validate_name_not_empty(cls, v):
        """Ensure project name is not empty or just whitespace"""
        if not v or not v.strip():
            raise ValueError('Project name cannot be empty')
        return v.strip()


class ProjectCreate(ProjectBase):
    """
    Schema for creating new projects.
    
    Includes budget information with currency support.
    """
    budget: Decimal = Field(..., gt=0, description="Project budget amount", example=15000.00)
    currency: str = Field(default="PLN", description="Budget currency", example="PLN")
    
    @validator('currency')
    def validate_currency_code(cls, v):
        """Basic currency code validation"""
        if len(v) != 3:
            raise ValueError('Currency code must be 3 characters long')
        return v.upper()
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "Kitchen Renovation",
                "budget": 20000.50,
                "currency": "PLN"
            }
        }


class ProjectOut(ProjectBase):
    """
    Schema for project responses.
    
    Includes calculated fields like total cost and remaining budget.
    """
    id: UUID = Field(..., description="Unique project identifier")
    budget: MoneySchema = Field(..., description="Project budget")
    created_at: str = Field(..., description="Project creation timestamp")
    total_cost: MoneySchema = Field(..., description="Total spent amount")
    remaining_budget: MoneySchema = Field(..., description="Remaining budget")
    expense_count: int = Field(default=0, description="Number of expenses")
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "name": "Kitchen Renovation",
                "budget": {"amount": 20000.50, "currency": "PLN"},
                "created_at": "2024-01-15T10:30:00Z",
                "total_cost": {"amount": 8500.75, "currency": "PLN"},
                "remaining_budget": {"amount": 11499.25, "currency": "PLN"},
                "expense_count": 12
            }
        }


# Token and authentication schemas
class Token(BaseModel):
    """JWT token response schema"""
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration time in seconds")
    user: UserOut = Field(..., description="User information")
    
    class Config:
        json_schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "expires_in": 86400,
                "user": {
                    "id": "123e4567-e89b-12d3-a456-426614174000",
                    "email": "user@example.com",
                    "created_at": "2024-01-15T10:30:00Z"
                }
            }
        }


# Summary and analytics schemas
class CategorySummary(BaseModel):
    """Summary statistics for a specific category"""
    category: ExpenseCategory = Field(..., description="Expense category")
    total_amount: MoneySchema = Field(..., description="Total amount for this category")
    expense_count: int = Field(..., description="Number of expenses in this category")
    percentage: float = Field(..., description="Percentage of total project cost")


class ProjectSummary(BaseModel):
    """
    Comprehensive project financial summary.
    
    Used for detailed project analytics and reporting.
    """
    project_id: UUID = Field(..., description="Project identifier")
    project_name: str = Field(..., description="Project name")
    total_cost: MoneySchema = Field(..., description="Total project cost")
    budget: MoneySchema = Field(..., description="Project budget")
    remaining_budget: MoneySchema = Field(..., description="Remaining budget")
    budget_utilization_percent: float = Field(..., description="Percentage of budget used")
    expense_count: int = Field(..., description="Total number of expenses")
    by_category: list[CategorySummary] = Field(..., description="Breakdown by category")
    
    class Config:
        json_schema_extra = {
            "example": {
                "project_id": "123e4567-e89b-12d3-a456-426614174000",
                "project_name": "Kitchen Renovation",
                "total_cost": {"amount": 8500.75, "currency": "PLN"},
                "budget": {"amount": 15000.00, "currency": "PLN"},
                "remaining_budget": {"amount": 6499.25, "currency": "PLN"},
                "budget_utilization_percent": 56.67,
                "expense_count": 12,
                "by_category": [
                    {
                        "category": "MATERIAL",
                        "total_amount": {"amount": 5500.00, "currency": "PLN"},
                        "expense_count": 8,
                        "percentage": 64.7
                    },
                    {
                        "category": "LABOR",
                        "total_amount": {"amount": 3000.75, "currency": "PLN"},
                        "expense_count": 4,
                        "percentage": 35.3
                    }
                ]
            }
        }


# Utility mapper class
class Mapper:
    """
    Utility class for converting between domain entities and DTOs.
    
    Provides static methods for data transformation operations
    between different layers of the application.
    """
    
    @staticmethod
    def to_expense_dto(expense: Expense) -> ExpenseDTO:
        """Convert Expense domain entity to DTO"""
        return ExpenseDTO(
            id=expense.id,
            project_id=expense.project_id,
            category=expense.category.value,
            amount=float(expense.amount.amount),
            currency=expense.amount.currency,
            vendor=expense.vendor,
            date=expense.date,
            description=expense.description,
        )

    @staticmethod
    def to_expense_out(expense: Expense) -> ExpenseOut:
        """Convert Expense domain entity to API response schema"""
        return ExpenseOut(
            id=expense.id,
            amount=expense.amount.amount,
            category=ExpenseCategory(expense.category.value),
            vendor=expense.vendor,
            date=expense.date,
            description=expense.description
        )

    @staticmethod
    def expense_dto_to_domain(dto: ExpenseDTO, project_id: UUID = None) -> Expense:
        """Convert ExpenseDTO to domain entity"""
        from renovation_cost_tracker.domain.models import Money
        
        return Expense(
            id=dto.id,
            project_id=project_id or dto.project_id,
            category=DomainCategory(dto.category),
            amount=Money(Decimal(str(dto.amount)), dto.currency),
            vendor=dto.vendor,
            date=dto.date,
            description=dto.description,
        )


# Error response schemas
class ErrorDetail(BaseModel):
    """Standard error detail schema"""
    detail: str = Field(..., description="Error message")
    code: Optional[str] = Field(None, description="Error code")
    field: Optional[str] = Field(None, description="Field that caused the error")


class ValidationError(BaseModel):
    """Validation error response schema"""
    detail: str = Field(..., description="Error message")
    errors: list[ErrorDetail] = Field(..., description="List of validation errors")
    
    class Config:
        json_schema_extra = {
            "example": {
                "detail": "Validation failed",
                "errors": [
                    {
                        "detail": "Amount must be positive",
                        "field": "amount"
                    },
                    {
                        "detail": "Vendor name cannot be empty",
                        "field": "vendor"
                    }
                ]
            }
        }