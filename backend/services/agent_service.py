"""
Agent management service for handling agent cloning and user assignments.

This module provides services for cloning virtual assistant agents to ensure
uniqueness per user, managing agent assignments, and interfacing with LlamaStack
for agent operations.

Key Features:
- Clone base agent templates for individual user assignment
- Manage user-specific agent instances
- Interface with LlamaStack agent management APIs
- Track agent ownership and relationships
"""

import uuid
from datetime import datetime
from typing import List, Optional
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from ..api.llamastack import client
from ..utils.logging_config import get_logger

logger = get_logger(__name__)


class AgentService:
    """Service class for managing agent cloning and user assignments."""

    @staticmethod
    async def clone_agent_for_user(base_agent_id: str, user_id: str, user_email: str, admin_user_id: str = None) -> str:
        """
        Clone a base agent configuration for a specific user.

        This method creates a new agent instance from a base template, ensuring
        the user gets their own unique agent instance.

        Args:
            base_agent_id: The ID of the base agent template to clone
            user_id: The UUID of the user the agent is being assigned to
            user_email: The email of the user for naming purposes

        Returns:
            str: The ID of the newly created agent instance

        Raises:
            HTTPException: If agent cloning fails or base agent doesn't exist
        """
        try:
            logger.info(f"Cloning agent {base_agent_id} for user {user_email}")
            
            # Get the base agent configuration
            base_agent = client.agents.retrieve(agent_id=base_agent_id)
            if not base_agent:
                raise HTTPException(
                    status_code=404, 
                    detail=f"Base agent {base_agent_id} not found"
                )

            # Create a unique name for the cloned agent
            base_name = base_agent.agent_config.get("name", "Virtual Assistant")
            user_prefix = user_email.split("@")[0]  # Use email prefix for readability
            unique_suffix = str(uuid.uuid4())[:8]  # Short unique suffix
            cloned_name = f"{base_name} - {user_prefix} - {unique_suffix}"

            # Clone the agent configuration
            cloned_config = base_agent.agent_config.copy()
            cloned_config["name"] = cloned_name
            
            # Add metadata to track the cloning relationship
            if "metadata" not in cloned_config:
                cloned_config["metadata"] = {}
            
            cloned_config["metadata"].update({
                "base_agent_id": base_agent_id,
                "user_id": user_id,
                "user_email": user_email,
                "is_cloned": True,
                "assigned_by": admin_user_id,
                "assigned_at": datetime.now().isoformat()
            })

            # Create the new agent instance in LlamaStack
            create_response = client.agents.create(agent_config=cloned_config)
            cloned_agent_id = create_response.agent_id

            logger.info(f"Successfully cloned agent {base_agent_id} -> {cloned_agent_id} for user {user_email}")
            return cloned_agent_id

        except Exception as e:
            logger.error(f"Failed to clone agent {base_agent_id} for user {user_email}: {str(e)}")
            if isinstance(e, HTTPException):
                raise
            raise HTTPException(
                status_code=500,
                detail=f"Failed to clone agent: {str(e)}"
            )

    @staticmethod
    async def clone_multiple_agents_for_user(
        base_agent_ids: List[str], 
        user_id: str, 
        user_email: str,
        admin_user_id: str = None
    ) -> List[str]:
        """
        Clone multiple base agents for a specific user.

        Args:
            base_agent_ids: List of base agent template IDs to clone
            user_id: The UUID of the user
            user_email: The email of the user

        Returns:
            List[str]: List of newly created agent instance IDs

        Raises:
            HTTPException: If any agent cloning fails
        """
        cloned_agent_ids = []
        failed_clones = []

        for base_agent_id in base_agent_ids:
            try:
                cloned_id = await AgentService.clone_agent_for_user(
                    base_agent_id, user_id, user_email, admin_user_id
                )
                cloned_agent_ids.append(cloned_id)
            except Exception as e:
                logger.error(f"Failed to clone agent {base_agent_id}: {str(e)}")
                failed_clones.append(base_agent_id)
                # Continue with other agents rather than failing completely

        if failed_clones:
            logger.warning(f"Some agent clones failed: {failed_clones}")
            # You might want to handle partial failures differently based on requirements
            
        if not cloned_agent_ids:
            raise HTTPException(
                status_code=500,
                detail="Failed to clone any agents"
            )

        return cloned_agent_ids

    @staticmethod
    async def get_user_agents(user_id: str) -> List[str]:
        """
        Get all agent IDs assigned to a specific user.

        This method would typically query the user's agent_ids from the database,
        but could also validate against LlamaStack to ensure agents still exist.

        Args:
            user_id: The UUID of the user

        Returns:
            List[str]: List of agent IDs assigned to the user
        """
        # This method will be used in conjunction with the database
        # For now, it's a placeholder that could be enhanced to validate
        # agents still exist in LlamaStack
        return []

    @staticmethod
    async def delete_user_agent(agent_id: str, user_id: str) -> bool:
        """
        Delete a user's agent instance.

        Args:
            agent_id: The ID of the agent to delete
            user_id: The UUID of the user who owns the agent

        Returns:
            bool: True if deletion was successful

        Raises:
            HTTPException: If deletion fails or agent doesn't belong to user
        """
        try:
            # Verify the agent belongs to the user by checking metadata
            agent = client.agents.retrieve(agent_id=agent_id)
            if not agent:
                raise HTTPException(status_code=404, detail="Agent not found")

            agent_metadata = agent.agent_config.get("metadata", {})
            if agent_metadata.get("user_id") != user_id:
                raise HTTPException(
                    status_code=403, 
                    detail="Agent does not belong to the specified user"
                )

            # Delete the agent from LlamaStack
            client.agents.delete(agent_id=agent_id)
            logger.info(f"Successfully deleted agent {agent_id} for user {user_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete agent {agent_id} for user {user_id}: {str(e)}")
            if isinstance(e, HTTPException):
                raise
            raise HTTPException(
                status_code=500,
                detail=f"Failed to delete agent: {str(e)}"
            )

    @staticmethod
    async def validate_base_agents_exist(base_agent_ids: List[str]) -> List[str]:
        """
        Validate that base agent templates exist in LlamaStack.

        Args:
            base_agent_ids: List of base agent IDs to validate

        Returns:
            List[str]: List of valid agent IDs

        Raises:
            HTTPException: If any required agents don't exist
        """
        valid_agents = []
        invalid_agents = []

        for agent_id in base_agent_ids:
            try:
                agent = client.agents.retrieve(agent_id=agent_id)
                if agent:
                    valid_agents.append(agent_id)
                else:
                    invalid_agents.append(agent_id)
            except Exception:
                invalid_agents.append(agent_id)

        if invalid_agents:
            raise HTTPException(
                status_code=400,
                detail=f"Base agents not found: {invalid_agents}"
            )

        return valid_agents

    @staticmethod
    def create_agent_assignment(
        agent_id: str, 
        assignment_type: str, 
        assigned_by: str = None,
        base_template_id: str = None
    ) -> dict:
        """
        Create an agent assignment object for user.agent_ids JSON field.

        Args:
            agent_id: The agent ID
            assignment_type: "template" or "clone"
            assigned_by: UUID of admin who assigned (optional)
            base_template_id: For cloned agents, the original template ID (optional)

        Returns:
            dict: Agent assignment object
        """
        assignment = {
            "agent_id": agent_id,
            "type": assignment_type,
            "assigned_at": datetime.now().isoformat()
        }
        
        if assigned_by:
            assignment["assigned_by"] = assigned_by
            
        if base_template_id:
            assignment["base_template_id"] = base_template_id
            
        return assignment

    @staticmethod
    def normalize_agent_ids(agent_ids: list) -> List[dict]:
        """
        Normalize agent_ids to the new format for backward compatibility.
        
        Converts string agent IDs to the new object format.
        
        Args:
            agent_ids: List that may contain strings or dicts
            
        Returns:
            List[dict]: Normalized list of agent assignment objects
        """
        normalized = []
        
        for item in agent_ids or []:
            if isinstance(item, str):
                # Convert legacy string format to new object format
                normalized.append({
                    "agent_id": item,
                    "type": "template",  # Assume legacy entries are templates
                    "assigned_at": datetime.now().isoformat()
                })
            elif isinstance(item, dict):
                # Already in new format, ensure required fields
                if "agent_id" in item:
                    assignment = {
                        "agent_id": item["agent_id"],
                        "type": item.get("type", "template"),
                        "assigned_at": item.get("assigned_at", datetime.now().isoformat())
                    }
                    
                    # Preserve optional fields
                    for field in ["assigned_by", "base_template_id"]:
                        if field in item:
                            assignment[field] = item[field]
                            
                    normalized.append(assignment)
                    
        return normalized

    @staticmethod
    def extract_agent_ids(agent_assignments: list) -> List[str]:
        """
        Extract just the agent IDs from agent assignment objects.
        
        Args:
            agent_assignments: List of agent assignment objects
            
        Returns:
            List[str]: List of agent IDs
        """
        return [
            assignment.get("agent_id") if isinstance(assignment, dict) else assignment
            for assignment in agent_assignments or []
            if assignment
        ]

    @staticmethod
    async def verify_user_agent_access(agent_id: str, user_id: str, user_role: str) -> bool:
        """
        Verify that a user has access to a specific agent.

        Args:
            agent_id: The ID of the agent to check access for
            user_id: The UUID of the user
            user_role: The role of the user (admin, ops, user)

        Returns:
            bool: True if user has access to the agent

        Raises:
            HTTPException: If agent doesn't exist or access is denied
        """
        from ..models import RoleEnum  # Import here to avoid circular imports
        
        # Admin users have access to all agents
        if user_role == RoleEnum.admin.value:
            return True

        try:
            # Get the agent from LlamaStack
            agent = client.agents.retrieve(agent_id=agent_id)
            if not agent:
                raise HTTPException(status_code=404, detail="Agent not found")

            # Check if the agent belongs to the user (for cloned agents)
            agent_metadata = agent.agent_config.get("metadata", {})
            if agent_metadata.get("user_id") == user_id:
                return True

            # For ops and regular users, they must be explicitly assigned the agent
            # This will be checked against the user's agent_ids in the database
            return False

        except Exception as e:
            logger.error(f"Error verifying agent access for user {user_id}, agent {agent_id}: {str(e)}")
            if isinstance(e, HTTPException):
                raise
            raise HTTPException(
                status_code=500,
                detail="Failed to verify agent access"
            )

    @staticmethod
    async def verify_user_agent_access_complete(
        agent_id: str, 
        user_id: str, 
        user_role: str, 
        db: AsyncSession
    ) -> bool:
        """
        Complete agent access verification using both database and LlamaStack.

        This method checks both the user's assigned agent_ids in the database
        and the agent metadata in LlamaStack for comprehensive access control.

        Args:
            agent_id: The ID of the agent to check access for
            user_id: The UUID of the user
            user_role: The role of the user (admin, ops, user)
            db: Database session for user lookup

        Returns:
            bool: True if user has access to the agent

        Raises:
            HTTPException: If agent doesn't exist or access is denied
        """
        from ..models import User, RoleEnum  # Import here to avoid circular imports
        
        # Admin users have access to all agents
        if user_role == RoleEnum.admin.value:
            return True

        try:
            # Get user from database to check assigned agents
            result = await db.execute(select(User).where(User.id == user_id))
            db_user = result.scalar_one_or_none()
            if not db_user:
                raise HTTPException(status_code=404, detail="User not found")

            # Check if agent is in user's assigned agent list
            user_agent_ids = db_user.agent_ids or []
            if agent_id in user_agent_ids:
                # Also verify the agent still exists in LlamaStack
                agent = client.agents.retrieve(agent_id=agent_id)
                if agent:
                    return True
                else:
                    # Agent exists in database but not in LlamaStack - should be cleaned up
                    logger.warning(f"Agent {agent_id} assigned to user {user_id} but not found in LlamaStack")
                    return False

            # If not in assigned list, check LlamaStack metadata (for cloned agents)
            return await AgentService.verify_user_agent_access(agent_id, user_id, user_role)

        except Exception as e:
            logger.error(f"Error in complete agent access verification for user {user_id}, agent {agent_id}: {str(e)}")
            if isinstance(e, HTTPException):
                raise
            raise HTTPException(
                status_code=500,
                detail="Failed to verify agent access"
            ) 