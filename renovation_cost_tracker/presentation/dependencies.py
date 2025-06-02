import os
from typing import AsyncGenerator
from uuid import UUID

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from jose import JWTError, jwt

from renovation_cost_tracker.infrastructure.db import get_engine, get_session_factory
from renovation_cost_tracker.infrastructure.repositories import (
    PostgresUserRepository,
    PostgresProjectRepository, 
    PostgresExpenseRepository,
)
from renovation_cost_tracker.application.services import (
    AuthService,
    ProjectService,
    ExpenseService,
)
from renovation_cost_tracker.domain.models import User


class DependencyContainer:
    """Dependency injection container for managing application dependencies"""
    
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.engine = get_engine(database_url)
        self.session_factory = get_session_factory(self.engine)
        
        # JWT configuration
        self.jwt_secret = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
        self.jwt_algorithm = os.getenv("JWT_ALGORITHM", "HS256")
        
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get database session"""
        async with self.session_factory() as session:
            try:
                yield session
            finally:
                await session.close()
    
    def get_user_repository(self, session: AsyncSession = None) -> PostgresUserRepository:
        """Get user repository instance"""
        if session:
            # For when we already have a session in the same request
            return PostgresUserRepository(lambda: session)
        return PostgresUserRepository(self.session_factory)
    
    def get_project_repository(self, session: AsyncSession = None) -> PostgresProjectRepository:
        """Get project repository instance"""
        if session:
            return PostgresProjectRepository(lambda: session)
        return PostgresProjectRepository(self.session_factory)
    
    def get_expense_repository(self, session: AsyncSession = None) -> PostgresExpenseRepository:
        """Get expense repository instance"""
        if session:
            return PostgresExpenseRepository(lambda: session)
        return PostgresExpenseRepository(self.session_factory)
    
    def get_auth_service(self, session: AsyncSession = None) -> AuthService:
        """Get authentication service instance"""
        user_repo = self.get_user_repository(session)
        return AuthService(user_repo)
    
    def get_project_service(self, session: AsyncSession = None) -> ProjectService:
        """Get project service instance"""
        project_repo = self.get_project_repository(session)
        return ProjectService(project_repo)
    
    def get_expense_service(self, session: AsyncSession = None) -> ExpenseService:
        """Get expense service instance"""
        project_repo = self.get_project_repository(session)
        expense_repo = self.get_expense_repository(session)
        return ExpenseService(project_repo, expense_repo)


# Security dependencies
security = HTTPBearer()


async def get_container(request: Request) -> DependencyContainer:
    """Get dependency container from app state"""
    return request.app.state.container


async def get_database_session(
    container: DependencyContainer = Depends(get_container)
) -> AsyncGenerator[AsyncSession, None]:
    """Database session dependency"""
    async for session in container.get_session():
        yield session


async def get_user_repository(
    session: AsyncSession = Depends(get_database_session),
    container: DependencyContainer = Depends(get_container)
) -> PostgresUserRepository:
    """User repository dependency"""
    return container.get_user_repository(session)


async def get_project_repository(
    session: AsyncSession = Depends(get_database_session),
    container: DependencyContainer = Depends(get_container)
) -> PostgresProjectRepository:
    """Project repository dependency"""
    return container.get_project_repository(session)


async def get_expense_repository(
    session: AsyncSession = Depends(get_database_session),
    container: DependencyContainer = Depends(get_container)
) -> PostgresExpenseRepository:
    """Expense repository dependency"""
    return container.get_expense_repository(session)


async def get_auth_service(
    session: AsyncSession = Depends(get_database_session),
    container: DependencyContainer = Depends(get_container)
) -> AuthService:
    """Authentication service dependency"""
    return container.get_auth_service(session)


async def get_project_service(
    session: AsyncSession = Depends(get_database_session),
    container: DependencyContainer = Depends(get_container)
) -> ProjectService:
    """Project service dependency"""
    return container.get_project_service(session)


async def get_expense_service(
    session: AsyncSession = Depends(get_database_session),
    container: DependencyContainer = Depends(get_container)
) -> ExpenseService:
    """Expense service dependency"""
    return container.get_expense_service(session)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    auth_service: AuthService = Depends(get_auth_service),
    container: DependencyContainer = Depends(get_container)
) -> User:
    """
    Extract and validate JWT token, return current user.
    
    This dependency:
    1. Extracts Bearer token from Authorization header
    2. Validates JWT token signature and expiration
    3. Extracts user_id from token payload
    4. Fetches user from database
    5. Returns User entity
    
    Raises HTTPException if:
    - Token is missing or invalid
    - Token is expired
    - User not found in database
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # Decode JWT token
        payload = jwt.decode(
            credentials.credentials,
            container.jwt_secret,
            algorithms=[container.jwt_algorithm]
        )
        
        # Extract user_id from token
        user_id_str: str = payload.get("sub")
        if user_id_str is None:
            raise credentials_exception
            
        user_id = UUID(user_id_str)
        
    except (JWTError, ValueError):
        raise credentials_exception
    
    # Get user from database
    try:
        user = await auth_service.get_user(user_id)
        return user
    except ValueError:
        raise credentials_exception


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Ensure user is active (for future extensibility).
    Currently just returns the user, but can be extended
    to check user status, subscription, etc.
    """
    # Future: check if user.is_active, subscription status, etc.
    return current_user