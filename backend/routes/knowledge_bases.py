"""
Knowledge Base API endpoints for managing vector databases and knowledge sources.

This module provides CRUD operations for knowledge bases that are used for
Retrieval-Augmented Generation (RAG) functionality. Knowledge bases are integrated
with LlamaStack's vector database system for semantic search and document retrieval.

Key Features:
- Create and manage knowledge bases with metadata
- Automatic synchronization with LlamaStack vector databases
- Support for external knowledge sources and configurations
- Vector database name as primary identifier for LlamaStack integration
- Read-only operations after creation (knowledge bases cannot be modified)
"""
import os
from typing import List

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .. import models, schemas
from ..api.llamastack import client
from ..database import get_db
from ..services.auth import RoleChecker
from ..models import RoleEnum
from ..utils.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/knowledge_bases", tags=["knowledge_bases"])


@router.post(
    "/", response_model=schemas.KnowledgeBaseRead, status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(RoleChecker([RoleEnum.admin, RoleEnum.ops]))]
)
async def create_knowledge_base(
    kb: schemas.KnowledgeBaseCreate, db: AsyncSession = Depends(get_db)
):
    """
    Create a new knowledge base.

    This endpoint creates a new knowledge base in the database and automatically
    triggers synchronization with LlamaStack's vector database system.

    Args:
        kb: Knowledge base creation data including name, version, and configuration
        db: Database session dependency

    Returns:
        schemas.KnowledgeBaseRead: The created knowledge base with metadata

    Raises:
        HTTPException: If creation fails or validation errors occur
    """
    await dispatch_ingestion_pipeline(kb)
    db_kb = models.KnowledgeBase(**kb.model_dump(exclude_unset=True))
    db_kb.status = "pending"
    db.add(db_kb)
    await db.commit()
    await db.refresh(db_kb)

    # Auto-sync with LlamaStack after creation
    try:
        logger.info(f"Auto-syncing knowledge bases after creation of: {db_kb.name}")
        await sync_knowledge_bases(db)
    except Exception as e:
        logger.warning(f"Failed to auto-sync after knowledge base creation: {str(e)}")

    return db_kb


@router.get("/", response_model=List[schemas.KnowledgeBaseRead], dependencies=[Depends(RoleChecker([RoleEnum.admin, RoleEnum.ops]))])
async def read_knowledge_bases(db: AsyncSession = Depends(get_db)):
    """
    Retrieve all knowledge bases from the database.

    This endpoint returns a list of all knowledge bases stored in the database,
    including their metadata and configuration details.

    Args:
        db: Database session dependency

    Returns:
        List[schemas.KnowledgeBaseRead]: List of all knowledge bases
    """
    result = await db.execute(select(models.KnowledgeBase))
    return result.scalars().all()


@router.get("/{vector_db_name}", response_model=schemas.KnowledgeBaseRead, dependencies=[Depends(RoleChecker([RoleEnum.admin, RoleEnum.ops]))])
async def read_knowledge_base(vector_db_name: str, db: AsyncSession = Depends(get_db)):
    """
    Retrieve a specific knowledge base by its vector database name.

    This endpoint fetches a single knowledge base using its vector database name
    as the unique identifier, which corresponds to the LlamaStack vector database.

    Args:
        vector_db_name: The unique vector database name/identifier
        db: Database session dependency

    Returns:
        schemas.KnowledgeBaseRead: The requested knowledge base

    Raises:
        HTTPException: 404 if the knowledge base is not found
    """
    result = await db.execute(
        select(models.KnowledgeBase).where(
            models.KnowledgeBase.vector_db_name == vector_db_name
        )
    )
    kb = result.scalar_one_or_none()
    if not kb:
        raise HTTPException(status_code=404, detail="Knowledge base not found")
    return kb


