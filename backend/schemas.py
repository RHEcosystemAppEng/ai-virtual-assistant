"""
Pydantic schemas for API request/response validation and serialization.

This module defines all Pydantic models used for data validation, serialization,
and API documentation generation throughout the AI Virtual Assistant application.
Each schema group corresponds to a specific domain:

- User schemas: Authentication and user management
- MCPServer schemas: Model Context Protocol server configurations
- KnowledgeBase schemas: Vector database and knowledge base management
- VirtualAssistant schemas: AI agent configuration and management
- Guardrail schemas: Safety and content filtering rules
- ModelServer schemas: External model service configurations

The schemas follow a standard pattern:
- Base: Common fields for creation and updates
- Create: Fields required for resource creation
- Read: Fields returned in API responses (includes metadata)
- Update: Optional fields for resource updates
"""

import enum
from typing import Any, Dict, List, Optional, Union  # Added Dict for Guardrail rules

from pydantic import UUID4, BaseModel, EmailStr


# This should match the Enum in your models.py
class ToolTypeEnumSchema(str, enum.Enum):
    BUILTIN = "builtin"
    MCP_SERVER = "mcp_server"


class RoleEnum(str, enum.Enum):
    admin = "admin"
    ops = "ops"
    user = "user"


class AgentAssignment(BaseModel):
    """Schema for individual agent assignments in user.agent_ids JSON field."""
    agent_id: str
    type: str  # "template" or "clone"
    assigned_by: Optional[str] = None  # UUID of admin who assigned
    assigned_at: Optional[str] = None  # ISO timestamp
    base_template_id: Optional[str] = None  # For cloned agents


class UserBase(BaseModel):
    username: Optional[str] = None
    email: EmailStr
    role: RoleEnum
    agent_ids: Optional[List[Union[str, AgentAssignment]]] = []  # Backward compatible


class UserCreate(UserBase):
    password: Optional[str] = None


class UserRead(UserBase):
    id: UUID4
    created_at: Any
    updated_at: Any

    class Config:
        orm_mode = True


class UserUpdate(BaseModel):
    role: Optional[RoleEnum] = None


class AgentAssignmentRequest(BaseModel):
    agent_template_ids: List[str]  # Base agent configurations to clone and assign


class UserProfileResponse(UserRead):
    """Response schema for user profile endpoint"""
    pass


class AgentTemplateResponse(BaseModel):
    """Response schema for agent template listing."""
    agent_id: str
    name: str
    description: Optional[str] = None
    created_by: str  # Admin user ID who created it
    created_by_email: str  # Admin email for display
    created_at: str  # ISO timestamp


# MCPServer Schemas
class MCPServerBase(BaseModel):
    toolgroup_id: str  # LlamaStack identifier (now PK)
    name: str
    description: Optional[str] = None
    endpoint_url: str
    configuration: Optional[Dict[str, Any]] = None


class MCPServerCreate(MCPServerBase):
    pass


class MCPServerRead(MCPServerBase):
    created_by: Optional[UUID4] = None
    created_at: Any
    updated_at: Any

    class Config:
        orm_mode = True


# KnowledgeBase Schemas
class KnowledgeBaseBase(BaseModel):
    vector_db_name: str  # LlamaStack identifier (now PK)
    name: str
    version: str
    embedding_model: str
    provider_id: Optional[str] = None
    is_external: bool = False
    source: Optional[str] = None
    source_configuration: Optional[Union[List[str], Dict[str, Any]]] = (
        None  # More specific type
    )


class KnowledgeBaseCreate(KnowledgeBaseBase):

    def pipeline_model_dict(self) -> Dict[str, Any]:
        base = {
            "name": self.name,
            "version": self.version,
            "source": self.source,
            "embedding_model": self.embedding_model,
            "vector_db_name": self.vector_db_name
        }
        if self.source == "URL":
            return base | {"urls": self.source_configuration}

        return base | {k.lower(): v for k, v in self.source_configuration.items()}


class KnowledgeBaseRead(KnowledgeBaseBase):
    created_by: Optional[UUID4] = None
    created_at: Any
    updated_at: Any

    class Config:
        orm_mode = True


# Tool Association Info for VirtualAssistant
class ToolAssociationInfo(BaseModel):
    toolgroup_id: (
        str  # This refers to MCPServer.toolgroup_id or BuiltInTool.toolgroup_id
    )


# VirtualAssistant Schemas
class VirtualAssistantBase(BaseModel):
    name: str
    prompt: Optional[str] = None
    model_name: Optional[str] = None
    input_shields: Optional[List[str]] = []
    output_shields: Optional[List[str]] = []
    temperature: Optional[float] = 0.1
    repetition_penalty: Optional[float] = 1.0
    max_tokens: Optional[int] = 4096
    top_p: Optional[float] = 0.95
    knowledge_base_ids: Optional[List[str]] = (
        []
    )  # Now expecting list of vector_db_names
    tools: Optional[List[ToolAssociationInfo]] = []  # Changed from tool_ids: List[str]
    max_infer_iters: Optional[int] = 10
    enable_session_persistence: Optional[bool] = False


class VirtualAssistantCreate(VirtualAssistantBase):
    pass


class VirtualAssistantUpdate(VirtualAssistantBase):
    name: Optional[str] = None
    prompt: Optional[str] = None
    model_name: Optional[str] = None
    knowledge_base_ids: Optional[List[str]] = (
        None  # Now expecting list of vector_db_names
    )
    tools: Optional[List[ToolAssociationInfo]] = None


class VirtualAssistantRead(VirtualAssistantBase):
    id: str

    class Config:
        orm_mode = True


class GuardrailBase(BaseModel):
    name: str
    rules: Dict[str, Any]


class GuardrailCreate(GuardrailBase):
    pass


class GuardrailRead(GuardrailBase):
    id: UUID4
    created_by: Optional[UUID4] = None
    created_at: Any
    updated_at: Any

    class Config:
        orm_mode = True


# ModelServer Schemas (These seemed largely okay with your models.py)
class ModelServerBase(BaseModel):
    name: str
    provider_name: str
    model_name: str
    endpoint_url: str
    token: Optional[str] = None


class ModelServerCreate(ModelServerBase):
    pass


class ModelServerUpdate(ModelServerBase):
    name: Optional[str] = None
    provider_name: Optional[str] = None
    model_name: Optional[str] = None
    endpoint_url: Optional[str] = None
    token: Optional[str] = None


class ModelServerRead(ModelServerBase):
    id: UUID4

    class Config:
        orm_mode = True
