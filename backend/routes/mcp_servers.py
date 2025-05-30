from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from uuid import UUID
from typing import List, Dict, Any

from .. import models, schemas
from ..database import get_db
from ..api.llamastack import client
from llama_stack_client.types.toolgroup_register_params import McpEndpoint

router = APIRouter(prefix="/mcp_servers", tags=["mcp_servers"])

@router.post("/", response_model=schemas.MCPServerRead, status_code=status.HTTP_201_CREATED)
async def create_mcp_server(server: schemas.MCPServerCreate, db: AsyncSession = Depends(get_db)):
    #TODO refactor mcp server model to include toolgroup_id
    mcp_server = models.MCPServer(**server.model_dump())

    # Create a new tool group in llama stack
    # Tools are discovered dynamically from the endpoint
    try:
        client.toolgroups.register(
            provider_id="model-context-protocol",
            toolgroup_id="mcp::" + mcp_server.name,
            mcp_endpoint=McpEndpoint(uri=mcp_server.endpoint_url),
        )
    except Exception as e:
            print(f"Error creating tool group in llama stack: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

    # commit to databse
    db.add(mcp_server)
    await db.commit()
    await db.refresh(mcp_server)
    return mcp_server

@router.get("/", response_model=List[schemas.MCPServerRead])
async def read_mcp_servers(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(models.MCPServer))
    return result.scalars().all()

@router.get("/{server_id}", response_model=schemas.MCPServerRead)
async def read_mcp_server(server_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(models.MCPServer).where(models.MCPServer.id == server_id))
    server = result.scalar_one_or_none()
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")
    return server

@router.put("/{server_id}", response_model=schemas.MCPServerRead)
async def update_mcp_server(server_id: UUID, server: schemas.MCPServerCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(models.MCPServer).where(models.MCPServer.id == server_id))
    db_server = result.scalar_one_or_none()
    if not db_server:
        raise HTTPException(status_code=404, detail="Server not found")
    for field, value in server.dict().items():
        setattr(db_server, field, value)
    await db.commit()
    await db.refresh(db_server)
    return db_server

@router.delete("/{server_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_mcp_server(server_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(models.MCPServer).where(models.MCPServer.id == server_id))
    db_server = result.scalar_one_or_none()
    if not db_server:
        raise HTTPException(status_code=404, detail="Server not found")
    await db.delete(db_server)
    await db.commit()
    return None

async def sync_mcp_servers(db: AsyncSession):
    try:
        print("Starting MCP server sync")
        print("Fetching tools from LlamaStack")
        try:
            response = client.tools.list()
            
            if isinstance(response, list):
                tools = [item.__dict__ for item in response]
            elif isinstance(response, dict):
                tools = response.get("data", [])
            elif hasattr(response, "data"):
                tools = response.data
            else:
                print(f"Unexpected response type: {type(response)}")
                tools = []
                
            
        except Exception as e:
            raise Exception(f"Failed to fetch tools from LlamaStack: {str(e)}")
        
        mcp_tools = [tool for tool in tools if tool.get("provider_id") == "model-context-protocol"]
        
        print("Fetching existing MCP servers from database")
        result = await db.execute(select(models.MCPServer))
        existing_servers = {server.name: server for server in result.scalars().all()}
        print(f"Found {len(existing_servers)} existing MCP servers: {list(existing_servers.keys())}")
        
        synced_servers = []
        
        for tool in mcp_tools:
            try:
                if not tool.get("identifier"):
                    continue
                    
                server_data = {
                    "name": tool["identifier"],
                    "title": tool.get("title", tool["identifier"]),
                    "description": tool.get("description", ""),
                    "endpoint_url": tool.get("metadata", {}).get("endpoint", ""),
                    "configuration": {
                        "type": tool.get("type"),
                        "provider_id": tool.get("provider_id"),
                        "toolgroup_id": tool.get("toolgroup_id"),
                        "tool_host": tool.get("tool_host"),
                        "parameters": [p.__dict__ for p in tool.get("parameters", [])]
                    }
                }
                
                if tool["identifier"] in existing_servers:
                    print(f"Updating existing MCP server: {tool['identifier']}")
                    server = existing_servers[tool["identifier"]]
                    for field, value in server_data.items():
                        setattr(server, field, value)
                else:
                    print(f"Creating new MCP server: {tool['identifier']}")
                    server = models.MCPServer(**server_data)
                    db.add(server)
                
                synced_servers.append(server)
            except Exception as e:
                print(f"Error processing MCP tool {tool.get('identifier', 'unknown')}: {str(e)}")
                continue
        
        print("Checking for MCP servers to remove...")
        for server_name, server in existing_servers.items():
            if not any(t.get("identifier") == server_name for t in mcp_tools):
                print(f"Removing MCP server that no longer exists: {server_name}")
                await db.delete(server)
        
        print("Committing changes to database...")
        await db.commit()
        
        print("Refreshing synced MCP servers...")
        for server in synced_servers:
            await db.refresh(server)
        
        print(f"Sync complete. Synced {len(synced_servers)} MCP servers.")
        return synced_servers
        
    except Exception as e:
        print(f"Error during sync: {str(e)}")
        raise Exception(f"Failed to sync MCP servers: {str(e)}")

@router.post("/sync", response_model=List[schemas.MCPServerRead])
async def sync_mcp_servers_endpoint(db: AsyncSession = Depends(get_db)):
    try:
        return await sync_mcp_servers(db)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
