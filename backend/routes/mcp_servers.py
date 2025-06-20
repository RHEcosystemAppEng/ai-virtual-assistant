"""
Model Context Protocol (MCP) Server management API endpoints.

This module provides CRUD operations for MCP servers, which are external tools
and services that can be integrated with AI agents through the Model Context Protocol.
MCP servers are automatically discovered and synchronized with LlamaStack's tool system.

Key Features:
- Register and manage MCP server configurations
- Automatic synchronization with LlamaStack tool discovery
- Tool group management and parameter configuration
- Integration with virtual assistants for enhanced capabilities
"""

from typing import List

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

router = APIRouter(prefix="/mcp_servers", tags=["mcp_servers"])


@router.post(
    "/", response_model=schemas.MCPServerRead, status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(RoleChecker([RoleEnum.admin, RoleEnum.ops]))]
)
async def create_mcp_server(
    server: schemas.MCPServerCreate, db: AsyncSession = Depends(get_db)
):
    """
    Create a new MCP server configuration.

    This endpoint registers a new MCP server in the database and triggers
    automatic synchronization with LlamaStack to discover available tools.

    Args:
        server: MCP server creation data including name, endpoint, and configuration
        db: Database session dependency

    Returns:
        schemas.MCPServerRead: The created MCP server configuration

    Raises:
        HTTPException: If creation fails or validation errors occur
    """
    db_server = models.MCPServer(**server.dict())
    db.add(db_server)
    await db.commit()
    await db.refresh(db_server)

    # Auto-sync with LlamaStack after creation
    try:
        logger.info(f"Auto-syncing MCP servers after creation of: {db_server.name}")
        await sync_mcp_servers(db)
    except Exception as e:
        logger.warning(f"Failed to auto-sync after MCP server creation: {str(e)}")

    return db_server


@router.get("/", response_model=List[schemas.MCPServerRead], dependencies=[Depends(RoleChecker([RoleEnum.admin, RoleEnum.ops]))])
async def read_mcp_servers(db: AsyncSession = Depends(get_db)):
    """
    Retrieve all registered MCP servers.

    This endpoint returns a list of all MCP server configurations stored
    in the database, including their connection details and tool metadata.

    Args:
        db: Database session dependency

    Returns:
        List[schemas.MCPServerRead]: List of all MCP servers
    """
    result = await db.execute(select(models.MCPServer))
    return result.scalars().all()


@router.get("/{toolgroup_id}", response_model=schemas.MCPServerRead, dependencies=[Depends(RoleChecker([RoleEnum.admin, RoleEnum.ops]))])
async def read_mcp_server(toolgroup_id: str, db: AsyncSession = Depends(get_db)):
    """
    Retrieve a specific MCP server by its tool group identifier.

    This endpoint fetches a single MCP server configuration using its
    unique tool group ID, which corresponds to the LlamaStack tool group.

    Args:
        toolgroup_id: The unique tool group identifier of the MCP server
        db: Database session dependency

    Returns:
        schemas.MCPServerRead: The requested MCP server configuration

    Raises:
        HTTPException: 404 if the MCP server is not found
    """
    result = await db.execute(
        select(models.MCPServer).where(models.MCPServer.toolgroup_id == toolgroup_id)
    )
    server = result.scalar_one_or_none()
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")
    return server


