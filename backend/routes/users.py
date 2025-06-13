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
from ..services.auth import RoleChecker
from ..models import RoleEnum

router = APIRouter(prefix="/users", tags=["users"])


@router.post("/", response_model=schemas.UserRead, status_code=status.HTTP_201_CREATED)
async def create_user(user: schemas.UserCreate, db: AsyncSession = Depends(get_db)):
    """
    Create a new user account with encrypted password.

    This endpoint registers a new user in the system with secure password
    hashing using bcrypt. The user's role determines their access permissions
    within the application.

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


@router.get("/{user_id}", response_model=schemas.UserRead)
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


@router.put("/{user_id}", response_model=schemas.UserRead)
async def update_user(
    user_id: UUID, user: schemas.UserCreate, db: AsyncSession = Depends(get_db)
):
    """
    Update an existing user's profile information.

    This endpoint allows updating user details including username, email,
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


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: UUID, db: AsyncSession = Depends(get_db)):
    """
    Delete a user account from the system.

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
