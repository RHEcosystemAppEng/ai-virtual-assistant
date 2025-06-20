"""
Virtual Assistants API endpoints for managing AI agents through LlamaStack.

This module provides CRUD operations for virtual assistants (AI agents) that are
managed through the LlamaStack platform. Virtual assistants can be configured with
different models, tools, knowledge bases, and safety shields.
"""

from typing import List
from datetime import datetime

from fastapi import APIRouter, HTTPException, status, Depends
from llama_stack_client.lib.agents.agent import AgentUtils

from .. import schemas
from ..api.llamastack import client
from ..utils.logging_config import get_logger
from ..virtual_agents.agent_model import VirtualAgent
from ..services.auth import RoleChecker, get_current_user
from ..models import User as UserModel, RoleEnum
from sqlalchemy.future import select
from ..services.agent_service import AgentService
from ..database import get_db

logger = get_logger(__name__)

router = APIRouter(prefix="/virtual_assistants", tags=["virtual_assistants"])


def get_strategy(temperature, top_p):
    """
    Determines the sampling strategy for the LLM based on temperature.

    Args:
        temperature: Temperature parameter for sampling (0 = greedy)
        top_p: Top-p parameter for nucleus sampling

    Returns:
        Dict containing the sampling strategy configuration
    """
    return (
        {"type": "greedy"}
        if temperature == 0
        else {"type": "top_p", "temperature": temperature, "top_p": top_p}
    )


@router.post(
    "/",
    response_model=schemas.VirtualAssistantRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(RoleChecker([RoleEnum.admin]))]
)
async def create_virtual_assistant(
    va: schemas.VirtualAssistantCreate,
    current_admin: schemas.UserRead = Depends(get_current_user)
):
    """
    Create a new virtual assistant agent in LlamaStack.

    Args:
        va: Virtual assistant configuration including model, tools, and settings

    Returns:
        The created virtual assistant with generated ID

    Raises:
        HTTPException: If creation fails
    """
    try:
        sampling_params = {
            "strategy": get_strategy(va.temperature, va.top_p),
            "max_tokens": va.max_tokens,
            "repetition_penalty": va.repetition_penalty,
        }

        tools = []
        for i, tool_info in enumerate(va.tools):
            if tool_info.toolgroup_id == "builtin::rag":
                if len(va.knowledge_base_ids) > 0:
                    tool_dict = dict(
                        name="builtin::rag",
                        args={
                            "vector_db_ids": list(va.knowledge_base_ids),
                        },
                    )
                    tools.append(tool_dict)
            else:
                tools.append(tool_info.toolgroup_id)

        agent_config = AgentUtils.get_agent_config(
            model=va.model_name,
            instructions=va.prompt,
            tools=tools,
            sampling_params=sampling_params,
            max_infer_iters=va.max_infer_iters,
            input_shields=va.input_shields,
            output_shields=va.output_shields,
        )
        agent_config["name"] = va.name
        
        # Add template metadata for admin-created agents
        if "metadata" not in agent_config:
            agent_config["metadata"] = {}
            
        agent_config["metadata"].update({
            "is_template": True,
            "created_by": str(current_admin.id),
            "created_by_email": current_admin.email,
            "created_at": datetime.now().isoformat()
        })

        agentic_system_create_response = client.agents.create(
            agent_config=agent_config,
        )

        return schemas.VirtualAssistantRead(
            id=agentic_system_create_response.agent_id,
            name=va.name,
            input_shields=va.input_shields,
            output_shields=va.output_shields,
            prompt=va.prompt,
            model_name=va.model_name,
            knowledge_base_ids=va.knowledge_base_ids,
            tools=va.tools,
        )

    except Exception as e:
        logger.error(f"ERROR: create_virtual_assistant: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"An unexpected error occurred: {str(e)}"
        )


def to_va_response(agent: VirtualAgent):
    """
    Convert a LlamaStack VirtualAgent to API response format.

    Args:
        agent: VirtualAgent object from LlamaStack

    Returns:
        VirtualAssistantRead schema with formatted data
    """
    tools = []
    kb_ids = []

    for toolgroup in agent.agent_config.get("toolgroups", []):
        if isinstance(toolgroup, dict):
            tool_name = toolgroup.get("name")
            tools.append(schemas.ToolAssociationInfo(toolgroup_id=tool_name))
            if tool_name == "builtin::rag":
                kb_ids = toolgroup.get("args", {}).get("vector_db_ids", [])
                logger.debug("Assigned vector_db_ids:", kb_ids)
        elif isinstance(toolgroup, str):
            tools.append(schemas.ToolAssociationInfo(toolgroup_id=toolgroup))

    id = agent.agent_id
    name = agent.agent_config.get("name", "")
    name = name if name is not None else "Missing Name"
    input_shields = agent.agent_config.get("input_shields", [])
    output_shields = agent.agent_config.get("output_shields", [])
    prompt = agent.agent_config.get("instructions", "")
    model_name = agent.agent_config.get("model", "")

    return schemas.VirtualAssistantRead(
        id=id,
        name=name,
        input_shields=input_shields,
        output_shields=output_shields,
        prompt=prompt,
        model_name=model_name,
        knowledge_base_ids=kb_ids,
        tools=tools,  # Use the 'tools' field with the correct structure
    )


