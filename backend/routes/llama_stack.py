"""
LlamaStack Integration API endpoints for direct LlamaStack operations.

This module provides endpoints for interacting directly with LlamaStack services,
including LLM model management, chat interactions, and session handling. It serves
as the primary bridge between the frontend and LlamaStack infrastructure.

Key Features:
- List available LLM models from LlamaStack
- Stream chat responses with session management
- Automatic session metadata storage for UI persistence
- Integration with virtual assistant configurations
- Background task processing for database operations

The module handles real-time streaming chat interactions while maintaining
session state in both LlamaStack and the local database for UI features
like conversation history sidebars.
"""

import json
import logging
from typing import Any, Dict, List, Literal, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db

from .. import models
from ..api.llamastack import client
from .chat import Chat
from .virtual_assistants import read_virtual_assistant
from ..services.auth import RoleChecker, get_current_user
from ..services.agent_service import AgentService
from ..models import RoleEnum
from .. import schemas


class Message(BaseModel):
    """
    Standard message format for LlamaStack chat interactions.

    Attributes:
        role: The role of the message sender ('user', 'assistant', or 'system')
        content: The text content of the message
    """

    role: Literal["user", "assistant", "system"]
    content: str


class VAChatMessage(BaseModel):
    """
    Extended chat message format for Virtual Assistant interface compatibility.

    This format extends the basic Message format to include additional fields
    required by frontend chat interfaces and streaming implementations.

    Attributes:
        id: Optional unique identifier for the message
        role: The role of the message sender ('user', 'assistant', or 'system')
        content: The text content of the message
        parts: List of message parts for streaming/chunked content display
    """

    id: Optional[str] = None
    role: Literal["user", "assistant", "system"]
    content: str
    parts: List[str] = []  # Add parts field to match useChat format


log = logging.getLogger(__name__)

router = APIRouter(prefix="/llama_stack", tags=["llama_stack"])


# Initialize LlamaStack client
@router.get("/llms", response_model=List[Dict[str, Any]], dependencies=[Depends(RoleChecker([RoleEnum.admin]))])
async def get_llms():
    """
    Retrieve all available Large Language Models from LlamaStack (Admin only).

    Fetches the complete list of LLM models available in the LlamaStack instance,
    filtering for models with 'llm' API type and formatting them for frontend
    consumption. Used by chat interfaces to populate model selection dropdowns.

    Returns:
        List of dictionaries containing LLM model information:
        - model_name: The model identifier
        - provider_resource_id: Provider-specific resource identifier
        - model_type: API model type (always 'llm' for this endpoint)

    Raises:
        HTTPException: 502 if LlamaStack is unreachable, 500 for other errors
    """
    try:
        log.info(f"Attempting to fetch models from LlamaStack at {client.base_url}")
        try:
            models = client.models.list()
            log.info(f"Received response from LlamaStack: {models}")
        except Exception as client_error:
            log.error(f"Error calling LlamaStack API: {str(client_error)}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Failed to connect to LlamaStack API: {str(client_error)}",
            )

        if not models:
            log.warning("No models returned from LlamaStack")
            return []

        llms = []
        for model in models:
            try:
                if model.api_model_type == "llm":
                    llm_config = {
                        "model_name": str(model.identifier),
                        "provider_resource_id": model.provider_resource_id,
                        "model_type": model.api_model_type,
                    }
                    llms.append(llm_config)
            except AttributeError as ae:
                log.error(
                    f"Error processing model data: {str(ae)}. Model data: {model}"
                )
                continue

        log.info(f"Successfully processed {len(llms)} LLM models")
        return llms

    except Exception as e:
        log.error(f"Unexpected error in get_llms: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}",
        )


