"""
Tools API endpoints for managing MCP servers and builtin tools.

This module provides endpoints to retrieve and manage tool groups, including
both MCP (Model Context Protocol) servers and LlamaStack builtin tools.
"""

from typing import Any, Dict, List

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from .. import models
from ..api.llamastack import client
from ..database import get_db
from ..services.auth import RoleChecker
from ..models import RoleEnum
from ..utils.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/tools", tags=["tools"])


@router.get("/", response_model=List[Dict[str, Any]], dependencies=[Depends(RoleChecker([RoleEnum.admin, RoleEnum.ops]))])
async def get_all_tool_groups(db: AsyncSession = Depends(get_db)):
    """
    Get all available tool groups from both MCP servers and LlamaStack builtin tools.

    This endpoint combines tool groups from:
    - MCP servers stored in the database
    - Builtin tools available through LlamaStack

    Args:
        db: Database session dependency

    Returns:
        List of tool groups with their metadata and configuration
    """
    tool_groups = {}

    # Get all MCP servers from database
    mcp_result = await db.execute(select(models.MCPServer))
    mcp_servers = mcp_result.scalars().all()

    for server in mcp_servers:
        tool_groups[server.toolgroup_id] = {
            "toolgroup_id": server.toolgroup_id,
            "name": server.name,
            "description": server.description,
            "endpoint_url": server.endpoint_url,
            "configuration": server.configuration,
            "created_at": server.created_at.isoformat() if server.created_at else None,
            "updated_at": server.updated_at.isoformat() if server.updated_at else None,
        }

    # Get builtin tools from LlamaStack
    try:
        response = client.tools.list()
        if isinstance(response, list):
            llamastack_tools = [item.__dict__ for item in response]
        elif isinstance(response, dict):
            llamastack_tools = response.get("data", [])
        elif hasattr(response, "data"):
            llamastack_tools = response.data
        else:
            llamastack_tools = []

        # Filter for builtin tools (not MCP)
        builtin_tools = [
            tool
            for tool in llamastack_tools
            if tool.get("provider_id") != "model-context-protocol"
        ]

        # Group builtin tools by toolgroup_id
        for tool in builtin_tools:
            toolgroup_id = tool.get("toolgroup_id", tool.get("identifier"))
            if toolgroup_id and toolgroup_id not in tool_groups:
                tool_groups[toolgroup_id] = {
                    "toolgroup_id": toolgroup_id,
                    "name": toolgroup_id,  # Use toolgroup_id as display name
                    "description": tool.get("description", f"Tools for {toolgroup_id}"),
                    "endpoint_url": None,
                    "configuration": tool.get("metadata", {}),
                    "created_at": None,
                    "updated_at": None,
                }
    except Exception as e:
        logger.warning(f"Failed to fetch builtin tools from LlamaStack: {str(e)}")

    return list(tool_groups.values())
