from datetime import date as date_type
from decimal import Decimal
from enum import Enum
from uuid import UUID
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


class ExpenseCategory(str, Enum):
    """Expense category enumeration for API schemas."""
    MATERIAL = "MATERIAL"
    LABOR = "LABOR"
    PERMIT = "PERMIT"
    OTHER = "OTHER"


class MoneySchema(BaseModel):
    """Money value object schema for API responses"""
    amount: Decimal
    currency: str = "PLN"


# === EXPENSE SCHEMAS ===
class ExpenseCreate(BaseModel):
    """Schema for creating new expenses."""
    amount: Decimal = Field(..., gt=0)
    category: ExpenseCategory
    vendor: str = Field(..., min_length=1, max_length=255)
    date: date_type
    description: Optional[str] = Field(None, max_length=500)
    
    @field_validator('date')
    @classmethod
    def validate_date_not_future(cls, v):
        if v > date_type.today():
            raise ValueError('Expense date cannot be in the future')
        return v
    
    @field_validator('vendor')
    @classmethod
    def validate_vendor_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('Vendor name cannot be empty')
        return v.strip()


class ExpenseUpdate(BaseModel):
    """Schema for updating existing expenses."""
    amount: Optional[Decimal] = Field(None, gt=0)
    category: Optional[ExpenseCategory] = None
    vendor: Optional[str] = Field(None, min_length=1, max_length=255)
    date: Optional[date_type] = None
    description: Optional[str] = Field(None, max_length=500)
    
    @field_validator('date')
    @classmethod
    def validate_date_not_future(cls, v):
        if v is not None and v > date_type.today():
            raise ValueError('Expense date cannot be in the future')
        return v


class ExpenseOut(BaseModel):
    """Schema for expense responses."""
    id: UUID
    amount: Decimal
    category: ExpenseCategory
    vendor: str
    date: date_type
    description: Optional[str] = None


# === USER SCHEMAS ===
class UserCreate(BaseModel):
    """Schema for user registration."""
    email: EmailStr
    password: str = Field(..., min_length=8)
    
    @field_validator('password')
    @classmethod
    def validate_password_strength(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        return v


class UserOut(BaseModel):
    """Schema for user responses."""
    id: UUID
    email: EmailStr
    created_at: str


# === PROJECT SCHEMAS ===
class ProjectCreate(BaseModel):
    """Schema for creating new projects."""
    name: str = Field(..., min_length=1, max_length=255)
    budget: Decimal = Field(..., gt=0)
    currency: str = Field(default="PLN", min_length=3, max_length=3)
    
    @field_validator('name')
    @classmethod
    def validate_name_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('Project name cannot be empty')
        return v.strip()
    
    @field_validator('currency')
    @classmethod
    def validate_currency_code(cls, v):
        if len(v) != 3:
            raise ValueError('Currency code must be 3 characters long')
        return v.upper()


class ProjectOut(BaseModel):
    """Schema for project responses."""
    id: UUID
    name: str
    budget: MoneySchema
    created_at: str
    total_cost: MoneySchema
    remaining_budget: MoneySchema
    expense_count: int = 0


# === TOKEN SCHEMA ===
class Token(BaseModel):
    """JWT token response schema"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: dict  # Simplified to avoid circular reference