@router.get("/knowledge_bases", response_model=List[Dict[str, Any]], dependencies=[Depends(RoleChecker([RoleEnum.admin]))])
async def get_knowledge_bases():
    """
    Retrieve all available knowledge bases from LlamaStack vector databases (Admin only).

    Fetches the complete list of vector databases available in LlamaStack,
    which represent knowledge bases that can be used for RAG (Retrieval
    Augmented Generation) operations with virtual assistants.

    Returns:
        List of dictionaries containing knowledge base information:
        - kb_name: The knowledge base identifier
        - provider_resource_id: Provider-specific resource identifier

    Raises:
        HTTPException: If LlamaStack communication fails
    """
    try:
        kbs = client.vector_dbs.list()
        return [
            {
                "kb_name": str(kb.identifier),
                "provider_resource_id": kb.provider_resource_id,
                "provider_id": kb.provider_id,
                "type": kb.type,
                "embedding_model": kb.embedding_model,
            }
            for kb in kbs
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tools", response_model=List[Dict[str, Any]], dependencies=[Depends(RoleChecker([RoleEnum.admin]))])
async def get_tools():
    """
    Retrieve all available MCP (Model Context Protocol) servers from LlamaStack (Admin only).

    Fetches tool groups that represent MCP servers configured in LlamaStack.
    These servers provide external tools and capabilities that can be used
    by virtual assistants during conversations.

    Returns:
        List of dictionaries containing MCP server information:
        - id: The tool group identifier
        - name: Provider resource identifier
        - title: Provider identifier

    Raises:
        HTTPException: If LlamaStack communication fails
    """
    try:
        servers = client.toolgroups.list()
        return [
            {
                "id": str(server.identifier),
                "name": server.provider_resource_id,
                "title": server.provider_id,
                "toolgroup_id": str(server.identifier),
            }
            for server in servers
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/safety_models", response_model=List[Dict[str, Any]], dependencies=[Depends(RoleChecker([RoleEnum.admin]))])
async def get_safety_models():
    """
    Retrieve all available safety models from LlamaStack (Admin only).

    Fetches models specifically designed for content safety and moderation.
    These models can be used to filter harmful content, detect inappropriate
    requests, and ensure safe AI interactions.

    Returns:
        List of dictionaries containing safety model information:
        - id: The model identifier
        - name: Provider resource identifier
        - model_type: Model type (always 'safety')

    Raises:
        HTTPException: If LlamaStack communication fails
    """
    try:
        models = client.models.list()
        safety_models = []
        for model in models:
            if model.model_type == "safety":
                safety_model = {
                    "id": str(model.identifier),
                    "name": model.provider_resource_id,
                    "model_type": model.type,
                }
                safety_models.append(safety_model)
        return safety_models
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/embedding_models", response_model=List[Dict[str, Any]], dependencies=[Depends(RoleChecker([RoleEnum.admin]))])
async def get_embedding_models():
    """
    Retrieve all available embedding models from LlamaStack (Admin only).

    Fetches models designed for generating vector embeddings from text.
    These models are used for knowledge base indexing, semantic search,
    and RAG (Retrieval Augmented Generation) operations.

    Returns:
        List of dictionaries containing embedding model information:
        - name: The model identifier
        - provider_resource_id: Provider-specific resource identifier
        - model_type: Model type (always 'embedding')

    Raises:
        HTTPException: If LlamaStack communication fails
    """
    try:
        models = client.models.list()
        embedding_models = []
        for model in models:
            if model.model_type == "embedding":
                embedding_model = {
                    "name": str(model.identifier),
                    "provider_resource_id": model.provider_resource_id,
                    "model_type": model.type,
                }
                embedding_models.append(embedding_model)
        return embedding_models
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/shields", response_model=List[Dict[str, Any]], dependencies=[Depends(RoleChecker([RoleEnum.admin]))])
async def get_shields():
    """
    Retrieve all available safety shields from LlamaStack (Admin only).

    Fetches shield configurations used for content filtering and safety
    enforcement. Shields provide pre-configured safety policies that can
    be applied to AI interactions to prevent harmful content generation.

    Returns:
        List of dictionaries containing shield information:
        - id: The shield identifier
        - name: Provider resource identifier
        - model_type: Shield type identifier

    Raises:
        HTTPException: If LlamaStack communication fails
    """
    try:
        shields = client.shields.list()
        shields_list = []
        for shield in shields:
            shield = {
                "id": str(shield.identifier),
                "name": shield.provider_resource_id,
                "model_type": shield.type,
            }
            shields_list.append(shield)
        return shields_list
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/providers", response_model=List[Dict[str, Any]], dependencies=[Depends(RoleChecker([RoleEnum.admin]))])
async def get_providers():
    """
    Retrieve all available providers from LlamaStack (Admin only).

    Fetches the complete list of providers configured in LlamaStack,
    including their configurations and supported APIs. Providers are
    the underlying services that supply models, tools, and other capabilities.

    Returns:
        List of dictionaries containing provider information:
        - provider_id: The provider identifier
        - provider_type: Type of provider (e.g., 'meta-reference', 'openai')
        - config: Provider-specific configuration parameters
        - api: List of APIs supported by this provider

    Raises:
        HTTPException: If LlamaStack communication fails
    """
    try:
        providers = client.providers.list()
        return [
            {
                "provider_id": str(provider.provider_id),
                "provider_type": provider.provider_type,
                "config": provider.config if hasattr(provider, "config") else {},
                "api": provider.api,
            }
            for provider in providers
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class ChatRequest(BaseModel):
    """
    Request model for LlamaStack chat interactions.

    Defines the structure for chat requests sent to the LlamaStack chat endpoint.
    Includes virtual assistant selection, conversation history, streaming preferences,
    and session management.

    Attributes:
        virtualAssistantId: The ID of the virtual assistant/agent to use for chat
        messages: List of conversation messages (user, assistant, system)
        stream: Whether to stream the response (default: False)
        sessionId: Optional session ID for conversation continuity
    """

    virtualAssistantId: str
    messages: list[Message]
    stream: bool = False
    sessionId: Optional[str] = None


@router.post("/chat")
async def chat(
    request: ChatRequest,
    background_task: BackgroundTasks,
    current_user: schemas.UserRead = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Main chat endpoint for streaming conversations with LlamaStack agents (with user access verification).

    Handles real-time chat interactions by streaming responses from LlamaStack
    agents while maintaining session state. Automatically saves session metadata
    to the database for UI features like conversation history sidebars.
    
    Users can only chat with agents they have been assigned.

    The endpoint validates the virtual assistant exists, requires a session ID,
    and streams responses in Server-Sent Events format. Session metadata is
    saved asynchronously to avoid blocking the chat response.

    Args:
        request: ChatRequest containing assistant ID, messages, and session info
        background_task: FastAPI background tasks for async metadata saving
        current_user: Current authenticated user
        db: Database session for metadata operations

    Returns:
        StreamingResponse: Server-Sent Events stream of chat responses

    Raises:
        HTTPException:
            - 404 if virtual assistant not found in LlamaStack
            - 403 if user doesn't have access to the agent
            - 400 if session ID is missing
            - 500 for internal server errors during chat processing
    """
    try:
        log.info(f"Received chat request from user {current_user.id}: {request.model_dump()}")

        # Verify user has access to this agent FIRST
        has_access = await AgentService.verify_user_agent_access_complete(
            agent_id=request.virtualAssistantId,
            user_id=str(current_user.id),
            user_role=current_user.role.value,
            db=db
        )
        
        if not has_access:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to this agent"
            )

        # Get the agent directly from LlamaStack
        try:
            agent = client.agents.retrieve(agent_id=request.virtualAssistantId)
            log.info(f"Found agent: {agent.agent_id}")
        except Exception as e:
            log.error(
                f"Agent {request.virtualAssistantId} not found in LlamaStack: {str(e)}"
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Virtual assistant {request.virtualAssistantId} not found",
            )

        # Use the agent_id directly from LlamaStack
        agent_id = request.virtualAssistantId

        # Session ID is required - no session creation in chat endpoint
        session_id = request.sessionId
        if not session_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Session ID is required. Please select or create a "
                    "session first."
                ),
            )

        log.info(f"User {current_user.id} chatting with agent: {agent_id} in session: {session_id}")

        # Create stateless Chat instance (no longer needs assistant or session_state)
        chat = Chat(log)

        def generate_response():
            try:
                # Get the last user message
                if len(request.messages) > 0:
                    last_message = request.messages[
                        -1
                    ]  # Get last message instead of popping
                    # Stream response using new stateless interface
                    for chunk in chat.stream(
                        agent_id, session_id, last_message.content
                    ):
                        # Send the chunk directly since it's already
                        # properly formatted JSON
                        yield f"data: {chunk}\n\n"

                # End of stream
                yield "data: [DONE]\n\n"

                # Save session metadata to database
                background_task.add_task(
                    save_session_metadata, db, session_id, agent_id, request.messages
                )

            except Exception as e:
                log.error(f"Error in stream: {str(e)}")
                yield f'data: {{"type":"error","content":"Error: {str(e)}"}}\n\n'

        return StreamingResponse(generate_response(), media_type="text/event-stream")

    except Exception as e:
        log.error(f"Error in chat endpoint: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


async def save_session_metadata(
    db: AsyncSession, session_id: str, agent_id: str, messages: list
):
    """
    Save session metadata to database for UI sidebar display.

    Asynchronously saves or updates session information in the database to support
    frontend features like conversation history sidebars. Generates meaningful
    session titles from the first user message and fetches agent display names.

    This function is called as a background task to avoid blocking chat responses
    while ensuring session metadata is available for the UI.

    Args:
        db: Database session for executing queries
        session_id: Unique identifier for the chat session
        agent_id: ID of the virtual assistant/agent used in the session
        messages: List of conversation messages for title generation

    Note:
        Errors in metadata saving are logged but don't affect chat functionality.
        Uses INSERT ... ON CONFLICT DO UPDATE for idempotent session storage.
    """
    try:
        # Generate title from first user message
        title = "New Chat"
        if messages:
            # Find first user message for title
            for msg in messages:
                if msg.role == "user":
                    content = msg.content
                    title = content[:50] + "..." if len(content) > 50 else content
                    break

        # Get agent name
        agent_name = "Unknown Agent"
        try:
            # Fetch agent details from LlamaStack
            agent_details = await read_virtual_assistant(agent_id)
            agent_name = (
                agent_details.name if agent_details.name else f"Agent {agent_id[:8]}..."
            )
        except Exception as e:
            log.error(f"Error fetching agent details: {e}")
            agent_name = f"Agent {agent_id[:8]}..."

        # Insert or update session metadata
        stmt = insert(models.ChatSession).values(
            id=session_id,
            title=title,
            agent_name=agent_name,
            session_state=json.dumps({"agent_id": agent_id, "session_id": session_id}),
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["id"],
            set_=dict(
                title=stmt.excluded.title,
                agent_name=stmt.excluded.agent_name,
                updated_at=stmt.excluded.updated_at,
            ),
        )

        await db.execute(stmt)
        await db.commit()
        log.info(f"Saved session metadata for {session_id}")

    except Exception as e:
        log.error(f"Error saving session metadata: {e}")
        await db.rollback()
