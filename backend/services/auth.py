import os
from fastapi import APIRouter, Depends, HTTPException, status, Header, Request
from pydantic import BaseModel
from sqlalchemy.future import select
from backend import schemas
from backend.database import get_db
from backend.models import User as UserModel, RoleEnum
from backend.schemas import UserRead

class TokenData(BaseModel):
    email: str | None = None

# =============================================================================
# Development Mode Bypass
# =============================================================================
"""
Development Mode Bypass allows you to skip OAuth authentication during local development.
""" 
def is_dev_mode() -> bool:
    """
    Check if the application is running in development mode.
    
    Returns:
        bool: True if DEV_MODE environment variable is set to 'true' (case insensitive)
    """
    return os.getenv("DEV_MODE", "false").lower() in ["true", "1", "yes", "on"]

def get_dev_user() -> UserRead:
    """
    Create a development mode user from environment variables.
    
    Environment Variables:
        DEV_USER_EMAIL: Email for dev user (default: dev@example.com)
        DEV_USER_ROLE: Role for dev user (default: admin)
        DEV_USER_USERNAME: Username for dev user (default: dev-user)
    
    Returns:
        UserRead: Mock user for development mode
    """
    dev_email = os.getenv("DEV_USER_EMAIL", "dev@example.com")
    dev_role_str = os.getenv("DEV_USER_ROLE", "admin")
    dev_username = os.getenv("DEV_USER_USERNAME", "dev-user")
    
    # Validate role
    try:
        dev_role = RoleEnum(dev_role_str)
    except ValueError:
        dev_role = RoleEnum.admin  # Default to admin if invalid role
    
    # Create mock user object
    from uuid import uuid4
    from datetime import datetime
    
    return UserRead(
        id=uuid4(),
        username=dev_username,
        email=dev_email,
        role=dev_role,
        agent_ids=[],
        created_at=datetime.now(),
        updated_at=datetime.now()
    )

# =============================================================================
# Authentication Functions (with Dev Mode Support)
# =============================================================================

async def get_current_user(
    x_forwarded_user: str = Header(None, alias="X-Forwarded-User"),
    x_auth_request_user: str = Header(None, alias="X-Auth-Request-User"),
    x_forwarded_email: str = Header(None, alias="X-Forwarded-Email"),
    x_auth_request_email: str = Header(None, alias="X-Auth-Request-Email"),
    db=Depends(get_db)
):
    """
    Get the current authenticated user from OAuth headers or dev mode.
    
    In production: Reads user information from OAuth proxy headers
    In dev mode: Returns a configurable dev user when DEV_MODE=true
    
    Returns:
        UserRead: Authenticated user object
        
    Raises:
        HTTPException: If authentication fails in production mode
    """
    # Development Mode Bypass
    if is_dev_mode():
        return get_dev_user()
    
    # Production Mode Authentication
    # Try to get user email from various header sources
    email = x_forwarded_email or x_auth_request_email or x_forwarded_user or x_auth_request_user
    
    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated - no user information in headers",
        )
    
    email = email.strip()
    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication - empty user information",
        )

    result = await db.execute(select(UserModel).filter(UserModel.email == email))
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    return user

class RoleChecker:
    def __init__(self, allowed_roles: list[RoleEnum]):
        self.allowed_roles = allowed_roles

    async def __call__(self, user: UserRead = Depends(get_current_user)):
        """
        Check if the user has one of the allowed roles.
        
        Args:
            user: Current authenticated user
            
        Returns:
            UserRead: The user if they have the required role
            
        Raises:
            HTTPException: If user doesn't have the required role
        """
        # Log authentication attempt for debugging
        import logging
        logger = logging.getLogger(__name__)
        
        mode = "DEV" if is_dev_mode() else "PROD"
        logger.info(f"[{mode}] Role check: user={user.email}, role={user.role.value}, allowed={[r.value for r in self.allowed_roles]}")
        
        if user.role not in self.allowed_roles:
            logger.warning(f"[{mode}] Access denied: user={user.email}, role={user.role.value}, required={[r.value for r in self.allowed_roles]}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User does not have the right privileges",
            )
        
        logger.info(f"[{mode}] Access granted: user={user.email}, role={user.role.value}")
        return user

