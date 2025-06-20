# Authentication & Authorization Architecture

## Table of Contents
- [Overview](#overview)
- [Current Architecture](#current-architecture)
- [Role-Based Access Control (RBAC)](#role-based-access-control-rbac)
- [Development Mode Bypass](#development-mode-bypass)
- [API Endpoint Security](#api-endpoint-security)
- [Agent Access Control](#agent-access-control)
- [Future Integration: Llama Stack OAuth & ABAC](#future-integration-llama-stack-oauth--abac)
- [Security Considerations](#security-considerations)
- [Troubleshooting](#troubleshooting)

## Overview

The AI Virtual Assistant platform implements a comprehensive **Role-Based Access Control (RBAC)** system that provides enterprise-grade security through:

- **Authentication**: OAuth proxy integration with header-based user identification
- **Authorization**: Three-tier role system (Admin, Ops, User) with granular permissions
- **Agent Access Control**: User-specific agent assignments with template/clone management
- **Development Support**: Configurable dev mode bypass for local development
- **Future Ready**: Designed for seamless integration with Llama Stack's OAuth and ABAC systems

### Authentication Flow

```
Client Request → Dev Mode Check → OAuth Headers → Database Lookup → Role Authorization → Access Decision
```

## Current Architecture

### Authentication Layer

The authentication system operates in two modes:

#### Production Mode (OAuth Proxy)
- **Integration**: OpenShift OAuth proxy
- **Headers**: `X-Forwarded-User`, `X-Auth-Request-User`, `X-Forwarded-Email`, `X-Auth-Request-Email`
- **User Lookup**: Email-based user identification in PostgreSQL database
- **Security**: Relies on OAuth proxy for authentication, application handles authorization

#### Development Mode (Bypass)
- **Activation**: `DEV_MODE=true` environment variable
- **Configuration**: Environment-based user setup
- **Security**: Disabled in production environments
- **Purpose**: Local development and testing

### Authorization Layer

Three-tier role system with hierarchical permissions:

```
Admin Role → Full System Access
        ├── User Management
        ├── Agent Management
        └── Infrastructure Management

Ops Role → Infrastructure Management
        ├── Infrastructure Management
        ├── Assigned Agent Chat
        └── Own Chat History

User Role → Limited Access
        ├── Assigned Agent Chat
        └── Own Chat History
```

## Role-Based Access Control (RBAC)

### Role Definitions

| Role | Description | Primary Use Case |
|------|-------------|------------------|
| **Admin** | Full system access and control | System administrators |
| **Ops** | Infrastructure and operations management | DevOps engineers, system operators |
| **User** | End-user access to assigned agents | Business users, employees |

### Permission Matrix

| Feature | Admin | Ops | User |
|---------|-------|-----|------|
| **User Management** |  |  |  |
| Create/Delete Users | ✅ | ❌ | ❌ |
| Assign Agents to Users | ✅ | ❌ | ❌ |
| View All Users | ✅ | ❌ | ❌ |
| Update User Roles | ✅ | ❌ | ❌ |
| **Agent Management** |  |  |  |
| Create/Delete Agents | ✅ | ❌ | ❌ |
| View Agent Templates | ✅ | ❌ | ❌ |
| Chat with Assigned Agents | ✅ | ✅ | ✅ |
| **Infrastructure** |  |  |  |
| Knowledge Bases (CRUD) | ✅ | ✅ | ❌ |
| MCP Servers (CRUD) | ✅ | ✅ | ❌ |
| Model Servers (CRUD) | ✅ | ✅ | ❌ |
| Tools (Read) | ✅ | ✅ | ❌ |
| Sync Operations | ✅ | ❌ | ❌ |
| **System Configuration** |  |  |  |
| Guardrails | ✅ | ❌ | ❌ |
| LlamaStack Integration | ✅ | ❌ | ❌ |
| **Chat & Sessions** |  |  |  |
| Own Chat History | ✅ | ✅ | ✅ |
| All Chat History | ✅ | ❌ | ❌ |
| Own Profile | ✅ | ✅ | ✅ |

## Development Mode Bypass

### Setup

Create a `.env` file in the backend directory:

```bash
# Enable development mode
DEV_MODE=true

# Configure development user (optional - defaults shown)
DEV_USER_EMAIL=admin@example.com
DEV_USER_ROLE=admin
DEV_USER_USERNAME=dev-admin
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DEV_MODE` | `false` | Enable/disable development mode |
| `DEV_USER_EMAIL` | `dev@example.com` | Email for development user |
| `DEV_USER_ROLE` | `admin` | Role for development user (`admin`, `ops`, `user`) |
| `DEV_USER_USERNAME` | `dev-user` | Username for development user |

### Testing Different Roles

```bash
# Test as Admin (full access)
export DEV_USER_ROLE=admin

# Test as Ops (infrastructure access)  
export DEV_USER_ROLE=ops

# Test as User (limited access)
export DEV_USER_ROLE=user

# Restart the application to apply changes
```

### Security Features

- ✅ Only activated by explicit environment variable
- ✅ Logged with clear [DEV] vs [PROD] indicators
- ✅ Recommended for local development only
- ✅ No OAuth headers required in dev mode
- ⚠️ Never use in production environments

## API Endpoint Security

### Protected Endpoints

All API endpoints are secured with role-based access control:

#### Admin-Only Endpoints
```python
# User management
POST   /api/users/                    # Create users
PUT    /api/users/{id}/role          # Update user roles
GET    /api/users/{id}               # View user details

# Agent management  
POST   /api/virtual_assistants/      # Create agents
POST   /api/users/{id}/agents        # Assign agents
GET    /api/virtual_assistants/templates # List templates

# System configuration
POST   /api/guardrails/              # Manage guardrails
POST   /api/*/sync                   # Sync operations
```

#### Admin/Ops Endpoints
```python
# Infrastructure management
POST   /api/knowledge_bases/         # Knowledge base CRUD
POST   /api/mcp_servers/             # MCP server CRUD  
POST   /api/model_servers/           # Model server CRUD
GET    /api/tools/                   # Tool access
```

#### All Authenticated Users
```python
# Self-service
GET    /api/users/profile            # Own profile
GET    /api/users/agents             # Own agents
POST   /api/chat/sessions            # Chat sessions
GET    /api/chat/history             # Own chat history
```

### Implementation Pattern

```python
from backend.services.auth import RoleChecker
from backend.models import RoleEnum

# Admin only
@router.post("/", dependencies=[Depends(RoleChecker([RoleEnum.admin]))])

# Admin or Ops
@router.get("/", dependencies=[Depends(RoleChecker([RoleEnum.admin, RoleEnum.ops]))])

# All authenticated users (uses get_current_user)
@router.get("/profile")
async def get_profile(current_user = Depends(get_current_user)):
```

## Agent Access Control

### Agent Assignment System

The platform implements a sophisticated agent access control system:

#### Template vs Clone System
- **Templates**: Admin-created base agent configurations
- **Clones**: User-specific instances created from templates
- **Isolation**: Each user gets their own agent instance
- **Tracking**: Full audit trail of assignments and usage

#### Assignment Process
```
Admin Selects Templates → System Validates → Clones Agents for User → Updates User Agent IDs → User Can Access Cloned Agents
```

#### Access Verification
```python
# Verify user has access to specific agent
from backend.services.auth import verify_agent_access

@router.post("/agents/{agent_id}/chat")
async def start_chat(
    agent_id: str,
    user = Depends(verify_agent_access)
):
    # User has verified access to this agent
    return {"status": "chat_started"}
```

### Agent ID Structure

The `user.agent_ids` JSON field supports both legacy and enhanced formats:

```json
// Legacy format (backward compatible)
["agent_123", "agent_456"]

// Enhanced format (current)
[
  {
    "agent_id": "template_123",
    "type": "template", 
    "assigned_by": "admin_user_id",
    "assigned_at": "2025-01-28T10:00:00Z"
  },
  {
    "agent_id": "clone_456",
    "type": "clone",
    "base_template_id": "template_123",
    "assigned_by": "admin_user_id", 
    "assigned_at": "2025-01-28T10:00:00Z"
  }
]
```

## Future Integration: Llama Stack OAuth & ABAC

### Planned Evolution

The current RBAC system is designed to seamlessly integrate with Llama Stack's upcoming authentication and authorization features:

#### Phase 1: OAuth Client Integration (Future)
- **Replace**: OAuth proxy with Llama Stack OAuth client
- **Enhance**: Token-based authentication
- **Maintain**: Current role-based permissions
- **Migration**: Smooth transition from header-based to token-based auth

```python
# Future OAuth integration (planned)
from llamastack.auth import OAuthClient

@router.get("/profile")
async def get_profile(token = Depends(oauth_client.verify_token)):
    user = await get_user_from_token(token)
    return user
```

#### Phase 2: Attribute-Based Access Control (ABAC) (Future)
- **Extend**: Current role-based system with attribute-based controls
- **Attributes**: User department, project membership, security clearance
- **Policies**: Fine-grained permissions based on multiple attributes
- **Integration**: Leverage Llama Stack's ABAC policy engine

```python
# Future ABAC integration (planned)
from llamastack.auth import ABACPolicyEngine

@router.get("/sensitive-agents")
async def get_sensitive_agents(
    user = Depends(get_current_user),
    policy_engine = Depends(ABACPolicyEngine)
):
    # Check multiple attributes
    if policy_engine.evaluate({
        "user.role": user.role,
        "user.department": user.department,
        "user.clearance_level": user.clearance_level,
        "resource.sensitivity": "high"
    }):
        return get_sensitive_agents()
    raise HTTPException(403, "Insufficient privileges")
```

#### Phase 3: Unified Policy Management (Future)
- **Centralize**: All auth policies in Llama Stack
- **Standardize**: Cross-service authorization
- **Scale**: Multi-tenant authorization
- **Audit**: Comprehensive access logging

### Migration Strategy

#### Backward Compatibility
- Current RBAC system will remain functional
- Gradual migration path with zero downtime
- Dual authentication support during transition
- Role mappings preserved

#### Implementation Phases
1. **OAuth Integration**: Replace OAuth proxy with Llama Stack OAuth
2. **Policy Enhancement**: Add ABAC attributes to existing roles
3. **Policy Migration**: Move policies to Llama Stack policy engine
4. **Full Integration**: Complete Llama Stack auth integration

### Benefits of Future Integration

| Current RBAC | Future Llama Stack Integration |
|--------------|-------------------------------|
| Role-based permissions | ✅ Role + Attribute-based permissions |
| Manual user management | ✅ Automated user provisioning |
| Application-specific auth | ✅ Cross-service authentication |
| Static role assignments | ✅ Dynamic policy evaluation |
| Limited audit trail | ✅ Comprehensive audit logging |

## Security Considerations

### Production Security

#### Authentication Security
- ✅ OAuth proxy handles authentication
- ✅ Application never sees user credentials
- ✅ Headers validated and sanitized
- ✅ User lookup via database queries

#### Authorization Security
- ✅ Role-based access control on all endpoints
- ✅ Agent access verification before operations
- ✅ Database-level user isolation
- ✅ Comprehensive audit logging

#### Data Protection
- ✅ User chat sessions isolated by agent access
- ✅ Admin-only access to sensitive operations
- ✅ No exposure of system configuration to end users
- ✅ Encrypted database connections

### Development Security

#### Dev Mode Safeguards
- ✅ Explicit environment variable activation
- ✅ Clear logging of dev vs production mode
- ✅ No dev mode in production deployments
- ✅ Role testing capabilities

#### Best Practices
```bash
# Recommended .env setup
DEV_MODE=true
DEV_USER_EMAIL=yourname@company.com
DEV_USER_ROLE=admin

# Security checks
export NODE_ENV=development
unset DEV_MODE  # For production testing
```

### Security Monitoring

#### Logging Features
- Authentication attempts (success/failure)
- Role-based access decisions  
- Agent access verifications
- Admin operations (user creation, role changes)
- Development mode usage

#### Log Examples
```
[PROD] Role check: user=admin@company.com, role=admin, allowed=[admin]
[PROD] Access granted: user=admin@company.com, role=admin
[DEV] Role check: user=dev@example.com, role=admin, allowed=[admin,ops]
[PROD] Access denied: user=user@company.com, role=user, required=[admin]
```

## Troubleshooting

### Common Issues

#### Authentication Problems

**Issue**: 401 Unauthorized errors in production
```bash
# Check OAuth proxy headers
curl -H "X-Forwarded-User: user@company.com" http://localhost:8000/api/users/profile

# Verify user exists in database
psql -c "SELECT * FROM users WHERE email = 'user@company.com';"
```

**Issue**: Dev mode not working
```bash
# Verify environment variables
echo $DEV_MODE
echo $DEV_USER_EMAIL

# Check logs for dev mode activation
grep "DEV" backend.log
```

#### Authorization Problems

**Issue**: 403 Forbidden errors
```bash
# Check user role
psql -c "SELECT email, role FROM users WHERE email = 'user@company.com';"

# Verify endpoint permissions
grep "RoleChecker" backend/routes/your_endpoint.py
```

**Issue**: Agent access denied
```bash
# Check user agent assignments  
psql -c "SELECT email, agent_ids FROM users WHERE email = 'user@company.com';"

# Verify agent exists
curl http://localhost:8000/api/virtual_assistants/
```

#### Database Issues

**Issue**: User not found errors
```bash
# Check database connection
psql $DATABASE_URL -c "SELECT 1;"

# Verify user table
psql -c "SELECT COUNT(*) FROM users;"

# Create test user
psql -c "INSERT INTO users (email, role, username) VALUES ('test@company.com', 'user', 'test');"
```

### Debug Mode

Enable detailed logging:

```python
import logging
logging.getLogger("backend.services.auth").setLevel(logging.DEBUG)
```

### Health Checks

```bash
# Test authentication
curl http://localhost:8000/api/v1/login

# Test role-based access
curl http://localhost:8000/api/users/profile

# Test dev mode
DEV_MODE=true python -c "from backend.services.auth import is_dev_mode; print(is_dev_mode())"
```

---

## Quick Reference

### Environment Variables
```bash
# Production
DATABASE_URL=postgresql://...
OAUTH_PROXY_HEADERS=true

# Development  
DEV_MODE=true
DEV_USER_EMAIL=admin@example.com
DEV_USER_ROLE=admin
```

### Role Hierarchy
```
Admin > Ops > User
  ↓     ↓     ↓
Full  Infra Limited
```

### Common Commands
```bash
# Switch roles (dev mode)
export DEV_USER_ROLE=admin && restart
export DEV_USER_ROLE=ops && restart  
export DEV_USER_ROLE=user && restart

# Check access
curl /api/knowledge_bases/  # Admin/Ops only
curl /api/users/profile     # All authenticated
```
