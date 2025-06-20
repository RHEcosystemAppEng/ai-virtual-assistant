"""
Guardrails API endpoints for managing AI safety and content filtering rules.

This module provides CRUD operations for guardrails that define safety constraints
and content filtering rules for AI virtual assistants. All operations require admin access.
"""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from .. import models, schemas
from ..database import get_db
from ..services.auth import RoleChecker
from ..models import RoleEnum

router = APIRouter(prefix="/guardrails", tags=["guardrails"])


@router.post(
    "/", response_model=schemas.GuardrailRead, status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(RoleChecker([RoleEnum.admin]))]
)
async def create_guardrail(
    item: schemas.GuardrailCreate, db: AsyncSession = Depends(get_db)
):
    """
    Create a new guardrail with specified rules and configuration (Admin only).

    Args:
        item: Guardrail data containing name and rules
        db: Database session dependency

    Returns:
        Created guardrail with generated ID and metadata
    """
    db_item = models.Guardrail(**item.dict())
    db.add(db_item)
    await db.commit()
    await db.refresh(db_item)
    return db_item


@router.get("/", response_model=List[schemas.GuardrailRead], dependencies=[Depends(RoleChecker([RoleEnum.admin]))])
async def read_guardrails(db: AsyncSession = Depends(get_db)):
    """
    Retrieve all guardrails from the database (Admin only).

    Args:
        db: Database session dependency

    Returns:
        List of all guardrails with their rules and metadata
    """
    result = await db.execute(select(models.Guardrail))
    return result.scalars().all()


@router.get("/{guardrail_id}", response_model=schemas.GuardrailRead, dependencies=[Depends(RoleChecker([RoleEnum.admin]))])
async def read_guardrail(guardrail_id: UUID, db: AsyncSession = Depends(get_db)):
    """
    Retrieve a specific guardrail by its ID (Admin only).

    Args:
        guardrail_id: UUID of the guardrail to retrieve
        db: Database session dependency

    Returns:
        Guardrail with specified ID

    Raises:
        HTTPException: 404 if guardrail not found
    """
    result = await db.execute(
        select(models.Guardrail).where(models.Guardrail.id == guardrail_id)
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Guardrail not found")
    return item


@router.put("/{guardrail_id}", response_model=schemas.GuardrailRead, dependencies=[Depends(RoleChecker([RoleEnum.admin]))])
async def update_guardrail(
    guardrail_id: UUID,
    item: schemas.GuardrailCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Update an existing guardrail's rules and configuration (Admin only).

    Args:
        guardrail_id: UUID of the guardrail to update
        item: New guardrail data to apply
        db: Database session dependency

    Returns:
        Updated guardrail with new rules and metadata

    Raises:
        HTTPException: 404 if guardrail not found
    """
    result = await db.execute(
        select(models.Guardrail).where(models.Guardrail.id == guardrail_id)
    )
    db_item = result.scalar_one_or_none()
    if not db_item:
        raise HTTPException(status_code=404, detail="Guardrail not found")
    for field, value in item.dict().items():
        setattr(db_item, field, value)
    await db.commit()
    await db.refresh(db_item)
    return db_item


@router.delete("/{guardrail_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(RoleChecker([RoleEnum.admin]))])
async def delete_guardrail(guardrail_id: UUID, db: AsyncSession = Depends(get_db)):
    """
    Delete a guardrail from the database (Admin only).

    Args:
        guardrail_id: UUID of the guardrail to delete
        db: Database session dependency

    Returns:
        None (204 No Content)

    Raises:
        HTTPException: 404 if guardrail not found
    """
    result = await db.execute(
        select(models.Guardrail).where(models.Guardrail.id == guardrail_id)
    )
    db_item = result.scalar_one_or_none()
    if not db_item:
        raise HTTPException(status_code=404, detail="Guardrail not found")
    await db.delete(db_item)
    await db.commit()
    return None
