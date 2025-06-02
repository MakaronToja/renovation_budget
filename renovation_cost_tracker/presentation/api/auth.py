import os
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from jose import jwt
from pydantic import BaseModel, EmailStr

from renovation_cost_tracker.application.services import AuthService
from renovation_cost_tracker.presentation.dependencies import get_auth_service
from renovation_cost_tracker.domain.models import User


router = APIRouter()

# JWT Configuration
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))  # 24 hours


# Pydantic schemas for request/response
class UserRegister(BaseModel):
    """User registration request schema"""
    email: EmailStr
    password: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "email": "user@example.com",
                "password": "strongpassword123"
            }
        }


class UserLogin(BaseModel):
    """User login request schema"""
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    """User response schema (without sensitive data)"""
    id: str
    email: str
    created_at: datetime
    
    class Config:
        from_attributes = True


class Token(BaseModel):
    """JWT token response schema"""
    access_token: str
    token_type: str
    expires_in: int
    user: UserResponse


def create_access_token(data: dict, expires_delta: timedelta = None) -> str:
    """
    Create JWT access token.
    
    Args:
        data: Payload data to encode in token
        expires_delta: Token expiration time
        
    Returns:
        Encoded JWT token string
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return encoded_jwt


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register new user",
    description="Register a new user account with email and password"
)
async def register_user(
    user_data: UserRegister,
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Register a new user account.
    
    **Requirements:**
    - Email must be valid and unique
    - Password must be at least 8 characters
    
    **Returns:**
    - User information (without password)
    - HTTP 201 on success
    - HTTP 400 if email already exists or validation fails
    """
    try:
        # Validate password strength
        if len(user_data.password) < 8:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password must be at least 8 characters long"
            )
        
        # Register user through service
        user = await auth_service.register(user_data.email, user_data.password)
        
        return UserResponse(
            id=str(user.id),
            email=user.email,
            created_at=user.created_at
        )
        
    except ValueError as e:
        # Handle business logic errors (e.g., email already exists)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        # Handle unexpected errors
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during registration"
        )


@router.post(
    "/login",
    response_model=Token,
    summary="User login",
    description="Authenticate user and return JWT access token"
)
async def login_user(
    user_data: UserLogin,
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Authenticate user and return JWT token.
    
    **Process:**
    1. Validate email and password
    2. Generate JWT access token
    3. Return token with user information
    
    **Returns:**
    - JWT access token (expires in 24 hours)
    - User information
    - HTTP 200 on success
    - HTTP 401 on invalid credentials
    """
    try:
        # Authenticate user
        user = await auth_service.login(user_data.email, user_data.password)
        
        # Create JWT token
        access_token_expires = timedelta(minutes=JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": str(user.id)},
            expires_delta=access_token_expires
        )
        
        return Token(
            access_token=access_token,
            token_type="bearer",
            expires_in=JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,  # in seconds
            user=UserResponse(
                id=str(user.id),
                email=user.email,
                created_at=user.created_at
            )
        )
        
    except ValueError as e:
        # Handle authentication errors
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"}
        )
    except Exception as e:
        # Handle unexpected errors
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during login"
        )


@router.post(
    "/token",
    response_model=Token,
    summary="OAuth2 compatible token endpoint",
    description="OAuth2 compatible endpoint for token-based authentication"
)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    OAuth2 compatible token endpoint.
    
    This endpoint is compatible with OAuth2 password flow
    and can be used with FastAPI's automatic OAuth2 documentation.
    
    **Form parameters:**
    - username: User's email address
    - password: User's password
    
    **Returns:**
    - JWT access token
    - User information
    """
    try:
        # In OAuth2 flow, username field contains the email
        user = await auth_service.login(form_data.username, form_data.password)
        
        # Create JWT token
        access_token_expires = timedelta(minutes=JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": str(user.id)},
            expires_delta=access_token_expires
        )
        
        return Token(
            access_token=access_token,
            token_type="bearer",
            expires_in=JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user=UserResponse(
                id=str(user.id),
                email=user.email,
                created_at=user.created_at
            )
        )
        
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"}
        )


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user",
    description="Get information about the currently authenticated user"
)
async def get_current_user_info():
    """
    Get current user information.
    
    **Requires:**
    - Valid JWT token in Authorization header
    
    **Returns:**
    - Current user information
    - HTTP 200 on success
    - HTTP 401 if token is invalid or expired
    
    Note: This endpoint will be completed when dependencies are fully configured
    """
    # This endpoint will be implemented with proper dependency injection
    # after all circular import issues are resolved
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="This endpoint will be implemented in the next iteration"
    )