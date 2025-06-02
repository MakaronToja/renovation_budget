# renovation_cost_tracker/infrastructure/repositories.py

from uuid import UUID
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Column,
    String,
    Date,
    DateTime,
    Numeric,
    ForeignKey,
    Table,
    select,
    delete,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column, relationship

from renovation_cost_tracker.application.repositories import IUserRepository, IProjectRepository, IExpenseRepository
from renovation_cost_tracker.domain.models import User, Project, Expense, Category, Money
from renovation_cost_tracker.infrastructure.db import Base


class ExpenseModel(Base):
    __tablename__ = "expenses"

    # kolumny
    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=UUID
    )
    project_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False
    )
    category: Mapped[str] = mapped_column(String, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="PLN")
    vendor: Mapped[str] = mapped_column(String, nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=True)

    project = relationship("ProjectModel", back_populates="expenses")

    @classmethod
    def from_entity(cls, expense: Expense) -> "ExpenseModel":
        return cls(
            id=expense.id,
            project_id=expense.project_id,
            category=expense.category.value,
            amount=expense.amount.amount,
            currency=expense.amount.currency,
            vendor=expense.vendor,
            date=expense.date,
            description=expense.description,
        )

    def to_entity(self) -> Expense:
        return Expense(
            id=self.id,
            project_id=self.project_id,
            category=Category(self.category),
            amount=Money(amount=self.amount, currency=self.currency),
            vendor=self.vendor,
            date=self.date,
            description=self.description or "",
        )


class PostgresExpenseRepository(IExpenseRepository):
    def __init__(self, session_factory):
        self._session_factory = session_factory

    async def save(self, expense: Expense) -> None:
        async with self._session_factory() as session:  # type: AsyncSession
            orm_obj = ExpenseModel.from_entity(expense)
            session.add(orm_obj)
            await session.commit()

    async def get(self, id: UUID) -> Expense | None:
        async with self._session_factory() as session:
            result = await session.get(ExpenseModel, id)
            return result.to_entity() if result else None

    async def list_by_project(self, project_id: UUID) -> list[Expense]:
        async with self._session_factory() as session:
            stmt = select(ExpenseModel).where(ExpenseModel.project_id == project_id)
            rows = await session.scalars(stmt)
            return [row.to_entity() for row in rows]

    async def delete(self, id: UUID) -> None:
        async with self._session_factory() as session:
            stmt = delete(ExpenseModel).where(ExpenseModel.id == id)
            await session.execute(stmt)
            await session.commit()


class UserModel(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    projects = relationship("ProjectModel", back_populates="user")

    @classmethod
    def from_entity(cls, user: User) -> "UserModel":
        return cls(
            id=user.id,
            email=user.email,
            password_hash=user.password_hash,
            created_at=user.created_at,
        )

    def to_entity(self) -> User:
        return User(
            id=self.id,
            email=self.email,
            password_hash=self.password_hash,
            created_at=self.created_at,
        )


class ProjectModel(Base):
    __tablename__ = "projects"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    user_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    budget_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    budget_currency: Mapped[str] = mapped_column(String(3), nullable=False, default="PLN")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    user = relationship("UserModel", back_populates="projects")
    expenses = relationship("ExpenseModel", back_populates="project")

    @classmethod
    def from_entity(cls, project: Project) -> "ProjectModel":
        return cls(
            id=project.id,
            user_id=project.user_id,
            name=project.name,
            budget_amount=project.budget.amount,
            budget_currency=project.budget.currency,
            created_at=project.created_at,
        )

    def to_entity(self) -> Project:
        return Project(
            id=self.id,
            user_id=self.user_id,
            name=self.name,
            budget=Money(self.budget_amount, self.budget_currency),
            created_at=self.created_at,
        )


class PostgresUserRepository(IUserRepository):
    def __init__(self, session_factory):
        self._session_factory = session_factory

    async def save(self, user: User) -> None:
        async with self._session_factory() as session:
            orm_obj = UserModel.from_entity(user)
            session.add(orm_obj)
            await session.commit()

    async def get(self, id: UUID) -> User | None:
        async with self._session_factory() as session:
            result = await session.get(UserModel, id)
            return result.to_entity() if result else None

    async def find_by_email(self, email: str) -> User | None:
        async with self._session_factory() as session:
            stmt = select(UserModel).where(UserModel.email == email)
            result = await session.scalar(stmt)
            return result.to_entity() if result else None


class PostgresProjectRepository(IProjectRepository):
    def __init__(self, session_factory):
        self._session_factory = session_factory

    async def save(self, project: Project) -> None:
        async with self._session_factory() as session:
            orm_obj = ProjectModel.from_entity(project)
            session.add(orm_obj)
            await session.commit()

    async def get(self, id: UUID) -> Project | None:
        async with self._session_factory() as session:
            result = await session.get(ProjectModel, id)
            return result.to_entity() if result else None

    async def list_by_user(self, user_id: UUID) -> list[Project]:
        async with self._session_factory() as session:
            stmt = select(ProjectModel).where(ProjectModel.user_id == user_id)
            rows = await session.scalars(stmt)
            return [row.to_entity() for row in rows]
