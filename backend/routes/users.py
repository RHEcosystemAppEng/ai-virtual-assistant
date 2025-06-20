"""
User management API endpoints for authentication and user administration.

This module provides CRUD operations for user accounts, including user creation,
authentication, role management, and profile updates. It handles password hashing
and role-based access control for the AI Virtual Assistant application.

Key Features:
- User registration and profile management
- Secure password hashing with bcrypt
- Role-based access control (admin, user, etc.)
- User lookup and management operations
"""

from typing import List
from uuid import UUID

import bcrypt
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from .. import models, schemas
from ..database import get_db
from ..services.auth import RoleChecker, get_current_user
from ..services.agent_service import AgentService
from ..models import RoleEnum
from ..utils.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/users", tags=["users"])


@router.post("/", response_model=schemas.UserRead, status_code=status.HTTP_201_CREATED, dependencies=[Depends(RoleChecker([RoleEnum.admin]))])
async def create_user(user: schemas.UserCreate, db: AsyncSession = Depends(get_db)):
    """
    Create a new user account with encrypted password (Admin only).

    This endpoint registers a new user in the system with secure password
    hashing using bcrypt. Only administrators can create new user accounts.
    The user's role determines their access permissions within the application.

    Args:
        user: User creation data including username, email, password, and role
        db: Database session dependency

    Returns:
        schemas.UserRead: The created user (without password hash)

    Raises:
        HTTPException: If username/email already exists or validation fails
    """
    hashed_password = bcrypt.hashpw(
        user.password.encode("utf-8"), bcrypt.gensalt()
    ).decode("utf-8")
    db_user = models.User(
        username=user.username,
        email=user.email,
        password_hash=hashed_password,
        role=user.role,
    )
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user

@router.get("/", response_model=List[schemas.UserRead], dependencies=[Depends(RoleChecker([RoleEnum.admin]))])
async def read_users(db: AsyncSession = Depends(get_db)):
    """
    Retrieve all user accounts from the database.

    This endpoint returns a list of all registered users with their profile
    information (excluding password hashes for security).

    Args:
        db: Database session dependency

    Returns:
        List[schemas.UserRead]: List of all users
    """
    result = await db.execute(select(models.User))
    return result.scalars().all()


@router.get("/{user_id}", response_model=schemas.UserRead, dependencies=[Depends(RoleChecker([RoleEnum.admin]))])
async def read_user(user_id: UUID, db: AsyncSession = Depends(get_db)):
    """
    Retrieve a specific user by their unique identifier.

    This endpoint fetches a single user's profile information using their UUID.

    Args:
        user_id: The unique identifier of the user to retrieve
        db: Database session dependency

    Returns:
        schemas.UserRead: The requested user profile

    Raises:
        HTTPException: 404 if the user is not found
    """
    result = await db.execute(select(models.User).where(models.User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.put("/{user_id}", response_model=schemas.UserRead, dependencies=[Depends(RoleChecker([RoleEnum.admin]))])
async def update_user(
    user_id: UUID, user: schemas.UserCreate, db: AsyncSession = Depends(get_db)
):
    """
    Update an existing user's profile information (Admin only).

    This endpoint allows administrators to update user details including username, email,
    password, and role. The password will be re-hashed if provided.

    Args:
        user_id: The unique identifier of the user to update
        user: Updated user data
        db: Database session dependency

    Returns:
        schemas.UserRead: The updated user profile

    Raises:
        HTTPException: 404 if the user is not found
    """
    result = await db.execute(select(models.User).where(models.User.id == user_id))
    db_user = result.scalar_one_or_none()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    db_user.username = user.username
    db_user.email = user.email
    db_user.password_hash = user.password
    db_user.role = user.role
    await db.commit()
    await db.refresh(db_user)
    return db_user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(RoleChecker([RoleEnum.admin]))])
async def delete_user(user_id: UUID, db: AsyncSession = Depends(get_db)):
    """
    Delete a user account from the system (Admin only).

    This endpoint permanently removes a user account and all associated data.
    Use with caution as this operation cannot be undone.

    Args:
        user_id: The unique identifier of the user to delete
        db: Database session dependency

    Raises:
        HTTPException: 404 if the user is not found

    Returns:
        None: 204 No Content on successful deletion
    """
    result = await db.execute(select(models.User).where(models.User.id == user_id))
    db_user = result.scalar_one_or_none()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    await db.delete(db_user)
    await db.commit()
    return None


