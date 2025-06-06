from http.client import HTTPException
from llama_stack_client import Agent
from llama_stack_client.lib.agents.react.agent import ReActAgent
from typing import Optional, List, Union, Any, Tuple, Callable
from llama_stack_client.lib.agents.agent import AgentConfig
from llama_stack_client.lib.agents.tool_parser import ToolParser
from llama_stack_client.lib.agents.client_tool import ClientTool
from llama_stack_client.types.agents.turn_create_params import Toolgroup
from llama_stack_client.types.shared_params.agent_config import ToolConfig
from llama_stack_client.types import SamplingParams


class ExistingAgent(Agent):
    """An extension of the Agent class that can be initialized with an existing agent_id."""
    
    def __init__(
        self,
        client,
        agent_id: str,
        agent_config: Optional[AgentConfig] = None,
        model: Optional[str] = None,
        instructions: Optional[str] = None,
        tools: Optional[List[Union[Toolgroup, ClientTool, Callable[..., Any]]]] = None,
        tool_config: Optional[ToolConfig] = None,
        sampling_params: Optional[SamplingParams] = None,
        max_infer_iters: Optional[int] = None,
        client_tools: Tuple[ClientTool, ...] = (),
        tool_parser: Optional[ToolParser] = None,
    ):
  
        self.client = client
        self.agent_id = agent_id
        self.agent_config = agent_config
        self.model = agent_config.get("model", None)
        self.instructions = agent_config.get("instructions", None)
        self.tools = agent_config.get("toolgroups", [])
        self.tool_config = agent_config.get("tool_config", None)
        self.sampling_params = agent_config.get("sampling_params", None)
        self.max_infer_iters = agent_config.get("max_infer_iters", None)
        self.client_tools = agent_config.get("client_tools", [])
        self.tool_parser = tool_parser
        self.sessions = []
        self.builtin_tools = {}


class ExistingReActAgent(ReActAgent):
    """An extension of the ReActAgent class that can be initialized with an existing agent_id."""
    
    def __init__(
        self,
        client,
        agent_id: str,
        agent_config: Optional[AgentConfig] = None,
        model: Optional[str] = None,
        tools: Optional[List[Union[Toolgroup, ClientTool, Callable[..., Any]]]] = None,
        tool_config: Optional[ToolConfig] = None,
        sampling_params: Optional[SamplingParams] = None,
        max_infer_iters: Optional[int] = None,
        client_tools: Tuple[ClientTool, ...] = (),
        response_format: Optional[dict] = None,
        tool_parser: Optional[ToolParser] = None,
    ):

        self.client = client
        self.agent_id = agent_id
        self.agent_config = agent_config
        self.model = agent_config.get("model", None)
        self.tools = agent_config.get("toolgroups", [])
        self.tool_config = agent_config.get("tool_config", None)
        self.sampling_params = agent_config.get("sampling_params", None)
        self.max_infer_iters = agent_config.get("max_infer_iters", None)
        self.client_tools = agent_config.get("client_tools", [])
        self.response_format = response_format
        self.tool_parser = tool_parser
        self.sessions = []
        self.builtin_tools = {}