@router.get("/", response_model=List[schemas.VirtualAssistantRead], dependencies=[Depends(RoleChecker([RoleEnum.admin]))])
async def get_virtual_assistants():
    """
    Retrieve all virtual assistants from LlamaStack (Admin only).

    Returns:
        List of all virtual assistants configured in the system
    """
    # get all virtual assitants or agents from llama stack
    agents = client.agents.list()
    response_list = []
    for agent in agents:
        response_list.append(to_va_response(agent))
    return response_list


@router.get("/{va_id}", response_model=schemas.VirtualAssistantRead, dependencies=[Depends(RoleChecker([RoleEnum.admin]))])
async def read_virtual_assistant(va_id: str):
    """
    Retrieve a specific virtual assistant by ID (Admin only).

    Args:
        va_id: The unique identifier of the virtual assistant

    Returns:
        The virtual assistant configuration and metadata

    Raises:
        HTTPException: If virtual assistant not found
    """
    agent = client.agents.retrieve(agent_id=va_id)
    return to_va_response(agent)


# @router.put("/{va_id}", response_model=schemas.VirtualAssistantRead)
# async def update_virtual_assistant(va_id: str):
#     pass


@router.delete("/{va_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(RoleChecker([RoleEnum.admin]))])
async def delete_virtual_assistant(va_id: str):
    """
    Delete a virtual assistant from LlamaStack (Admin only).

    Args:
        va_id: The unique identifier of the virtual assistant to delete

    Returns:
        None (204 No Content status)
    """
    client.agents.delete(agent_id=va_id)
    return None


@router.get("/templates", response_model=List[schemas.AgentTemplateResponse], dependencies=[Depends(RoleChecker([RoleEnum.admin]))])
async def get_agent_templates(db=Depends(get_db)):
    """
    Get all available agent templates for assignment (Admin only).

    This endpoint returns all virtual assistants that can be used as templates
    for assignment to users. Only admin users can access this endpoint.
    
    Uses database-based approach for efficiency: queries admin users and extracts
    template agents from their agent_ids JSON column.

    Returns:
        List[schemas.AgentTemplateResponse]: List of agent templates with metadata

    Raises:
        HTTPException: If retrieval fails
    """
    try:
        
        # Get all admin users
        result = await db.execute(
            select(UserModel).filter(UserModel.role == RoleEnum.admin)
        )
        admin_users = result.scalars().all()
        
        # Extract all template agents from admin users
        templates = []
        template_ids_seen = set()  # Avoid duplicates
        
        for admin_user in admin_users:
            if not admin_user.agent_ids:
                continue
                
            # Normalize agent_ids to ensure consistent format
            normalized_agents = AgentService.normalize_agent_ids(admin_user.agent_ids)
            
            for agent_assignment in normalized_agents:
                # Only include template agents, avoid duplicates
                if (agent_assignment.get("type") == "template" and 
                    agent_assignment["agent_id"] not in template_ids_seen):
                    
                    template_ids_seen.add(agent_assignment["agent_id"])
                    
                    # Try to get agent name from LlamaStack for display
                    try:
                        agent = client.agents.retrieve(agent_id=agent_assignment["agent_id"])
                        agent_name = agent.agent_config.get("name", "Unnamed Assistant")
                        agent_model = agent.agent_config.get("model", "Unknown")
                        tool_count = len(agent.agent_config.get("toolgroups", []))
                    except Exception as e:
                        # Fallback if agent doesn't exist in LlamaStack
                        logger.warning(f"Could not retrieve agent {agent_assignment['agent_id']} from LlamaStack: {e}")
                        agent_name = f"Template {agent_assignment['agent_id'][:8]}..."
                        agent_model = "Unknown"
                        tool_count = 0
                    
                    template = schemas.AgentTemplateResponse(
                        agent_id=agent_assignment["agent_id"],
                        name=agent_name,
                        description=f"Model: {agent_model}, Tools: {tool_count}",
                        created_by=agent_assignment.get("assigned_by", "unknown"),
                        created_by_email=admin_user.email,
                        created_at=agent_assignment.get("assigned_at", "Unknown")
                    )
                    templates.append(template)
        
        # Sort by name for consistent ordering
        templates.sort(key=lambda x: x.name)
        
        logger.info(f"Retrieved {len(templates)} agent templates from database")
        return templates

    except Exception as e:
        logger.error(f"Error retrieving agent templates from database: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve agent templates: {str(e)}"
        )