@router.put("/{toolgroup_id}", response_model=schemas.MCPServerRead, dependencies=[Depends(RoleChecker([RoleEnum.admin, RoleEnum.ops]))])
async def update_mcp_server(
    toolgroup_id: str,
    server: schemas.MCPServerCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Update an existing MCP server configuration.

    This endpoint allows updating MCP server details such as name, description,
    endpoint URL, and configuration parameters.

    Args:
        toolgroup_id: The tool group identifier of the MCP server to update
        server: Updated MCP server data
        db: Database session dependency

    Returns:
        schemas.MCPServerRead: The updated MCP server configuration

    Raises:
        HTTPException: 404 if the MCP server is not found
    """
    result = await db.execute(
        select(models.MCPServer).where(models.MCPServer.toolgroup_id == toolgroup_id)
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
        logger.info(f"Auto-syncing MCP servers after update of: {db_server.name}")
        await sync_mcp_servers(db)
    except Exception as e:
        logger.warning(f"Failed to auto-sync after MCP server update: {str(e)}")

    return db_server


@router.delete("/{toolgroup_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(RoleChecker([RoleEnum.admin, RoleEnum.ops]))])
async def delete_mcp_server(toolgroup_id: str, db: AsyncSession = Depends(get_db)):
    """
    Delete an MCP server configuration.

    This endpoint removes an MCP server from the database. The server will
    no longer be available for use by virtual assistants.

    Args:
        toolgroup_id: The tool group identifier of the MCP server to delete
        db: Database session dependency

    Raises:
        HTTPException: 404 if the MCP server is not found

    Returns:
        None: 204 No Content on successful deletion
    """
    result = await db.execute(
        select(models.MCPServer).where(models.MCPServer.toolgroup_id == toolgroup_id)
    )
    db_server = result.scalar_one_or_none()
    if not db_server:
        raise HTTPException(status_code=404, detail="Server not found")

    server_name = db_server.name  # Store name before deletion
    await db.delete(db_server)
    await db.commit()

    # Auto-sync with LlamaStack after deletion
    try:
        logger.info(f"Auto-syncing MCP servers after deletion of: {server_name}")
        await sync_mcp_servers(db)
    except Exception as e:
        logger.warning(f"Failed to auto-sync after MCP server deletion: {str(e)}")

    return None


async def sync_mcp_servers(db: AsyncSession):
    """
    Internal synchronization function for MCP servers with LlamaStack.

    This function performs the actual sync logic by fetching available tools
    from LlamaStack and updating the MCP server database. It discovers new
    MCP servers and removes servers that are no longer available.

    Args:
        db: Database session for executing queries

    Returns:
        List[models.MCPServer]: List of synchronized MCP servers

    Raises:
        Exception: If LlamaStack communication fails or database operations fail
    """
    try:
        logger.info("Starting MCP server sync")
        logger.debug("Fetching tools from LlamaStack")
        try:
            response = client.tools.list()

            if isinstance(response, list):
                tools = [item.__dict__ for item in response]
            elif isinstance(response, dict):
                tools = response.get("data", [])
            elif hasattr(response, "data"):
                tools = response.data
            else:
                logger.warning(f"Unexpected response type: {type(response)}")
                tools = []

        except Exception as e:
            raise Exception(f"Failed to fetch tools from LlamaStack: {str(e)}")

        mcp_tools = [
            tool
            for tool in tools
            if tool.get("provider_id") == "model-context-protocol"
        ]

        logger.debug("Fetching existing MCP servers from database")
        result = await db.execute(select(models.MCPServer))
        existing_servers = {
            server.toolgroup_id: server for server in result.scalars().all()
        }
        logger.debug(
            f"Found {len(existing_servers)} existing MCP servers: "
            f"{list(existing_servers.keys())}"
        )

        synced_servers = []

        for tool in mcp_tools:
            try:
                if not tool.get("identifier"):
                    continue

                server_data = {
                    "name": tool["identifier"],
                    "description": tool.get("description", ""),
                    "endpoint_url": tool.get("metadata", {}).get("endpoint", ""),
                    "toolgroup_id": tool.get("toolgroup_id"),
                    "configuration": {
                        "type": tool.get("type"),
                        "provider_id": tool.get("provider_id"),
                        "tool_host": tool.get("tool_host"),
                        "parameters": [p.__dict__ for p in tool.get("parameters", [])],
                    },
                }

                if tool.get("toolgroup_id") in existing_servers:
                    logger.debug(
                        f"Updating existing MCP server: {tool.get('toolgroup_id')}"
                    )
                    server = existing_servers[tool.get("toolgroup_id")]
                    for field, value in server_data.items():
                        setattr(server, field, value)
                else:
                    logger.debug(f"Creating new MCP server: {tool.get('toolgroup_id')}")
                    server = models.MCPServer(**server_data)
                    db.add(server)

                synced_servers.append(server)
            except Exception as e:
                logger.error(
                    "Error processing MCP tool "
                    f"{tool.get('identifier', 'unknown')}: {str(e)}"
                )
                continue

        logger.debug("Checking for MCP servers to remove...")
        for toolgroup_id, server in existing_servers.items():
            if not any(t.get("toolgroup_id") == toolgroup_id for t in mcp_tools):
                logger.debug(
                    f"Removing MCP server that no longer exists: {toolgroup_id}"
                )
                await db.delete(server)

        logger.debug("Committing changes to database...")
        await db.commit()

        logger.debug("Refreshing synced MCP servers...")
        for server in synced_servers:
            await db.refresh(server)

        logger.info(f"Sync complete. Synced {len(synced_servers)} MCP servers.")
        return synced_servers

    except Exception as e:
        logger.error(f"Error during sync: {str(e)}")
        raise Exception(f"Failed to sync MCP servers: {str(e)}")


@router.post("/sync", response_model=List[schemas.MCPServerRead], dependencies=[Depends(RoleChecker([RoleEnum.admin]))])
async def sync_mcp_servers_endpoint(db: AsyncSession = Depends(get_db)):
    """
    Synchronize MCP servers with LlamaStack tool discovery.

    This endpoint triggers synchronization between the local MCP server database
    and LlamaStack's tool system, discovering new MCP servers and updating
    existing configurations.

    Args:
        db: Database session dependency

    Returns:
        List[schemas.MCPServerRead]: List of synchronized MCP servers

    Raises:
        HTTPException: If synchronization fails due to LlamaStack errors
    """
    try:
        return await sync_mcp_servers(db)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )
