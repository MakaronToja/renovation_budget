from datetime import datetime, date
from decimal import Decimal
from uuid import UUID, uuid4
from typing import Optional

from passlib.hash import bcrypt

from renovation_cost_tracker.domain.models import (
    User, Project, Expense, Money, Category
)
from renovation_cost_tracker.application.repositories import (
    IUserRepository, IProjectRepository, IExpenseRepository
)


class AuthService:
    def __init__(self, users: IUserRepository):
        self._users = users

    def register(self, email: str, password: str) -> User:
        if self._users.find_by_email(email):
            raise ValueError("E-mail already used")
        user = User(
            id=uuid4(),
            email=email,
            password_hash=bcrypt.hash(password),
            created_at=datetime.utcnow(),
        )
        self._users.save(user)
        return user

    def login(self, email: str, password: str) -> User:
        user = self._users.find_by_email(email)
        if not user or not bcrypt.verify(password, user.password_hash):
            raise ValueError("Bad credentials")
        return user

    def get_user(self, user_id: UUID) -> User:
        user = self._users.get(user_id)
        if not user:
            raise ValueError("User not found")
        return user


class ExpenseService:
    def __init__(self,
                 projects: IProjectRepository,
                 expenses: IExpenseRepository):
        self._projects = projects
        self._expenses = expenses

    def record_expense(self,
                       project_id: UUID,
                       *,
                       amount: Decimal,
                       category: Category,
                       vendor: str,
                       date: date,
                       description: str = "") -> UUID:
        project = self._projects.get(project_id)
        if not project:
            raise ValueError("Project not found")

        expense = Expense(
            id=uuid4(),
            project_id=project_id,
            category=category,
            amount=Money(amount),
            vendor=vendor,
            date=date,
            description=description,
        )

        project.add_expense(expense)
        self._expenses.save(expense)
        self._projects.save(project)
        return expense.id

    def list_expenses(self, project_id: UUID, category_filter: Optional[Category] = None) -> list[Expense]:
        expenses = list(self._expenses.list_by_project(project_id))
        if category_filter:
            expenses = [e for e in expenses if e.category == category_filter]
        return expenses

    def get_expense(self, expense_id: UUID) -> Expense:
        expense = self._expenses.get(expense_id)
        if not expense:
            raise ValueError("Expense not found")
        return expense

    def update_expense(self, expense_id: UUID, **kwargs) -> None:
        expense = self.get_expense(expense_id)
        for key, value in kwargs.items():
            if hasattr(expense, key):
                setattr(expense, key, value)
        self._expenses.save(expense)

    def delete_expense(self, expense_id: UUID) -> None:
        expense = self.get_expense(expense_id)
        self._expenses.delete(expense_id)

    def summarize(self, project_id: UUID) -> dict:
        project = self._projects.get(project_id)
        if not project:
            raise ValueError("Project not found")
        
        expenses = self.list_expenses(project_id)
        total_by_category = {}
        for expense in expenses:
            if expense.category not in total_by_category:
                total_by_category[expense.category] = Money(Decimal("0"))
            total_by_category[expense.category] += expense.amount
        
        return {
            "total_cost": project.total_cost,
            "budget": project.budget,
            "remaining_budget": project.remaining_budget(),
            "by_category": total_by_category,
            "expense_count": len(expenses)
        }


class ProjectService:
    def __init__(self, projects: IProjectRepository):
        self._projects = projects

    def create_project(self, user_id: UUID, name: str, budget: Decimal) -> UUID:
        project = Project(
            id=uuid4(),
            user_id=user_id,
            name=name,
            budget=Money(budget),
            created_at=datetime.utcnow(),
        )
        self._projects.save(project)
        return project.id

    def get_project(self, project_id: UUID) -> Project:
        project = self._projects.get(project_id)
        if not project:
            raise ValueError("Project not found")
        return project

    def list_user_projects(self, user_id: UUID) -> list[Project]:
        return list(self._projects.list_by_user(user_id))
