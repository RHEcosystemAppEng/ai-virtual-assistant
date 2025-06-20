"""
Model Server management API endpoints for LLM providers.

This module provides CRUD operations for model servers, which are external
LLM providers and inference endpoints that can be integrated with the AI
Virtual Assistant system. Model servers are synchronized with LlamaStack
to provide access to various language models.

Key Features:
- Register and manage model server configurations
- Integration with LlamaStack model providers
- Support for various LLM providers (OpenAI, Anthropic, local models, etc.)
- Configuration management for model endpoints and authentication
"""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from .. import models, schemas
from ..api.llamastack import client
from ..database import get_db
from ..services.auth import RoleChecker
from ..models import RoleEnum
from ..utils.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/model_servers", tags=["Model Servers"])


@router.post(
    "/", response_model=schemas.ModelServerRead, status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(RoleChecker([RoleEnum.admin, RoleEnum.ops]))]
)
async def create_model_server(
    server: schemas.ModelServerCreate, db: AsyncSession = Depends(get_db)
):
    """
    Create a new model server configuration.

    This endpoint registers a new model server (LLM provider) in the database
    and triggers automatic synchronization with LlamaStack to make the models available.

    Args:
        server: Model server creation data including name, provider, and configuration
        db: Database session dependency

    Returns:
        schemas.ModelServerRead: The created model server configuration

    Raises:
        HTTPException: If creation fails or validation errors occur
    """
    model_server = models.ModelServer(**server.dict())
    db.add(model_server)
    await db.commit()
    await db.refresh(model_server)

    # Auto-sync with LlamaStack after creation
    try:
        logger.info(
            f"Auto-syncing model servers after creation of: {model_server.name}"
        )
        await sync_model_servers(db)
    except Exception as e:
        logger.warning(f"Failed to auto-sync after model server creation: {str(e)}")

    return model_server


@router.get("/", response_model=List[schemas.ModelServerRead], dependencies=[Depends(RoleChecker([RoleEnum.admin, RoleEnum.ops]))])
async def read_model_servers(db: AsyncSession = Depends(get_db)):
    """
    Retrieve all registered model servers.

    This endpoint returns a list of all model server configurations stored
    in the database, including their provider details and connection settings.

    Args:
        db: Database session dependency

    Returns:
        List[schemas.ModelServerRead]: List of all model servers
    """
    result = await db.execute(select(models.ModelServer))
    return result.scalars().all()


@router.get("/{server_id}", response_model=schemas.ModelServerRead, dependencies=[Depends(RoleChecker([RoleEnum.admin, RoleEnum.ops]))])
async def read_model_server(server_id: UUID, db: AsyncSession = Depends(get_db)):
    """
    Retrieve a specific model server by its unique identifier.

    This endpoint fetches a single model server configuration using its UUID.

    Args:
        server_id: The unique identifier of the model server to retrieve
        db: Database session dependency

    Returns:
        schemas.ModelServerRead: The requested model server configuration

    Raises:
        HTTPException: 404 if the model server is not found
    """
    result = await db.execute(
        select(models.ModelServer).where(models.ModelServer.id == server_id)
    )
    server = result.scalar_one_or_none()
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")
    return server


