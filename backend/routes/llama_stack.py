import asyncio

from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.responses import StreamingResponse
#from llama_stack_client.types import UserMessage, SystemMessage, CompletionMessage, Tool
from typing import List, Dict, Any, AsyncGenerator, Literal, Optional, AsyncIterable
import logging
from pydantic import BaseModel
import json
from sqlalchemy.exc import StatementError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from backend.models import VirtualAssistant, VirtualAssistantTool, VirtualAssistantKnowledgeBase, KnowledgeBase, ChatSession
from backend.database import get_db
from uuid import UUID
import time
from .chat import Chat
from ..api.llamastack import client
from .. import models
from uuid import uuid4
from fastapi import BackgroundTasks
from ..database import SessionLocal


class Message(BaseModel):
    role: Literal['user', 'assistant', 'system']
    content: str

class VAChatMessage(BaseModel):
    id: Optional[str] = None
    role: Literal['user', 'assistant', 'system']
    content: str
    parts: List[str] = []  # Add parts field to match useChat format

log = logging.getLogger(__name__)

router = APIRouter(prefix="/llama_stack", tags=["llama_stack"])

# Initialize LlamaStack client
@router.get("/llms", response_model=List[Dict[str, Any]])
async def get_llms():
    """Get available LLMs from LlamaStack"""
    try:
        log.info(f"Attempting to fetch models from LlamaStack at {client.base_url}")
        try:
            models = client.models.list()
            log.info(f"Received response from LlamaStack: {models}")
        except Exception as client_error:
            log.error(f"Error calling LlamaStack API: {str(client_error)}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Failed to connect to LlamaStack API: {str(client_error)}"
            )

        if not models:
            log.warning("No models returned from LlamaStack")
            return []

        llms = []
        for model in models:
            try:
                if model.model_type == "llm":
                    llm_config = {
                        "id": str(model.identifier),
                        "name": model.provider_resource_id,
                        "model_type": model.model_type,
                    }
                    llms.append(llm_config)
            except AttributeError as ae:
                log.error(f"Error processing model data: {str(ae)}. Model data: {model}")
                continue

        log.info(f"Successfully processed {len(llms)} LLM models")
        return llms

    except Exception as e:
        log.error(f"Unexpected error in get_llms: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )

@router.get("/knowledge_bases", response_model=List[Dict[str, Any]])
async def get_knowledge_bases():
    """Get available knowledge bases from LlamaStack"""
    try:
        kbs = client.vector_dbs.list()
        return [{
            "id": str(kb.identifier),
            "name": kb.provider_resource_id,
            "provider_id": kb.provider_id,
            "type": kb.type,
            "embedding_model": kb.embedding_model,
        } for kb in kbs]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/mcp_servers", response_model=List[Dict[str, Any]])
async def get_mcp_servers():
    """Get available MCP servers from LlamaStack"""
    try:
        servers = client.toolgroups.list()
        return [{
            "id": str(server.identifier),
            "name": server.provider_resource_id,
            "title": server.provider_id,
        } for server in servers]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/safety_models", response_model=List[Dict[str, Any]])
async def get_safety_models():
    """Get available safety models from LlamaStack"""
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

@router.get("/embedding_models", response_model=List[Dict[str, Any]])
async def get_embedding_models():
    """Get available embedding models from LlamaStack"""
    try:
        models = client.models.list()
        embedding_models = []
        for model in models:
            if model.model_type == "embedding":
                embedding_model = {
                    "id": str(model.identifier),
                    "name": model.provider_resource_id,
                    "model_type": model.type,
                }
                embedding_models.append(embedding_model)
        return embedding_models
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/shields", response_model=List[Dict[str, Any]])
async def get_shields():
    """Get available shields from LlamaStack"""
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

class ChatRequest(BaseModel):
    virtualAssistantId: str
    messages: list[Message]
    stream: bool = False
    sessionId: Optional[str] = None

@router.post("/chat")
async def chat(request: ChatRequest, background_task: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    """Chat endpoint that streams responses from LlamaStack"""
    try:
        log.info(f"Received request: {request.model_dump()}")
        # Get the list of available virtual assistants from the database
        result = await db.execute(select(models.VirtualAssistant))
        assistants = result.scalars().all()
        selectedAssistant = VirtualAssistant()
        
        # If the requested virtual assistant is available, use it
        for va in assistants:
            log.info(f"Requested virtual assistant: {request.virtualAssistantId}")
            log.info(f"Processing virtual assistant: {va.id}")
            if str(va.id) == request.virtualAssistantId:
                log.info(f"Found virtual assistant: {va.id}")
                selectedAssistant = va
                break

        if not selectedAssistant:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Requested virtual assistant {request.virtualAssistantId} not available"
            )

        log.info(f"Processing messages: {request.messages}")
        log.info(f"Using agent: {selectedAssistant.name}")

        session_id = "session_not_set"
        if request.sessionId:
            session_id = request.sessionId

        # Fetch the session state from the database if session_id is set.
        session_state = None
        if session_id != "session_not_set":
            result = await db.execute(select(models.ChatSession).where(models.ChatSession.id == session_id))
            session = result.scalar_one_or_none()
            if session:
                session_state = json.loads(session.session_state)
                if "agent_session_id" in session_state:
                    session_id = session_state["agent_session_id"]
                log.info(f"Got Session state from the database: {session_id}")
            else:
                log.info(f"Session {session_id} not found in the database")

        log.info(f"Creating chat session with Session ID: {session_id}")
        chat = Chat(session_state, selectedAssistant, log)
        
        def generate_response() -> AsyncGenerator[str, None]:
            try:
                # Can check if there is last message and role is user
                if len(request.messages) > 0:
                    last_message = request.messages.pop()
                    for chunk in chat.stream(last_message.content):
                        # Escape text so it can be sent as json
                        text = json.dumps(chunk)
                        yield f"data: {{\"type\":\"text\",\"content\":{text}}}\n\n"

                    # Send session ID as an event
                    log.info(f"Sending Session ID: {chat.session_id}")
                    yield f"data: {{\"type\":\"session\",\"sessionId\":\"{chat.session_id}\"}}\n\n"

                # End of stream
                yield f"data: [DONE]\n\n"

            except Exception as e:
                log.error(f"Error in stream: {str(e)}")
                #yield f"data: Error: {str(e)}\n\n"
                yield f"data: Error  {str(e)}\n\n"

        # save session state to db
        background_task.add_task(save_session_state, chat, db)
        
        return StreamingResponse(
            generate_response(),
            media_type="text/event-stream"
        )

    except Exception as e:
        log.error(f"Error in chat endpoint: {str(e)}")
        #log.error(e.with_traceback())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

async def save_session_state(chat: Chat, db: AsyncSession): 
    #Save session state to the database
    log.info(f"Saving session_state with session id: {chat.session_id}")
    insert_stmt = insert(ChatSession).values(
        id = chat.session_id,
        session_state=json.dumps(chat.session_state)
    )
    update_stmt = insert_stmt.on_conflict_do_update(
        index_elements=[ChatSession.id],
        set_=dict(session_state=json.dumps(chat.session_state))
    )
    await db.execute(update_stmt)
    await db.commit()
