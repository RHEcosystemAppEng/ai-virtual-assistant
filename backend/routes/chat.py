import enum
import json
import uuid

from llama_stack_client import Agent
from llama_stack_client.lib.agents.react.agent import ReActAgent
from llama_stack_client.lib.agents.react.tool_parser import ReActOutput
import os
from ..api.llamastack import client

class AgentType(enum.Enum):
    REGULAR = "Regular"
    REACT = "ReAct"


class Chat:

    """
    A class representing a chatbot.

    Args:
        config (dict): Configuration settings for the chatbot.
        logger: Logger object for logging messages.

    Attributes:
        logger: Logger object for logging messages.
        config (dict): Configuration settings for the chatbot.
        model_kwargs (dict): Keyword arguments for the model.
        embeddings: HuggingFaceEmbeddings object for handling embeddings.
        prompt_template: Template for the chatbot's prompt.

    Methods:
        _format_sources: Formats the list of sources.
        stream: Streams the chatbot's response based on the query and other parameters.
    """

    def __init__(self, user_id, virtual_assistant_id):
        os.environ["TOKENIZERS_PARALLELISM"] = "false"
        self.user_id = user_id
        self.virtual_assistant_id = virtual_assistant_id
        self.session_state = {}
        self.session_state["agent_type"] = AgentType.REGULAR
        self.session_state["messages"] = []
        self.components = None
        
    async def _fetch_components(self, db):
        """Fetch the model server, knowledge base, and tools for this virtual assistant."""
        from sqlalchemy import select
        from ..models import VirtualAssistant, ModelServer, VirtualAssistantKnowledgeBase, KnowledgeBase, VirtualAssistantTool, MCPServer
        
        try:
            # Get the virtual assistant
            result = await db.execute(select(VirtualAssistant).where(VirtualAssistant.id == self.virtual_assistant_id))
            db_va = result.scalar_one_or_none()
            if not db_va:
                raise ValueError(f"Virtual assistant with ID {self.virtual_assistant_id} not found")

            # Get the model server
            model_result = await db.execute(
                select(ModelServer).where(ModelServer.model_name == db_va.model_name)
            )
            model_server = model_result.scalar_one_or_none()
            if not model_server:
                raise ValueError(f"Model server for model {db_va.model_name} not found")

            # Get knowledge bases
            kb_result = await db.execute(
                select(VirtualAssistantKnowledgeBase)
                .where(VirtualAssistantKnowledgeBase.virtual_assistant_id == self.virtual_assistant_id)
            )
            kb_relations = kb_result.scalars().all()
            kb_ids = [r.knowledge_base_id for r in kb_relations]
            
            kb_details = []
            for kb_id in kb_ids:
                kb_detail = await db.execute(
                    select(KnowledgeBase).where(KnowledgeBase.id == kb_id)
                )
                kb = kb_detail.scalar_one_or_none()
                if kb:
                    kb_details.append({
                        "id": str(kb.id),
                        "name": kb.name,
                        "version": kb.version,
                        "embedding_model": kb.embedding_model,
                        "vector_db_name": kb.vector_db_name,
                        "is_external": kb.is_external,
                        "source": kb.source,
                        "source_configuration": kb.source_configuration
                    })

            # Get MCP servers (tools)
            mcp_result = await db.execute(
                select(VirtualAssistantTool)
                .where(VirtualAssistantTool.virtual_assistant_id == self.virtual_assistant_id)
            )
            mcp_relations = mcp_result.scalars().all()
            mcp_ids = [r.mcp_server_id for r in mcp_relations]
            
            mcp_details = []
            for mcp_id in mcp_ids:
                mcp_detail = await db.execute(
                    select(MCPServer).where(MCPServer.id == mcp_id)
                )
                mcp = mcp_detail.scalar_one_or_none()
                if mcp:
                    mcp_details.append({
                        "id": str(mcp.id),
                        "name": mcp.name,
                        "title": mcp.title,
                        "description": mcp.description,
                        "endpoint_url": mcp.endpoint_url,
                        "configuration": mcp.configuration
                    })

            self.components = {
                "model_server": {
                    "id": str(model_server.id) if model_server else None,
                    "name": model_server.name if model_server else None,
                    "provider_name": model_server.provider_name if model_server else None,
                    "model_name": model_server.model_name if model_server else None,
                    "endpoint_url": model_server.endpoint_url if model_server else None
                },
                "knowledge_bases": kb_details,
                "tools": mcp_details
            }
        except Exception as e:
            raise ValueError(f"Failed to fetch components: {str(e)}")
        
    def _reset_agent(self):
        self.session_state.clear()
        # st.cache_resource.clear()
        pass

    def _get_client(self):
        return client

    def _get_tools(self):
        if not self.components:
            return []
            
        tool_groups = self._get_client().toolgroups.list()
        tool_groups_list = [tool_group.identifier for tool_group in tool_groups]
        
        # Get MCP tools from components
        mcp_tools_list = [tool["name"] for tool in self.components["tools"]]
        
        if not mcp_tools_list:
            return []
            
        # Check if builtin::rag is in the tool groups and we have knowledge bases
        if "builtin::rag" in tool_groups_list and self.components["knowledge_bases"]:
            vector_db_ids = [kb["vector_db_name"] for kb in self.components["knowledge_bases"]]
            
            rag_tool = {
                "name": "builtin::rag",
                "args": {
                    "vector_db_ids": vector_db_ids,
                },
            }
            
            return mcp_tools_list + [rag_tool]
        
        # If no builtin::rag, just return MCP tools
        return mcp_tools_list

    def _get_model(self):
        if not self.components or not self.components["model_server"]:
            models = self._get_client().models.list()
            model_list = [model.identifier for model in models if model.api_model_type == "llm"]
            return model_list[0]
            
        return self.components["model_server"]["model_name"]

    def _create_agent(self, 
                    agent_type: AgentType,
                    model: str,
                    tools: list,
                    max_tokens: int):
        
        if agent_type == AgentType.REACT:
            return ReActAgent(
                self._get_client(),
                model=model,
                tools=tools,
                response_format={
                    "type": "json_schema",
                    "json_schema": ReActOutput.model_json_schema(),
                },
                sampling_params={"strategy": {"type": "greedy"}, "max_tokens": max_tokens},
            )
        else:
            return Agent(
                self._get_client(),
                model=model,
                instructions="You are a helpful assistant. When you use a tool always respond with a summary of the result.",
                tools=tools,
                sampling_params={"strategy": {"type": "greedy"}, "max_tokens": max_tokens},
            )

    async def _response_generator(self, turn_response):
        if self.session_state.get("agent_type") == AgentType.REACT:
            async for response in self._handle_react_response(turn_response):
                yield response
        else:
            async for response in self._handle_regular_response(turn_response):
                yield response

    def _handle_react_response(self, turn_response):
        current_step_content = ""
        final_answer = None
        tool_results = []

        for response in turn_response:
            if not hasattr(response.event, "payload"):
                yield (
                    "\n\n🚨 :red[_Llama Stack server Error:_]\n"
                    "The response received is missing an expected `payload` attribute.\n"
                    "This could indicate a malformed response or an internal issue within the server.\n\n"
                    f"Error details: {response}"
                )
                return

            payload = response.event.payload

            if payload.event_type == "step_progress" and hasattr(payload.delta, "text"):
                current_step_content += payload.delta.text
                continue

            if payload.event_type == "step_complete":
                step_details = payload.step_details

                if step_details.step_type == "inference":
                    yield from self._process_inference_step(current_step_content, tool_results, final_answer)
                    current_step_content = ""
                elif step_details.step_type == "tool_execution":
                    tool_results = self._process_tool_execution(step_details, tool_results)
                    current_step_content = ""
                else:
                    current_step_content = ""

        if not final_answer and tool_results:
            yield from self._format_tool_results_summary(tool_results)

    def _process_inference_step(self, current_step_content, tool_results, final_answer):
        try:
            react_output_data = json.loads(current_step_content)
            thought = react_output_data.get("thought")
            action = react_output_data.get("action")
            answer = react_output_data.get("answer")

            if answer and answer != "null" and answer is not None:
                final_answer = answer

            # TODO : Tools
            # if thought:
            #     with st.expander("🤔 Thinking...", expanded=False):
            #         st.markdown(f":grey[__{thought}__]")

            # if action and isinstance(action, dict):
            #     tool_name = action.get("tool_name")
            #     tool_params = action.get("tool_params")
            #     with st.expander(f'🛠 Action: Using tool "{tool_name}"', expanded=False):
            #         st.json(tool_params)

            if answer and answer != "null" and answer is not None:
                yield f"\n\n✅ **Final Answer:**\n{answer}"

        except json.JSONDecodeError:
            yield f"\n\nFailed to parse ReAct step content:\n```json\n{current_step_content}\n```"
        except Exception as e:
            yield f"\n\nFailed to process ReAct step: {e}\n```json\n{current_step_content}\n```"

        return final_answer

    def _format_tool_results_summary(self, tool_results):
        yield "\n\n**Here's what I found:**\n"
        for tool_name, content in tool_results:
            try:
                parsed_content = json.loads(content)

                if tool_name == "web_search" and "top_k" in parsed_content:
                    yield from self._format_web_search_results(parsed_content)
                elif "results" in parsed_content and isinstance(parsed_content["results"], list):
                    yield from self._format_results_list(parsed_content["results"])
                elif isinstance(parsed_content, dict) and len(parsed_content) > 0:
                    yield from self._format_dict_results(parsed_content)
                elif isinstance(parsed_content, list) and len(parsed_content) > 0:
                    yield from self._format_list_results(parsed_content)
            except json.JSONDecodeError:
                yield f"\n**{tool_name}** was used but returned complex data. Check the observation for details.\n"
            except (TypeError, AttributeError, KeyError, IndexError) as e:
                print(f"Error processing {tool_name} result: {type(e).__name__}: {e}")

    def _process_tool_execution(self, step_details, tool_results):
        try:
            if hasattr(step_details, "tool_responses") and step_details.tool_responses:
                for tool_response in step_details.tool_responses:
                    tool_name = tool_response.tool_name
                    content = tool_response.content
                    tool_results.append((tool_name, content))
                    # with st.expander(f'⚙️ Observation (Result from "{tool_name}")', expanded=False):
                    #     try:
                    #         parsed_content = json.loads(content)
                    #         st.json(parsed_content)
                    #     except json.JSONDecodeError:
                    #         st.code(content, language=None)

                    print()
                    try:
                        parsed_content = json.loads(content)
                        print(parsed_content)
                    except json.JSONDecodeError:
                        print(content, language=None)
                    
            else:
                # with st.expander("⚙️ Observation", expanded=False):
                #     st.markdown(":grey[_Tool execution step completed, but no response data found._]")
                print("⚙️ Observation")
                print(":grey[_Tool execution step completed, but no response data found._]")
                pass
        except Exception as e:
            # with st.expander("⚙️ Error in Tool Execution", expanded=False):
            #     st.markdown(f":red[_Error processing tool execution: {str(e)}_]")
            print(f":red[_Error processing tool execution: {str(e)}_]")

        return tool_results

    def _format_web_search_results(self, parsed_content):
        for i, result in enumerate(parsed_content["top_k"], 1):
            if i <= 3:
                title = result.get("title", "Untitled")
                url = result.get("url", "")
                content_text = result.get("content", "").strip()
                yield f"\n- **{title}**\n  {content_text}\n  [Source]({url})\n"
    def _format_results_list(self, results):
        for i, result in enumerate(results, 1):
            if i <= 3:
                if isinstance(result, dict):
                    name = result.get("name", result.get("title", "Result " + str(i)))
                    description = result.get("description", result.get("content", result.get("summary", "")))
                    yield f"\n- **{name}**\n  {description}\n"
                else:
                    yield f"\n- {result}\n"
    def _format_dict_results(self, parsed_content):
        yield "\n```\n"
        for key, value in list(parsed_content.items())[:5]:
            if isinstance(value, str) and len(value) < 100:
                yield f"{key}: {value}\n"
            else:
                yield f"{key}: [Complex data]\n"
        yield "```\n"

    def _format_list_results(self, parsed_content):
        yield "\n"
        for _, item in enumerate(parsed_content[:3], 1):
            if isinstance(item, str):
                yield f"- {item}\n"
            elif isinstance(item, dict) and "text" in item:
                yield f"- {item['text']}\n"
            elif isinstance(item, dict) and len(item) > 0:
                first_value = next(iter(item.values()))
                if isinstance(first_value, str) and len(first_value) < 100:
                    yield f"- {first_value}\n"

    async def _handle_regular_response(self, turn_response):
        async for response in turn_response:
            if hasattr(response.event, "payload"):
                print(response.event.payload)
                if response.event.payload.event_type == "step_progress":
                    if hasattr(response.event.payload.delta, "text"):
                        yield response.event.payload.delta.text
                if response.event.payload.event_type == "step_complete":
                    if response.event.payload.step_details.step_type == "tool_execution":
                        if response.event.payload.step_details.tool_calls:
                            tool_name = str(response.event.payload.step_details.tool_calls[0].tool_name)
                            yield f'\n\n🛠 :grey[_Using "{tool_name}" tool:_]\n\n'
                        else:
                            yield "No tool_calls present in step_details"
            else:
                yield f"Error occurred in the Llama Stack Cluster: {response}"

    async def stream(self, prompt: str, db):
        # Fetch components if not already fetched
        if not self.components:
            await self._fetch_components(db)
            
        agent_type = AgentType.REGULAR
        self.session_state["agent_type"] = agent_type
        max_tokens = 512 # 4096
        agent = self._create_agent(agent_type, self._get_model(), self._get_tools(), max_tokens)
        if "agent_session_id" not in self.session_state:
            self.session_state["agent_session_id"] = agent.create_session(session_name=f"tool_demo_{uuid.uuid4()}")

        session_id = self.session_state["agent_session_id"]

        turn_response = agent.create_turn(
            session_id=session_id,
            messages=[{"role": "user", "content": prompt}],
            stream=True,
        )

        async for response in self._response_generator(turn_response):
            yield response
        
        