@router.put("/{server_id}", response_model=schemas.ModelServerRead, dependencies=[Depends(RoleChecker([RoleEnum.admin, RoleEnum.ops]))])
async def update_mcp_server(
    server_id: UUID,
    server: schemas.ModelServerCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Update an existing model server configuration.

    This endpoint allows updating model server details such as name, provider,
    endpoint URL, and authentication configuration.

    Args:
        server_id: The unique identifier of the model server to update
        server: Updated model server data
        db: Database session dependency

    Returns:
        schemas.ModelServerRead: The updated model server configuration

    Raises:
        HTTPException: 404 if the model server is not found
    """
    result = await db.execute(
        select(models.ModelServer).where(models.ModelServer.id == server_id)
    )
    db_server = result.scalar_one_or_none()
    if not db_server:
        raise HTTPException(status_code=404, detail="Server not found")
    for field, value in server.dict().items():
        setattr(db_server, field, value)
    await db.commit()
    await db.refresh(db_server)

    # Auto-sync with LlamaStack after update
    try:
        logger.info(f"Auto-syncing model servers after update of: {db_server.name}")
        await sync_model_servers(db)
    except Exception as e:
        logger.warning(f"Failed to auto-sync after model server update: {str(e)}")

    return db_server


@router.delete("/{server_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(RoleChecker([RoleEnum.admin, RoleEnum.ops]))])
async def delete_model_server(server_id: UUID, db: AsyncSession = Depends(get_db)):
    """
    Delete a model server configuration.

    This endpoint removes a model server from the database. The server will
    no longer be available for use by virtual assistants.

    Args:
        server_id: The unique identifier of the model server to delete
        db: Database session dependency

    Raises:
        HTTPException: 404 if the model server is not found

    Returns:
        None: 204 No Content on successful deletion
    """
    result = await db.execute(
        select(models.ModelServer).where(models.ModelServer.id == server_id)
    )
    db_server = result.scalar_one_or_none()
    if not db_server:
        raise HTTPException(status_code=404, detail="Server not found")

    server_name = db_server.name  # Store name before deletion
    await db.delete(db_server)
    await db.commit()

    # Auto-sync with LlamaStack after deletion
    try:
        logger.info(f"Auto-syncing model servers after deletion of: {server_name}")
        await sync_model_servers(db)
    except Exception as e:
        logger.warning(f"Failed to auto-sync after model server deletion: {str(e)}")

    return None


async def sync_model_servers(db: AsyncSession):
    """
    Internal synchronization function for model servers with LlamaStack.

    This function performs the actual sync logic by fetching available models
    from LlamaStack and updating the model server database. It discovers new
    model providers and removes servers that are no longer available.

    Args:
        db: Database session for executing queries

    Returns:
        List[models.ModelServer]: List of synchronized model servers

    Raises:
        Exception: If LlamaStack communication fails or database operations fail
    """
    try:
        logger.info("Starting model server sync")
        logger.debug("Fetching models from LlamaStack")
        try:
            response = client.models.list()

            if isinstance(response, list):
                models = [item.__dict__ for item in response]
            elif isinstance(response, dict):
                models = response.get("data", [])
            elif hasattr(response, "data"):
                models = response.data
            else:
                logger.warning(f"Unexpected response type: {type(response)}")
                models = []

        except Exception as e:
            raise Exception(f"Failed to fetch models from LlamaStack: {str(e)}")

        logger.debug("Fetching existing model servers from database...")
        result = await db.execute(select(models.ModelServer))
        existing_servers = {server.name: server for server in result.scalars().all()}
        logger.debug(
            f"Found {len(existing_servers)} existing model servers: "
            f"{list(existing_servers.keys())}"
        )

        synced_servers = []

        logger.debug("Processing models...")
        for model in models:
            try:
                if not model.get("name"):
                    logger.debug(f"Skipping model without name: {model}")
                    continue

                server_data = {
                    "name": model["name"],
                    "title": model.get("title", model["name"]),
                    "description": model.get("description", ""),
                    "endpoint_url": model.get("endpoint_url", ""),
                    "configuration": model.get("configuration", {}),
                    "created_by": "admin",
                }
                logger.debug(
                    f"Processing model {model['name']} with data: {server_data}"
                )

                if model["name"] in existing_servers:
                    logger.debug(f"Updating existing model server: {model['name']}")
                    server = existing_servers[model["name"]]
                    for field, value in server_data.items():
                        setattr(server, field, value)
                else:
                    logger.debug(f"Creating new model server: {model['name']}")
                    server = models.ModelServer(**server_data)
                    db.add(server)

                synced_servers.append(server)
            except Exception as e:
                logger.error(
                    f"Error processing model {model.get('name', 'unknown')}: {str(e)}"
                )
                continue

        logger.debug("Checking for model servers to remove...")
        for server_name, server in existing_servers.items():
            if not any(m.get("name") == server_name for m in models):
                logger.debug(
                    f"Removing model server that no longer exists: {server_name}"
                )
                await db.delete(server)

        logger.debug("Committing changes to database...")
        await db.commit()

        logger.debug("Refreshing synced model servers...")
        for server in synced_servers:
            await db.refresh(server)

        logger.info(f"Sync complete. Synced {len(synced_servers)} model servers.")
        return synced_servers

    except Exception as e:
        logger.error(f"Error during sync: {str(e)}")
        raise Exception(f"Failed to sync model servers: {str(e)}")


@router.post("/sync", response_model=List[schemas.ModelServerRead], dependencies=[Depends(RoleChecker([RoleEnum.admin]))])
async def sync_model_servers_endpoint(db: AsyncSession = Depends(get_db)):
    """
    Synchronize model servers with LlamaStack model providers.

    This endpoint triggers synchronization between the local model server database
    and LlamaStack's model provider system, discovering new models and updating
    existing configurations.

    Args:
        db: Database session dependency

    Returns:
        List[schemas.ModelServerRead]: List of synchronized model servers

    Raises:
        HTTPException: If synchronization fails due to LlamaStack errors
    """
    try:
        return await sync_model_servers(db)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )
