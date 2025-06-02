from datetime import datetime, date
from decimal import Decimal
from uuid import UUID, uuid4
from typing import Optional, List

from passlib.hash import bcrypt

from renovation_cost_tracker.domain.models import (
    User, Project, Expense, Money, Category
)
from renovation_cost_tracker.application.repositories import (
    IUserRepository, IProjectRepository, IExpenseRepository
)


class AuthService:
    """
    Authentication service handling user registration and login.
    
    This service is responsible for:
    - User registration with email validation
    - User authentication and password verification
    - User retrieval by ID
    
    Business Rules:
    - Email must be unique across all users
    - Password is hashed using bcrypt
    - Minimum password length is enforced at API level
    """
    
    def __init__(self, users: IUserRepository):
        self._users = users

    async def register(self, email: str, password: str) -> User:
        """
        Register a new user.
        
        Args:
            email: User's email address (must be unique)
            password: Plain text password (will be hashed)
            
        Returns:
            Created User entity
            
        Raises:
            ValueError: If email already exists
        """
        # Check if email already exists
        existing_user = await self._users.find_by_email(email)
        if existing_user:
            raise ValueError("E-mail already used")
        
        # Create new user with hashed password
        user = User(
            id=uuid4(),
            email=email.lower().strip(),  # Normalize email
            password_hash=bcrypt.hash(password),
            created_at=datetime.utcnow(),
        )
        
        await self._users.save(user)
        return user

    async def login(self, email: str, password: str) -> User:
        """
        Authenticate user with email and password.
        
        Args:
            email: User's email address
            password: Plain text password
            
        Returns:
            Authenticated User entity
            
        Raises:
            ValueError: If credentials are invalid
        """
        user = await self._users.find_by_email(email.lower().strip())
        if not user or not bcrypt.verify(password, user.password_hash):
            raise ValueError("Bad credentials")
        
        return user

    async def get_user(self, user_id: UUID) -> User:
        """
        Get user by ID.
        
        Args:
            user_id: User's unique identifier
            
        Returns:
            User entity
            
        Raises:
            ValueError: If user not found
        """
        user = await self._users.get(user_id)
        if not user:
            raise ValueError("User not found")
        return user


class ProjectService:
    """
    Project service handling project management operations.
    
    This service is responsible for:
    - Creating new renovation projects
    - Retrieving project details
    - Listing user's projects
    
    Business Rules:
    - Project name should be unique per user (recommendation)
    - Budget must be positive
    - Each project belongs to exactly one user
    """
    
    def __init__(self, projects: IProjectRepository):
        self._projects = projects

    async def create_project(self, user_id: UUID, name: str, budget: Decimal, currency: str = "PLN") -> UUID:
        """
        Create a new renovation project.
        
        Args:
            user_id: Owner of the project
            name: Project name
            budget: Project budget amount
            currency: Budget currency (default: PLN)
            
        Returns:
            Created project ID
            
        Raises:
            ValueError: If budget is not positive or name is empty
        """
        # Validate input
        if not name or not name.strip():
            raise ValueError("Project name cannot be empty")
        
        if budget <= 0:
            raise ValueError("Budget must be positive")
        
        # Create project
        project = Project(
            id=uuid4(),
            user_id=user_id,
            name=name.strip(),
            budget=Money(budget, currency),
            created_at=datetime.utcnow(),
        )
        
        await self._projects.save(project)
        return project.id

    async def get_project(self, project_id: UUID) -> Project:
        """
        Get project by ID.
        
        Args:
            project_id: Project's unique identifier
            
        Returns:
            Project entity with all expenses loaded
            
        Raises:
            ValueError: If project not found
        """
        project = await self._projects.get(project_id)
        if not project:
            raise ValueError("Project not found")
        return project

    async def list_user_projects(self, user_id: UUID) -> List[Project]:
        """
        Get all projects belonging to a user.
        
        Args:
            user_id: User's unique identifier
            
        Returns:
            List of user's projects (may be empty)
        """
        projects = await self._projects.list_by_user(user_id)
        return list(projects)


