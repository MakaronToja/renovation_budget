from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, date
from decimal import Decimal
from enum import StrEnum
from uuid import UUID, uuid4


class Category(StrEnum):
    MATERIAL = "MATERIAL"
    LABOR = "LABOR"
    PERMIT = "PERMIT"
    OTHER = "OTHER"


@dataclass(frozen=True, slots=True)
class Money:
    amount: Decimal
    currency: str = "PLN"

    def __add__(self, other: "Money") -> "Money":
        assert self.currency == other.currency
        return Money(self.amount + other.amount, self.currency)

    def __sub__(self, other: "Money") -> "Money":
        assert self.currency == other.currency
        return Money(self.amount - other.amount, self.currency)


@dataclass(slots=True)
class Expense:
    id: UUID
    project_id: UUID
    category: Category
    amount: Money
    vendor: str
    date: date
    description: str = ""


@dataclass(slots=True)
class Project:
    id: UUID
    user_id: UUID
    name: str
    budget: Money
    created_at: datetime
    expenses: list[Expense] = field(default_factory=list)

    # --- logika domenowa ---
    @property
    def total_cost(self) -> Money:
        total = Money(Decimal("0"), self.budget.currency)
        for e in self.expenses:
            total += e.amount
        return total

    def remaining_budget(self) -> Money:
        return self.budget - self.total_cost

    def add_expense(self, expense: Expense) -> None:
        self.expenses.append(expense)


@dataclass(slots=True)
class User:
    id: UUID
    email: str
    password_hash: str
    created_at: datetime
