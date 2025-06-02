from datetime import date
from decimal import Decimal
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, EmailStr

from renovation_cost_tracker.domain.models import Expense, Category as DomainCategory


class Category(str, Enum):
    MATERIAL = "MATERIAL"
    LABOR = "LABOR"
    PERMIT = "PERMIT"
    OTHER = "OTHER"


class ExpenseCreate(BaseModel):
    amount: Decimal
    category: Category
    vendor: str
    date: date
    description: str | None = None


class ExpenseDTO(BaseModel):
    id: UUID
    category: str
    amount: float
    vendor: str
    date: date
    description: str

    class Config:
        from_attributes = True


class ExpenseOut(ExpenseCreate):
    id: UUID


class Mapper:
    @staticmethod
    def to_expense_dto(expense: Expense) -> ExpenseDTO:
        return ExpenseDTO(
            id=expense.id,
            category=expense.category.value,
            amount=float(expense.amount.amount),
            vendor=expense.vendor,
            date=expense.date,
            description=expense.description,
        )

    @staticmethod
    def to_expense(dto: ExpenseDTO) -> Expense:
        from renovation_cost_tracker.domain.models import Money
        return Expense(
            id=dto.id,
            project_id=UUID('00000000-0000-0000-0000-000000000000'),  # placeholder
            category=DomainCategory(dto.category),
            amount=Money(Decimal(str(dto.amount))),
            vendor=dto.vendor,
            date=dto.date,
            description=dto.description,
        )
