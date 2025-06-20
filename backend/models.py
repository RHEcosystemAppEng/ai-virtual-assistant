"""
SQLAlchemy database models for the AI Virtual Assistant application.

This module defines the database schema and relationships for:
- Users and role-based access control
- MCP servers and tool configurations
- Knowledge bases for RAG functionality
- Virtual assistants and chat sessions
- Guardrails for AI safety
- Model servers for LLM providers
"""

import enum
import uuid

from sqlalchemy import JSON, TIMESTAMP, Boolean, Column, Enum, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class RoleEnum(enum.Enum):
    admin = "admin"
    ops = "ops"
    user = "user"


class User(Base):
    __tablename__ = "users"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(255), unique=True, nullable=True)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=True)
    role = Column(Enum(RoleEnum, name="role"), nullable=False)
    agent_ids = Column(JSON, nullable=False, default=list)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(
        TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    mcp_servers = relationship("MCPServer", back_populates="creator")
    knowledge_bases = relationship("KnowledgeBase", back_populates="creator")
    guardrails = relationship("Guardrail", back_populates="creator")


class MCPServer(Base):
    __tablename__ = "mcp_servers"
    toolgroup_id = Column(String(255), primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(String(255))
    endpoint_url = Column(String(255), nullable=False)
    configuration = Column(JSON)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(
        TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    creator = relationship("User", back_populates="mcp_servers")


class KnowledgeBase(Base):
    __tablename__ = "knowledge_bases"
    vector_db_name = Column(String(255), primary_key=True)
    name = Column(String(255), nullable=False)
    version = Column(String(50), nullable=False)
    embedding_model = Column(String(255), nullable=False)
    provider_id = Column(String(255))
    is_external = Column(Boolean, nullable=False, default=False)
    status = Column(String(50), nullable=True)
    source = Column(String(255))
    source_configuration = Column(JSON)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(
        TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    creator = relationship("User", back_populates="knowledge_bases")


class ChatSession(Base):
    __tablename__ = "chat_sessions"
    id = Column(String(255), primary_key=True)
    session_state = Column(JSON, default=dict)

    # New fields for sidebar display
    title = Column(String(500), nullable=True)  # Generated summary/title
    agent_name = Column(String(255), nullable=True)  # Agent display name

    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(
        TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Guardrail(Base):
    __tablename__ = "guardrails"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    rules = Column(JSON, nullable=False)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(
        TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    creator = relationship("User", back_populates="guardrails")


class ModelServer(Base):
    __tablename__ = "model_servers"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    provider_name = Column(String(255), nullable=False)
    model_name = Column(String(255), nullable=False)
    endpoint_url = Column(String(255), nullable=False)
    token = Column(String(255), nullable=True)