async def get_or_create_user_from_token(
    x_forwarded_user: str = Header(None, alias="X-Forwarded-User"),
    x_auth_request_user: str = Header(None, alias="X-Auth-Request-User"),
    x_forwarded_email: str = Header(None, alias="X-Forwarded-Email"),
    x_auth_request_email: str = Header(None, alias="X-Auth-Request-Email"),
    db=Depends(get_db)
):
    """
    Get or create user from OAuth headers or dev mode.
    
    In production: Reads from OAuth headers and creates user if not exists
    In dev mode: Returns a configurable dev user when DEV_MODE=true
    
    Returns:
        UserRead: Authenticated user object
        
    Raises:
        HTTPException: If authentication fails in production mode
    """
    # Development Mode Bypass
    if is_dev_mode():
        return get_dev_user()
    
    # Production Mode Authentication
    # Try to get user email from various header sources
    email = x_forwarded_email or x_auth_request_email or x_forwarded_user or x_auth_request_user
    
    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated - no user information in headers",
        )
    
    email = email.strip()
    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication - empty user information",
        )

    result = await db.execute(select(UserModel).filter(UserModel.email == email))
    user = result.scalar_one_or_none()
    
    if user is None:
        # Create new user with default role
        new_user = UserModel(
            email=email,
            role=RoleEnum.user,
            username=email  # Using email as username for now
        )
        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)
        user = new_user

    return user

async def verify_agent_access(
    agent_id: str,
    current_user: UserRead = Depends(get_current_user),
    db=Depends(get_db)
) -> UserRead:
    """
    Dependency to verify user has access to a specific agent.
    
    This can be used as a FastAPI dependency in endpoints that require
    agent access verification.
    
    Args:
        agent_id: The agent ID to verify access for
        current_user: Current authenticated user
        db: Database session
        
    Returns:
        UserRead: The current user if access is granted
        
    Raises:
        HTTPException: If user doesn't have access to the agent
    """
    from .agent_service import AgentService  # Import here to avoid circular imports
    
    has_access = await AgentService.verify_user_agent_access_complete(
        agent_id=agent_id,
        user_id=str(current_user.id),
        user_role=current_user.role.value,
        db=db
    )
    
    if not has_access:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this agent"
        )
    
    return current_user


class AgentAccessChecker:
    """
    Factory class for creating agent access verification dependencies.
    
    This allows creating parameterized dependencies for specific agents
    that can be used in FastAPI route definitions.
    
    Example usage:
        @router.get("/agents/{agent_id}/chat")
        async def start_chat(
            agent_id: str,
            user: UserRead = Depends(AgentAccessChecker("agent_id"))
        ):
            # User has verified access to the agent
            return {"message": "Chat started"}
    """
    
    def __init__(self, agent_id_param: str = "agent_id"):
        """
        Initialize the access checker.
        
        Args:
            agent_id_param: The name of the path parameter containing the agent ID
        """
        self.agent_id_param = agent_id_param
    
    async def __call__(
        self, 
        request: Request,  # FastAPI Request object to extract path params
        current_user: UserRead = Depends(get_current_user),
        db=Depends(get_db)
    ) -> UserRead:
        """
        Verify agent access for the current request.
        
        Args:
            request: FastAPI request object
            current_user: Current authenticated user
            db: Database session
            
        Returns:
            UserRead: The current user if access is granted
            
        Raises:
            HTTPException: If user doesn't have access to the agent
        """
        # Extract agent_id from path parameters
        agent_id = request.path_params.get(self.agent_id_param)
        if not agent_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Missing {self.agent_id_param} parameter"
            )
        
        return await verify_agent_access(agent_id, current_user, db)


auth_router = APIRouter(prefix="/api/v1", tags=["auth"])

@auth_router.get("/login", response_model=schemas.UserRead)
async def login(current_user: schemas.UserRead = Depends(get_or_create_user_from_token)):
    return current_user

# =============================================================================
# Development Mode Bypass Configuration
# =============================================================================
"""
Development Mode Bypass allows you to skip OAuth authentication during local development.

SETUP:
    Set environment variables to enable dev mode:
    
    # Enable dev mode (required)
    export DEV_MODE=true
    
    # Configure dev user (optional - defaults shown)
    export DEV_USER_EMAIL="dev@example.com"
    export DEV_USER_ROLE="admin"              # admin, ops, or user
    export DEV_USER_USERNAME="dev-user"

SECURITY:
    - Dev mode ONLY works when DEV_MODE environment variable is explicitly set
    - Recommended to use .env file for local development
    - NEVER set DEV_MODE=true in production environments
    - All auth functions automatically detect and log dev vs production mode

USAGE:
    When dev mode is enabled:
    - All auth dependencies return the configured dev user
    - No OAuth headers required
    - All endpoints become accessible based on DEV_USER_ROLE
    - Perfect for testing role-based access control locally

EXAMPLE .env file:
    DEV_MODE=true
    DEV_USER_EMAIL=admin@mycompany.com
    DEV_USER_ROLE=admin
    DEV_USER_USERNAME=local-admin
    
TESTING DIFFERENT ROLES:
    # Test as admin
    export DEV_USER_ROLE=admin
    
    # Test as ops user  
    export DEV_USER_ROLE=ops
    
    # Test as regular user
    export DEV_USER_ROLE=user
    
    Restart the application after changing role to see different access levels.
""" 