@router.get("/profile", response_model=schemas.UserProfileResponse)
async def get_current_user_profile(current_user: schemas.UserRead = Depends(get_current_user)):
    """
    Get the current authenticated user's profile information.

    This endpoint returns the profile information for the currently authenticated user,
    including their role, assigned agents, and account details.

    Args:
        current_user: The current authenticated user from auth dependency

    Returns:
        schemas.UserProfileResponse: The user's profile information
    """
    return current_user


@router.post("/{user_id}", response_model=schemas.UserRead, dependencies=[Depends(RoleChecker([RoleEnum.admin]))])
async def assign_agents_to_user(
    user_id: UUID, 
    assignment: schemas.AgentAssignmentRequest, 
    current_admin: schemas.UserRead = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Assign virtual assistant agents to a user (Admin only).

    This endpoint allows administrators to assign virtual assistant agents to users.
    Each agent will be cloned from the specified templates to ensure uniqueness per user.

    Args:
        user_id: The unique identifier of the user to assign agents to
        assignment: Agent assignment request containing template agent IDs
        db: Database session dependency

    Returns:
        schemas.UserRead: The updated user with new agent assignments

    Raises:
        HTTPException: 404 if the user is not found
        HTTPException: 400 if base agents don't exist
        HTTPException: 500 if agent cloning fails
    """
    # Get the user
    result = await db.execute(select(models.User).where(models.User.id == user_id))
    db_user = result.scalar_one_or_none()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    # Validate that all base agents exist before proceeding
    valid_base_agents = await AgentService.validate_base_agents_exist(
        assignment.agent_template_ids
    )

    try:
        # Clone agents for the user
        cloned_agent_ids = await AgentService.clone_multiple_agents_for_user(
            base_agent_ids=valid_base_agents,
            user_id=str(user_id),
            user_email=db_user.email,
            admin_user_id=str(current_admin.id)
        )

        # Normalize existing agent assignments to new format for backward compatibility
        current_assignments = AgentService.normalize_agent_ids(db_user.agent_ids)
        
        # Create new assignments for cloned agents
        new_assignments = []
        for i, cloned_agent_id in enumerate(cloned_agent_ids):
            base_template_id = valid_base_agents[i] if i < len(valid_base_agents) else None
            assignment_obj = AgentService.create_agent_assignment(
                agent_id=cloned_agent_id,
                assignment_type="clone",
                assigned_by=str(current_admin.id),
                base_template_id=base_template_id
            )
            new_assignments.append(assignment_obj)
        
        # Combine existing and new assignments, avoiding duplicates by agent_id
        existing_agent_ids = AgentService.extract_agent_ids(current_assignments)
        updated_assignments = current_assignments.copy()
        
        for new_assignment in new_assignments:
            if new_assignment["agent_id"] not in existing_agent_ids:
                updated_assignments.append(new_assignment)
        
        db_user.agent_ids = updated_assignments
        await db.commit()
        await db.refresh(db_user)
        
        return db_user

    except Exception as e:
        # Rollback database changes
        await db.rollback()
        
        # If we have partially created agents, attempt cleanup
        # Note: This is a best-effort cleanup; some agents might remain if cleanup fails
        if 'cloned_agent_ids' in locals():
            for agent_id in cloned_agent_ids:
                try:
                    await AgentService.delete_user_agent(agent_id, str(user_id))
                except Exception as cleanup_error:
                    # Log cleanup failures but don't fail the overall operation
                    logger.error(f"Failed to cleanup agent {agent_id}: {cleanup_error}")
        
        # Re-raise the original exception
        if isinstance(e, HTTPException):
            raise
        raise HTTPException(
            status_code=500,
            detail=f"Failed to assign agents to user: {str(e)}"
        )


@router.put("/{user_id}/role", response_model=schemas.UserRead, dependencies=[Depends(RoleChecker([RoleEnum.admin]))])
async def update_user_role(
    user_id: UUID, 
    user_update: schemas.UserUpdate, 
    db: AsyncSession = Depends(get_db)
):
    """
    Update a user's role (Admin only).

    This endpoint allows administrators to update a user's role in the system.

    Args:
        user_id: The unique identifier of the user to update
        user_update: User update data containing the new role
        db: Database session dependency

    Returns:
        schemas.UserRead: The updated user information

    Raises:
        HTTPException: 404 if the user is not found
    """
    # Get the user
    result = await db.execute(select(models.User).where(models.User.id == user_id))
    db_user = result.scalar_one_or_none()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    # Update the role if provided
    if user_update.role is not None:
        db_user.role = user_update.role
        
    await db.commit()
    await db.refresh(db_user)
    
    return db_user


@router.get("/agents", response_model=List[str])
async def get_current_user_agents(current_user: schemas.UserRead = Depends(get_current_user)):
    """
    Get the current user's assigned agent IDs.

    This endpoint returns a list of agent IDs that the current user has access to.
    Available to all authenticated users for self-service.

    Args:
        current_user: The current authenticated user from auth dependency

    Returns:
        List[str]: List of agent IDs assigned to the current user
    """
    # Extract agent IDs from the potentially mixed format (strings or objects)
    return AgentService.extract_agent_ids(current_user.agent_ids or [])


@router.get("/{user_id}/agents", response_model=List[str], dependencies=[Depends(RoleChecker([RoleEnum.admin]))])
async def get_user_agents(user_id: UUID, db: AsyncSession = Depends(get_db)):
    """
    Get a specific user's assigned agent IDs (Admin only).

    This endpoint allows administrators to view the agent assignments for any user.

    Args:
        user_id: The unique identifier of the user to get agents for
        db: Database session dependency

    Returns:
        List[str]: List of agent IDs assigned to the specified user

    Raises:
        HTTPException: 404 if the user is not found
    """
    # Get the user
    result = await db.execute(select(models.User).where(models.User.id == user_id))
    db_user = result.scalar_one_or_none()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Extract agent IDs from the potentially mixed format (strings or objects)  
    return AgentService.extract_agent_ids(db_user.agent_ids or [])


@router.delete("/{user_id}/agents/{agent_id}", response_model=schemas.UserRead, dependencies=[Depends(RoleChecker([RoleEnum.admin]))])
async def remove_agent_from_user(
    user_id: UUID,
    agent_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Remove a specific agent from a user's assignment (Admin only).

    This endpoint allows administrators to remove an agent from a user's
    assigned agent list and delete the agent instance from LlamaStack.

    Args:
        user_id: The unique identifier of the user
        agent_id: The ID of the agent to remove
        db: Database session dependency

    Returns:
        schemas.UserRead: The updated user information

    Raises:
        HTTPException: 404 if user or agent not found
        HTTPException: 400 if agent is not assigned to user
    """
    # Get the user
    result = await db.execute(select(models.User).where(models.User.id == user_id))
    db_user = result.scalar_one_or_none()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    # Check if agent is assigned to user
    current_assignments = AgentService.normalize_agent_ids(db_user.agent_ids)
    current_agent_ids = AgentService.extract_agent_ids(current_assignments)
    if agent_id not in current_agent_ids:
        raise HTTPException(
            status_code=400, 
            detail="Agent is not assigned to this user"
        )

    try:
        # Remove agent from LlamaStack (if it's a cloned agent)
        await AgentService.delete_user_agent(agent_id, str(user_id))
        
        # Remove agent from user's assignment list
        updated_assignments = [
            assignment for assignment in current_assignments 
            if assignment.get("agent_id") != agent_id
        ]
        db_user.agent_ids = updated_assignments
        
        await db.commit()
        await db.refresh(db_user)
        
        return db_user

    except Exception as e:
        await db.rollback()
        
        # If it's an access error (agent doesn't belong to user), that's expected for template agents
        if isinstance(e, HTTPException) and e.status_code == 403:
            # Agent might be a template agent, just remove from user's list
            updated_assignments = [
                assignment for assignment in current_assignments 
                if assignment.get("agent_id") != agent_id
            ]
            db_user.agent_ids = updated_assignments
            
            await db.commit()
            await db.refresh(db_user)
            
            logger.info(f"Removed template agent {agent_id} from user {user_id} assignment")
            return db_user
        
        # Re-raise other errors
        if isinstance(e, HTTPException):
            raise
        raise HTTPException(
            status_code=500,
            detail=f"Failed to remove agent from user: {str(e)}"
        )
