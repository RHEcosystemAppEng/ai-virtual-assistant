"""
Chat History API endpoints for managing conversation records.

This module provides CRUD operations for chat history records, storing
conversation data between users and virtual assistants. It maintains
persistent records of chat interactions for audit trails and conversation
continuity.

Key Features:
- Store and retrieve chat conversation history with user isolation
- Associate chat records with specific agents and users
- Support for message and response storage
- Conversation audit and retrieval capabilities
- Users can only access their own chat history
"""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from .. import models, schemas
from ..database import get_db
from ..services.auth import get_current_user, RoleChecker
from ..models import RoleEnum

router = APIRouter(prefix="/chat_history", tags=["chat_history"])


@router.post(
    "/", response_model=schemas.ChatHistoryRead, status_code=status.HTTP_201_CREATED
)
async def create_chat_history(
    item: schemas.ChatHistoryCreate, 
    current_user: schemas.UserRead = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new chat history record.

    This endpoint stores a new chat interaction record including the user's
    message and the assistant's response for future reference and audit.
    The chat history is automatically associated with the current user.

    Args:
        item: Chat history data including agent_id, message, and response
        current_user: Current authenticated user
        db: Database session dependency

    Returns:
        schemas.ChatHistoryRead: The created chat history record

    Raises:
        HTTPException: If creation fails or validation errors occur
    """
    # Associate the chat history with the current user
    chat_data = item.dict()
    chat_data['user_id'] = current_user.id
    
    db_item = models.ChatHistory(**chat_data)
    db.add(db_item)
    await db.commit()
    await db.refresh(db_item)
    return db_item


@router.get("/", response_model=List[schemas.ChatHistoryRead])
async def read_chat_history(
    current_user: schemas.UserRead = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieve chat history for the current user.
    
    This endpoint returns chat history records that belong to the current user only.
    Admins can see all chat history by using the admin-specific endpoint.

    Args:
        current_user: Current authenticated user
        db: Database session dependency

    Returns:
        List[schemas.ChatHistoryRead]: List of user's chat history records
    """
    if current_user.role == RoleEnum.admin:
        # Admins can see all chat history
        result = await db.execute(select(models.ChatHistory))
    else:
        # Regular users can only see their own chat history
        result = await db.execute(
            select(models.ChatHistory).where(models.ChatHistory.user_id == current_user.id)
        )
    return result.scalars().all()


@router.get("/{chat_id}", response_model=schemas.ChatHistoryRead)
async def read_chat_item(
    chat_id: UUID, 
    current_user: schemas.UserRead = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieve a specific chat history record.
    
    Users can only access their own chat history records unless they are admin.

    Args:
        chat_id: UUID of the chat history record to retrieve
        current_user: Current authenticated user
        db: Database session dependency

    Returns:
        schemas.ChatHistoryRead: The requested chat history record

    Raises:
        HTTPException: 404 if chat history not found or user doesn't have access
    """
    result = await db.execute(
        select(models.ChatHistory).where(models.ChatHistory.id == chat_id)
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Chat history not found")
    
    # Check if user has access to this chat history
    if current_user.role != RoleEnum.admin and item.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="You don't have access to this chat history")
    
    return item


@router.delete("/{chat_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_chat_item(
    chat_id: UUID, 
    current_user: schemas.UserRead = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a chat history record.
    
    Users can only delete their own chat history records unless they are admin.

    Args:
        chat_id: UUID of the chat history record to delete
        current_user: Current authenticated user
        db: Database session dependency

    Returns:
        None (204 No Content)

    Raises:
        HTTPException: 404 if chat history not found or user doesn't have access
    """
    result = await db.execute(
        select(models.ChatHistory).where(models.ChatHistory.id == chat_id)
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Chat history not found")
    
    # Check if user has access to delete this chat history
    if current_user.role != RoleEnum.admin and item.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="You don't have access to this chat history")
    
    await db.delete(item)
    await db.commit()
    return None


@router.get("/admin/all", response_model=List[schemas.ChatHistoryRead], dependencies=[Depends(RoleChecker([RoleEnum.admin]))])
async def read_all_chat_history_admin(db: AsyncSession = Depends(get_db)):
    """
    Retrieve all chat history records (Admin only).
    
    This endpoint allows administrators to view all chat history records
    across all users for audit and monitoring purposes.

    Args:
        db: Database session dependency

    Returns:
        List[schemas.ChatHistoryRead]: List of all chat history records
    """
    result = await db.execute(select(models.ChatHistory))
    return result.scalars().all()
