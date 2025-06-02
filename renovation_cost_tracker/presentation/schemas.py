from datetime import date
from decimal import Decimal
from enum import Enum
from uuid import UUID
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator

from renovation_cost_tracker.domain.models import Category as DomainCategory


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
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "amount": 1500.50,
                "currency": "PLN"
            }
        }
    }


# Expense schemas
class ExpenseBase(BaseModel):
    """Base expense schema with common fields"""
    amount: Decimal = Field(..., gt=0, description="Expense amount (must be positive)", example=1500.50)
    category: ExpenseCategory = Field(..., description="Expense category", example=ExpenseCategory.MATERIAL)
    vendor: str = Field(..., min_length=1, max_length=255, description="Vendor or supplier name", example="BuildMart")
    expense_date: date = Field(..., description="Expense date", example="2024-01-15", alias="date")
    description: Optional[str] = Field(None, max_length=500, description="Optional expense description", example="Bathroom tiles and fixtures")
    
    @field_validator('expense_date')
    @classmethod
    def validate_date_not_future(cls, v):
        """Ensure expense date is not in the future"""
        if v > date.today():
            raise ValueError('Expense date cannot be in the future')
        return v
    
    @field_validator('vendor')
    @classmethod
    def validate_vendor_not_empty(cls, v):
        """Ensure vendor name is not empty or just whitespace"""
        if not v or not v.strip():
            raise ValueError('Vendor name cannot be empty')
        return v.strip()
    
    @field_validator('description')
    @classmethod
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
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "amount": 1500.50,
                "category": "MATERIAL",
                "vendor": "BuildMart",
                "date": "2024-01-15",
                "description": "Bathroom tiles and ceramic fixtures"
            }
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
    expense_date: Optional[date] = Field(None, description="New expense date", alias="date")
    description: Optional[str] = Field(None, max_length=500, description="New expense description")
    
    @field_validator('expense_date')
    @classmethod
    def validate_date_not_future(cls, v):
        """Ensure expense date is not in the future"""
        if v is not None and v > date.today():
            raise ValueError('Expense date cannot be in the future')
        return v
    
    @field_validator('vendor')
    @classmethod
    def validate_vendor_not_empty(cls, v):
        """Ensure vendor name is not empty or just whitespace"""
        if v is not None and (not v or not v.strip()):
            raise ValueError('Vendor name cannot be empty')
        return v.strip() if v else v
    
    @field_validator('description')
    @classmethod
    def validate_description(cls, v):
        """Clean up description field"""
        if v is not None:
            return v.strip()
        return v
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "amount": 1750.00,
                "vendor": "Updated BuildMart",
                "description": "Updated: Premium bathroom tiles and fixtures"
            }
        }
    }


class ExpenseOut(ExpenseBase):
    """
    Schema for expense responses.
    
    Includes the expense ID and maintains all base fields.
    Used in all expense response endpoints.
    """
    id: UUID = Field(..., description="Unique expense identifier")
    
    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "amount": 1500.50,
                "category": "MATERIAL",
                "vendor": "BuildMart",
                "date": "2024-01-15",
                "description": "Bathroom tiles and ceramic fixtures"
            }
        }
    }


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
    
    @field_validator('password')
    @classmethod
    def validate_password_strength(cls, v):
        """Basic password strength validation"""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        return v
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "email": "user@example.com",
                "password": "strongpassword123"
            }
        }
    }


class UserOut(UserBase):
    """
    Schema for user responses.
    
    Excludes sensitive information like password hash.
    """
    id: UUID = Field(..., description="Unique user identifier")
    created_at: str = Field(..., description="Account creation timestamp")
    
    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "email": "user@example.com",
                "created_at": "2024-01-15T10:30:00Z"
            }
        }
    }


# Project schemas
class ProjectBase(BaseModel):
    """Base project schema with common fields"""
    name: str = Field(..., min_length=1, max_length=255, description="Project name", example="Bathroom Renovation")
    
    @field_validator('name')
    @classmethod
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
    
    @field_validator('currency')
    @classmethod
    def validate_currency_code(cls, v):
        """Basic currency code validation"""
        if len(v) != 3:
            raise ValueError('Currency code must be 3 characters long')
        return v.upper()
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "Kitchen Renovation",
                "budget": 20000.50,
                "currency": "PLN"
            }
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
    
    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
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
    }


# Token and authentication schemas
class Token(BaseModel):
    """JWT token response schema"""
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration time in seconds")
    user: UserOut = Field(..., description="User information")
    
    model_config = {
        "json_schema_extra": {
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
    }