@router.delete("/{vector_db_name}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(RoleChecker([RoleEnum.admin, RoleEnum.ops]))])
async def delete_knowledge_base(
    vector_db_name: str, db: AsyncSession = Depends(get_db)
):
    """
    Delete a knowledge base from both the database and LlamaStack.

    This endpoint removes a knowledge base from the local database and attempts
    to unregister it from LlamaStack's vector database system. If LlamaStack
    deletion fails, the database deletion will still proceed to handle cases
    where the knowledge base is in PENDING status.

    Args:
        vector_db_name: The vector database name/identifier of the
                       knowledge base to delete
        db: Database session dependency

    Raises:
        HTTPException: 404 if the knowledge base is not found in the database

    Returns:
        None: 204 No Content on successful deletion
    """
    result = await db.execute(
        select(models.KnowledgeBase).where(
            models.KnowledgeBase.vector_db_name == vector_db_name
        )
    )
    db_kb = result.scalar_one_or_none()
    if not db_kb:
        raise HTTPException(status_code=404, detail="Knowledge base not found")

    kb_name = db_kb.name  # Store name before deletion

    # First, try to delete from LlamaStack
    try:
        logger.info(f"Deleting knowledge base from LlamaStack: {vector_db_name}")
        client.vector_dbs.unregister(vector_db_name)
        logger.info(f"Successfully deleted from LlamaStack: {vector_db_name}")

    except Exception as e:
        logger.warning(f"Failed to delete from LlamaStack (may not exist): {str(e)}")
        # Continue with DB deletion even if LlamaStack deletion fails
        # This handles cases where the KB exists
        # in DB but not in LlamaStack (PENDING status)

    # Then delete from database
    await db.delete(db_kb)
    await db.commit()

    logger.info(f"Successfully deleted knowledge base from database: {kb_name}")
    return None


@router.post("/sync", response_model=List[schemas.KnowledgeBaseRead], dependencies=[Depends(RoleChecker([RoleEnum.admin]))])
async def sync_knowledge_bases_endpoint(db: AsyncSession = Depends(get_db)):
    """
    Synchronize knowledge bases between the database and LlamaStack.

    This endpoint performs a unidirectional sync that fetches vector databases
    from LlamaStack and adds any missing ones to the local database. It preserves
    knowledge bases with PENDING status (exist in DB but not yet in LlamaStack).

    Args:
        db: Database session dependency

    Returns:
        List[schemas.KnowledgeBaseRead]: List of synchronized knowledge bases

    Raises:
        HTTPException: If synchronization fails due to LlamaStack errors
    """
    try:
        return await sync_knowledge_bases(db)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


async def dispatch_ingestion_pipeline(kb: schemas.KnowledgeBaseCreate):
    """
    Internal method that dispatches a new pipeline

    This method takes in a KnowledgebaseCreate object and converts it
    to a pipeline creation dictionary. It then calls the ingestion-pipeline
    API service to add a new pipeline and trigger a run.

    Args:
        kb: KnowledgeBaseCreate with all the relevant source information

    Returns:
        None

    Raises:
        Exception: If the ingestion-pipeline API call fails
    """
    add_pipeline = os.environ["INGESTION_PIPELINE_URL"] + "/add_pipeline"
    data = kb.pipeline_model_dict()
    logger.info(f"Dispatching pipeline to {add_pipeline} {data=}")
    async with httpx.AsyncClient() as client:
        response = await client.post(add_pipeline, json=data)
        response.raise_for_status()


async def sync_knowledge_bases(db: AsyncSession):
    """
    Internal synchronization function for knowledge bases with LlamaStack.

    This function performs the actual sync logic by fetching vector databases
    from LlamaStack and updating the local database. It's called automatically
    after knowledge base operations and by the manual sync endpoint.

    The sync is unidirectional - it only adds missing items from LlamaStack
    to the database without removing existing database entries. This preserves
    knowledge bases in PENDING status during ingestion processes.

    Args:
        db: Database session for executing queries

    Returns:
        List[models.KnowledgeBase]: List of synchronized knowledge bases

    Raises:
        Exception: If LlamaStack communication fails or database operations fail
    """
    try:
        logger.info("Starting knowledge base sync")
        logger.debug("Fetching vector databases from LlamaStack")
        try:
            response = client.vector_dbs.list()

            if isinstance(response, list):
                vector_dbs = [item.__dict__ for item in response]
            elif isinstance(response, dict):
                vector_dbs = response.get("data", [])
            elif hasattr(response, "data"):
                vector_dbs = response.data
            else:
                logger.warning(f"Unexpected response type: {type(response)}")
                vector_dbs = []

        except Exception as e:
            raise Exception(
                f"Failed to fetch vector databases from LlamaStack: {str(e)}"
            )

        logger.debug("Fetching existing knowledge bases from database...")
        result = await db.execute(select(models.KnowledgeBase))
        existing_kbs = {kb.vector_db_name: kb for kb in result.scalars().all()}
        logger.debug(
            f"Found {len(existing_kbs)} existing knowledge bases: "
            f"{list(existing_kbs.keys())}"
        )

        synced_kbs = []

        logger.debug("Processing vector databases...")
        for vector_db in vector_dbs:
            try:
                if not vector_db.get("identifier"):
                    logger.debug(
                        f"Skipping vector database without identifier: {vector_db}"
                    )
                    continue

                kb_data = {
                    "name": vector_db["identifier"],
                    "version": "1.0",
                    "embedding_model": vector_db.get(
                        "embedding_model", "all-MiniLM-L6-v2"
                    ),
                    "provider_id": vector_db.get("provider_id"),
                    "vector_db_name": vector_db["identifier"],
                    "is_external": False,
                    "source": None,
                    "source_configuration": {
                        "embedding_dimension": vector_db.get("embedding_dimension"),
                        "type": vector_db.get("type"),
                        "provider_resource_id": vector_db.get("provider_resource_id"),
                    },
                }
                logger.debug(
                    f"Processing vector database {vector_db['identifier']} "
                    f"with data: {kb_data}"
                )

                if vector_db["identifier"] in existing_kbs:
                    logger.debug(
                        "Updating existing knowledge base: "
                        f"{vector_db['identifier']}"
                    )
                    kb = existing_kbs[vector_db["identifier"]]
                    for field, value in kb_data.items():
                        setattr(kb, field, value)
                else:
                    logger.debug(
                        f"Creating new knowledge base: {vector_db['identifier']}"
                    )
                    kb = models.KnowledgeBase(**kb_data)
                    db.add(kb)

                synced_kbs.append(kb)
            except Exception as e:
                logger.error(
                    "Error processing vector database "
                    f"{vector_db.get('identifier', 'unknown')}: {str(e)}"
                )
                continue

        # Note: We no longer remove knowledge bases from DB that don't
        # exist in LlamaStack. This allows for PENDING status (exists in DB
        # but not yet in LlamaStack during ingestion). Deletion from DB should
        # only happen through explicit delete API calls
        logger.info("Sync complete - only added missing items from LlamaStack to DB")

        logger.debug("Committing changes to database...")
        await db.commit()

        logger.debug("Refreshing synced knowledge bases...")
        for kb in synced_kbs:
            await db.refresh(kb)

        logger.info(f"Sync complete. Synced {len(synced_kbs)} knowledge bases.")
        return synced_kbs

    except Exception as e:
        logger.error(f"Error during sync: {str(e)}")
        raise Exception(f"Failed to sync knowledge bases: {str(e)}")
