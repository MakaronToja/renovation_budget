# renovation_cost_tracker/infrastructure/repositories.py

from uuid import UUID
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional, Iterable

from sqlalchemy import (
    Column,
    String,
    Date,
    DateTime,
    Numeric,
    ForeignKey,
    select,
    delete,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column, relationship

from renovation_cost_tracker.application.repositories import IUserRepository, IProjectRepository, IExpenseRepository
from renovation_cost_tracker.domain.models import User, Project, Expense, Category, Money
from renovation_cost_tracker.infrastructure.db import Base


# SQLAlchemy ORM Models
class UserModel(Base):
    """
    SQLAlchemy ORM model for User entity.
    
    Maps User domain entity to 'users' database table.
    Handles conversion between domain objects and database records.
    """
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    # Relationships
    projects = relationship("ProjectModel", back_populates="user", cascade="all, delete-orphan")

    @classmethod
    def from_entity(cls, user: User) -> "UserModel":
        """Convert User domain entity to ORM model"""
        return cls(
            id=user.id,
            email=user.email,
            password_hash=user.password_hash,
            created_at=user.created_at,
        )

    def to_entity(self) -> User:
        """Convert ORM model to User domain entity"""
        return User(
            id=self.id,
            email=self.email,
            password_hash=self.password_hash,
            created_at=self.created_at,
        )


class ProjectModel(Base):
    """
    SQLAlchemy ORM model for Project entity.
    
    Maps Project domain entity to 'projects' database table.
    Includes budget as separate amount and currency fields.
    """
    __tablename__ = "projects"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    user_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    budget_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    budget_currency: Mapped[str] = mapped_column(String(3), nullable=False, default="PLN")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    # Relationships
    user = relationship("UserModel", back_populates="projects")
    expenses = relationship("ExpenseModel", back_populates="project", cascade="all, delete-orphan")

    @classmethod
    def from_entity(cls, project: Project) -> "ProjectModel":
        """Convert Project domain entity to ORM model"""
        return cls(
            id=project.id,
            user_id=project.user_id,
            name=project.name,
            budget_amount=project.budget.amount,
            budget_currency=project.budget.currency,
            created_at=project.created_at,
        )

    def to_entity(self) -> Project:
        """
        Convert ORM model to Project domain entity.
        
        Note: Expenses are loaded separately to avoid N+1 queries.
        Use load_expenses() method to populate expenses list.
        """
        project = Project(
            id=self.id,
            user_id=self.user_id,
            name=self.name,
            budget=Money(self.budget_amount, self.budget_currency),
            created_at=self.created_at,
        )
        
        # Convert related expenses if loaded
        if hasattr(self, '_expenses_loaded') and self._expenses_loaded:
            project.expenses = [expense.to_entity() for expense in self.expenses]
        
        return project

    def load_expenses(self) -> None:
        """Mark that expenses have been loaded for to_entity() conversion"""
        self._expenses_loaded = True


class ExpenseModel(Base):
    """
    SQLAlchemy ORM model for Expense entity.
    
    Maps Expense domain entity to 'expenses' database table.
    Stores amount and currency separately for proper decimal handling.
    """
    __tablename__ = "expenses"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    project_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    category: Mapped[str] = mapped_column(String, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="PLN")
    vendor: Mapped[str] = mapped_column(String, nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=True)

    # Relationships
    project = relationship("ProjectModel", back_populates="expenses")

    @classmethod
    def from_entity(cls, expense: Expense) -> "ExpenseModel":
        """Convert Expense domain entity to ORM model"""
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
        """Convert ORM model to Expense domain entity"""
        return Expense(
            id=self.id,
            project_id=self.project_id,
            category=Category(self.category),
            amount=Money(amount=self.amount, currency=self.currency),
            vendor=self.vendor,
            date=self.date,
            description=self.description or "",
        )


# Repository Implementations
class PostgresUserRepository(IUserRepository):
    """
    PostgreSQL implementation of User repository.
    
    Handles all database operations for User entities including:
    - Creating and updating users
    - Finding users by ID or email
    - Proper session management
    """
    
    def __init__(self, session_factory):
        self._session_factory = session_factory

    async def save(self, user: User) -> None:
        """
        Save user to database (create or update).
        
        Args:
            user: User entity to save
        """
        async with self._session_factory() as session:  # type: AsyncSession
            # Check if user already exists
            existing = await session.get(UserModel, user.id)
            
            if existing:
                # Update existing user
                existing.email = user.email
                existing.password_hash = user.password_hash
                existing.created_at = user.created_at
            else:
                # Create new user
                orm_obj = UserModel.from_entity(user)
                session.add(orm_obj)
            
            await session.commit()

    async def get(self, id: UUID) -> Optional[User]:
        """
        Get user by ID.
        
        Args:
            id: User's unique identifier
            
        Returns:
            User entity if found, None otherwise
        """
        async with self._session_factory() as session:
            result = await session.get(UserModel, id)
            return result.to_entity() if result else None

    async def find_by_email(self, email: str) -> Optional[User]:
        """
        Find user by email address.
        
        Args:
            email: User's email address
            
        Returns:
            User entity if found, None otherwise
        """
        async with self._session_factory() as session:
            stmt = select(UserModel).where(UserModel.email == email.lower())
            result = await session.scalar(stmt)
            return result.to_entity() if result else None


class PostgresProjectRepository(IProjectRepository):
    """
    PostgreSQL implementation of Project repository.
    
    Handles all database operations for Project entities including:
    - Creating and updating projects
    - Loading projects with their expenses
    - Listing projects by user
    """
    
    def __init__(self, session_factory):
        self._session_factory = session_factory

    async def save(self, project: Project) -> None:
        """
        Save project to database (create or update).
        
        Args:
            project: Project entity to save
            
        Note: This method also saves associated expenses that are new.
        """
        async with self._session_factory() as session:  # type: AsyncSession
            # Check if project already exists
            existing = await session.get(ProjectModel, project.id)
            
            if existing:
                # Update existing project
                existing.name = project.name
                existing.budget_amount = project.budget.amount
                existing.budget_currency = project.budget.currency
                existing.created_at = project.created_at
            else:
                # Create new project
                orm_obj = ProjectModel.from_entity(project)
                session.add(orm_obj)
            
            # Save new expenses (if any)
            for expense in project.expenses:
                existing_expense = await session.get(ExpenseModel, expense.id)
                if not existing_expense:
                    expense_orm = ExpenseModel.from_entity(expense)
                    session.add(expense_orm)
            
            await session.commit()

    async def get(self, id: UUID) -> Optional[Project]:
        """
        Get project by ID with all associated expenses.
        
        Args:
            id: Project's unique identifier
            
        Returns:
            Project entity with expenses if found, None otherwise
        """
        async with self._session_factory() as session:
            # Load project with expenses in a single query
            stmt = (
                select(ProjectModel)
                .where(ProjectModel.id == id)
            )
            result = await session.scalar(stmt)
            
            if not result:
                return None
            
            # Load expenses separately to avoid lazy loading issues
            expenses_stmt = select(ExpenseModel).where(ExpenseModel.project_id == id)
            expenses_result = await session.scalars(expenses_stmt)
            result.expenses = list(expenses_result)
            result.load_expenses()
            
            return result.to_entity()

    async def list_by_user(self, user_id: UUID) -> Iterable[Project]:
        """
        Get all projects belonging to a user.
        
        Args:
            user_id: User's unique identifier
            
        Returns:
            Iterable of Project entities (may be empty)
        """
        async with self._session_factory() as session:
            stmt = select(ProjectModel).where(ProjectModel.user_id == user_id)
            rows = await session.scalars(stmt)
            
            projects = []
            for row in rows:
                # Load expenses for each project
                expenses_stmt = select(ExpenseModel).where(ExpenseModel.project_id == row.id)
                expenses_result = await session.scalars(expenses_stmt)
                row.expenses = list(expenses_result)
                row.load_expenses()
                
                projects.append(row.to_entity())
            
            return projects


class PostgresExpenseRepository(IExpenseRepository):
    """
    PostgreSQL implementation of Expense repository.
    
    Handles all database operations for Expense entities including:
    - Creating, updating, and deleting expenses
    - Listing expenses by project
    - Efficient querying with proper indexing
    """
    
    def __init__(self, session_factory):
        self._session_factory = session_factory

    async def save(self, expense: Expense) -> None:
        """
        Save expense to database (create or update).
        
        Args:
            expense: Expense entity to save
        """
        async with self._session_factory() as session:  # type: AsyncSession
            # Check if expense already exists
            existing = await session.get(ExpenseModel, expense.id)
            
            if existing:
                # Update existing expense
                existing.project_id = expense.project_id
                existing.category = expense.category.value
                existing.amount = expense.amount.amount
                existing.currency = expense.amount.currency
                existing.vendor = expense.vendor
                existing.date = expense.date
                existing.description = expense.description
            else:
                # Create new expense
                orm_obj = ExpenseModel.from_entity(expense)
                session.add(orm_obj)
            
            await session.commit()

    async def get(self, id: UUID) -> Optional[Expense]:
        """
        Get expense by ID.
        
        Args:
            id: Expense's unique identifier
            
        Returns:
            Expense entity if found, None otherwise
        """
        async with self._session_factory() as session:
            result = await session.get(ExpenseModel, id)
            return result.to_entity() if result else None

    async def list_by_project(self, project_id: UUID) -> Iterable[Expense]:
        """
        Get all expenses for a project.
        
        Args:
            project_id: Project's unique identifier
            
        Returns:
            Iterable of Expense entities (may be empty)
        """
        async with self._session_factory() as session:
            stmt = select(ExpenseModel).where(ExpenseModel.project_id == project_id)
            rows = await session.scalars(stmt)
            return [row.to_entity() for row in rows]

    async def delete(self, id: UUID) -> None:
        """
        Delete expense by ID.
        
        Args:
            id: Expense's unique identifier
            
        Note: This method doesn't raise an error if expense doesn't exist.
        """
        async with self._session_factory() as session:
            stmt = delete(ExpenseModel).where(ExpenseModel.id == id)
            await session.execute(stmt)
            await session.commit()


# Additional utility functions for repository management
async def create_database_indexes(engine):
    """
    Create additional database indexes for performance.
    
    This function creates indexes that are not part of the basic
    table definitions but improve query performance.
    """
    async with engine.begin() as conn:
        # Index on expenses by project_id and date for efficient filtering
        await conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_expenses_project_date "
            "ON expenses (project_id, date DESC)"
        )
        
        # Index on expenses by category for filtering
        await conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_expenses_category "
            "ON expenses (category)"
        )
        
        # Index on users by email for login performance
        await conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_users_email "
            "ON users (email)"
        )


async def verify_database_schema(engine):
    """
    Verify that database schema matches expected structure.
    
    This function can be used in health checks or startup
    to ensure database is properly configured.
    """
    async with engine.begin() as conn:
        # Check if all required tables exist
        result = await conn.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'public' "
            "AND table_name IN ('users', 'projects', 'expenses')"
        )
        
        tables = [row[0] for row in result.fetchall()]
        expected_tables = {'users', 'projects', 'expenses'}
        
        if not expected_tables.issubset(set(tables)):
            missing = expected_tables - set(tables)
            raise Exception(f"Missing database tables: {missing}")
        
        return True