import enum
from sqlalchemy import (
    Column, String, Enum, TIMESTAMP, Boolean, ForeignKey, JSON, Text, func
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base, relationship
import uuid

Base = declarative_base()

class RoleEnum(enum.Enum):
    admin = "admin"
    devops = "devops"
    user = "user"

class User(Base):
    __tablename__ = "users"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(255), unique=True, nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(Enum(RoleEnum, name="role"), nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
    
    mcp_servers = relationship("MCPServer", back_populates="creator")
    knowledge_bases = relationship("KnowledgeBase", back_populates="creator")
    virtual_assistants = relationship("VirtualAssistant", back_populates="creator")
    guardrails = relationship("Guardrail", back_populates="creator")

class MCPServer(Base):
    __tablename__ = "mcp_servers"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(String(255))
    endpoint_url = Column(String(255), nullable=False)
    configuration = Column(JSON)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
    creator = relationship("User", back_populates="mcp_servers")

class KnowledgeBase(Base):
    __tablename__ = "knowledge_bases"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    version = Column(String(50), nullable=False)
    embedding_model = Column(String(255), nullable=False)
    provider_id = Column(String(255))
    vector_db_name = Column(String(255), nullable=False)
    is_external = Column(Boolean, nullable=False, default=False)
    source = Column(String(255))
    source_configuration = Column(JSON)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
    creator = relationship("User", back_populates="knowledge_bases")

class VirtualAssistant(Base):
    __tablename__ = "virtual_assistants"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    prompt = Column(Text, nullable=False)
    model_name = Column(String(255), nullable=False)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
    creator = relationship("User", back_populates="virtual_assistants")

class VirtualAssistantKnowledgeBase(Base):
    __tablename__ = "virtual_assistant_knowledge_bases"
    virtual_assistant_id = Column(UUID(as_uuid=True), ForeignKey("virtual_assistants.id", ondelete="CASCADE"), primary_key=True)
    knowledge_base_id = Column(String(255), nullable=False)

class VirtualAssistantTool(Base):
    __tablename__ = "virtual_assistant_tools"
    virtual_assistant_id = Column(UUID(as_uuid=True), ForeignKey("virtual_assistants.id", ondelete="CASCADE"), primary_key=True)
    tool_id = Column(String(255), nullable=False)

class ChatHistory(Base):
    __tablename__ = "chat_history"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    virtual_assistant_id = Column(UUID(as_uuid=True), ForeignKey("virtual_assistants.id"))
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    message = Column(Text, nullable=False)
    response = Column(Text, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

class Guardrail(Base):
    __tablename__ = "guardrails"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    rules = Column(JSON, nullable=False)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
    creator = relationship("User", back_populates="guardrails")

class ModelServer(Base):
    __tablename__ = "model_servers"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    provider_name = Column(String(255), nullable=False)
    model_name = Column(String(255), nullable=False)
    endpoint_url = Column(String(255), nullable=False)
    token = Column(String(255), nullable=True)

class ChatSession(Base):
    __tablename__ = "chat_sessions"
    id = Column(String(255), primary_key=True)
    # session_id = Column(UUID, unique=True)
    # user_id = Column(UUID, ForeignKey("users.id"))
    # assistant_id = Column(UUID, ForeignKey("assistants.id"))
    # messages = Column(JSONB, default=list)
    session_state = Column(JSON, default=dict)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