class ExpenseService:
    """
    Expense service handling expense management operations.
    
    This service is responsible for:
    - Recording new expenses
    - Listing and filtering expenses
    - Updating and deleting expenses
    - Generating project summaries
    
    Business Rules:
    - Expense amount must be positive
    - Expense date cannot be in the future
    - All expenses must belong to an existing project
    - Project budget tracking is automatic
    """
    
    def __init__(self, projects: IProjectRepository, expenses: IExpenseRepository):
        self._projects = projects
        self._expenses = expenses

    async def record_expense(self,
                           project_id: UUID,
                           *,
                           amount: Decimal,
                           category: Category,
                           vendor: str,
                           date: date,
                           description: str = "") -> UUID:
        """
        Record a new expense for a project.
        
        Args:
            project_id: Project to add expense to
            amount: Expense amount (must be positive)
            category: Expense category (MATERIAL, LABOR, PERMIT, OTHER)
            vendor: Vendor/supplier name
            date: Expense date (cannot be in future)
            description: Optional expense description
            
        Returns:
            Created expense ID
            
        Raises:
            ValueError: If project not found, amount invalid, or date in future
        """
        # Validate project exists
        project = await self._projects.get(project_id)
        if not project:
            raise ValueError("Project not found")
        
        # Validate expense data
        if amount <= 0:
            raise ValueError("Expense amount must be positive")
        
        if date > date.today():
            raise ValueError("Expense date cannot be in the future")
        
        if not vendor or not vendor.strip():
            raise ValueError("Vendor name is required")
        
        # Create expense
        expense = Expense(
            id=uuid4(),
            project_id=project_id,
            category=category,
            amount=Money(amount, project.budget.currency),  # Use project currency
            vendor=vendor.strip(),
            date=date,
            description=description.strip() if description else "",
        )

        # Add to project and save both
        project.add_expense(expense)
        await self._expenses.save(expense)
        await self._projects.save(project)
        
        return expense.id

    async def list_expenses(self, project_id: UUID, category_filter: Optional[Category] = None) -> List[Expense]:
        """
        List expenses for a project with optional filtering.
        
        Args:
            project_id: Project to list expenses for
            category_filter: Optional category filter
            
        Returns:
            List of expenses (may be empty)
        """
        expenses = await self._expenses.list_by_project(project_id)
        expenses_list = list(expenses)
        
        if category_filter:
            expenses_list = [e for e in expenses_list if e.category == category_filter]
        
        # Sort by date (newest first)
        expenses_list.sort(key=lambda x: x.date, reverse=True)
        return expenses_list

    async def get_expense(self, expense_id: UUID) -> Expense:
        """
        Get expense by ID.
        
        Args:
            expense_id: Expense's unique identifier
            
        Returns:
            Expense entity
            
        Raises:
            ValueError: If expense not found
        """
        expense = await self._expenses.get(expense_id)
        if not expense:
            raise ValueError("Expense not found")
        return expense

    async def update_expense(self, expense_id: UUID, **kwargs) -> None:
        """
        Update an existing expense.
        
        Args:
            expense_id: Expense to update
            **kwargs: Fields to update (amount, category, vendor, date, description)
            
        Raises:
            ValueError: If expense not found or invalid data
        """
        expense = await self.get_expense(expense_id)
        
        # Validate updates
        if 'amount' in kwargs:
            amount = kwargs['amount']
            if isinstance(amount, (int, float, Decimal)) and amount <= 0:
                raise ValueError("Expense amount must be positive")
            if isinstance(amount, Decimal):
                expense.amount = Money(amount, expense.amount.currency)
            else:
                expense.amount = Money(Decimal(str(amount)), expense.amount.currency)
        
        if 'date' in kwargs:
            new_date = kwargs['date']
            if isinstance(new_date, date) and new_date > date.today():
                raise ValueError("Expense date cannot be in the future")
            expense.date = new_date
        
        if 'category' in kwargs:
            if isinstance(kwargs['category'], Category):
                expense.category = kwargs['category']
            else:
                expense.category = Category(kwargs['category'])
        
        if 'vendor' in kwargs:
            vendor = kwargs['vendor']
            if not vendor or not vendor.strip():
                raise ValueError("Vendor name is required")
            expense.vendor = vendor.strip()
        
        if 'description' in kwargs:
            expense.description = kwargs['description'].strip() if kwargs['description'] else ""
        
        await self._expenses.save(expense)

    async def delete_expense(self, expense_id: UUID) -> None:
        """
        Delete an expense.
        
        Args:
            expense_id: Expense to delete
            
        Raises:
            ValueError: If expense not found
        """
        # Verify expense exists
        expense = await self.get_expense(expense_id)
        
        # Remove from project's expenses list
        project = await self._projects.get(expense.project_id)
        if project:
            # Remove expense from project's expense list
            project.expenses = [e for e in project.expenses if e.id != expense_id]
            await self._projects.save(project)
        
        # Delete expense
        await self._expenses.delete(expense_id)

    async def summarize(self, project_id: UUID) -> dict:
        """
        Generate comprehensive project financial summary.
        
        Args:
            project_id: Project to summarize
            
        Returns:
            Dictionary containing:
            - total_cost: Total spent amount
            - budget: Project budget
            - remaining_budget: Budget minus total cost
            - by_category: Breakdown by expense category
            - expense_count: Number of expenses
            
        Raises:
            ValueError: If project not found
        """
        project = await self._projects.get(project_id)
        if not project:
            raise ValueError("Project not found")
        
        expenses = await self.list_expenses(project_id)
        
        # Calculate totals by category
        total_by_category = {}
        for expense in expenses:
            category = expense.category
            if category not in total_by_category:
                total_by_category[category] = Money(Decimal("0"), project.budget.currency)
            total_by_category[category] += expense.amount
        
        return {
            "total_cost": project.total_cost,
            "budget": project.budget,
            "remaining_budget": project.remaining_budget(),
            "by_category": total_by_category,
            "expense_count": len(expenses)
        }

    async def get_expenses_for_export(self, project_id: UUID, 
                                    category_filter: Optional[Category] = None,
                                    date_from: Optional[date] = None,
                                    date_to: Optional[date] = None) -> List[Expense]:
        """
        Get expenses prepared for CSV export with optional filters.
        
        Args:
            project_id: Project to export expenses from
            category_filter: Optional category filter
            date_from: Optional start date filter
            date_to: Optional end date filter
            
        Returns:
            List of filtered expenses sorted by date
        """
        expenses = await self.list_expenses(project_id, category_filter)
        
        # Apply date filters
        if date_from:
            expenses = [e for e in expenses if e.date >= date_from]
        
        if date_to:
            expenses = [e for e in expenses if e.date <= date_to]
        
        # Sort by date (oldest first for export)
        expenses.sort(key=lambda x: x.date)
        
        return expenses