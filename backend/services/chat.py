import enum
from http.client import HTTPException
import json
import uuid
import os
from fastapi import Depends
from llama_stack_client.types.shared_params.agent_config import AgentConfig
from llama_stack_client.lib.agents.react.tool_parser import ReActOutput
from ..api.llamastack import client
from ..virtual_agents.agents import ExistingAgent, ExistingReActAgent

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

    def __init__(self, session_state, assistant, logger):
        os.environ["TOKENIZERS_PARALLELISM"] = "false"
        
        # Initialize session_state if needed
        self.session_state = None
        if not session_state:
            self.session_state = {}
            self.session_state["agent_type"] = str(AgentType.REGULAR)
            self.session_state["messages"] = []
        else:
            self.session_state = session_state

        # Set a temporary session_id if not yet created
        self.session_id = "session_not_set"
        if "agent_session_id" in self.session_state:
            self.session_id = self.session_state["agent_session_id"]
        
        self.agent_id = assistant.agent_id
        self.agent_config = assistant.agent_config
        self.model = assistant.agent_config.get("model", None)
        self.tools = assistant.agent_config.get("toolgroups", [])
        self.log = logger
        
    def _reset_agent(self):
        self.session_state.clear()
        # st.cache_resource.clear()
        pass

    def _get_client(self):
        return client

    def _get_tools(self):
        # Get the list of tools from the knowledge bases and mcp servers
        
        # tool_groups = self._get_client().toolgroups.list()
        # tool_groups_list = [tool_group.identifier for tool_group in tool_groups]
        # mcp_tools_list = [tool for tool in tool_groups_list if tool.startswith("mcp::")]
        # builtin_tools_list = [tool for tool in tool_groups_list if not tool.startswith("mcp::")]
        # toolgroup_selection = tool_groups_list
        
        # selected_vector_dbs = self._get_client().vector_dbs.list() or []
        # for i, tool_name in enumerate(toolgroup_selection):
        #     if tool_name == "builtin::rag":
        #         tool_dict = dict(
        #             name="builtin::rag",
        #             args={
        #                 "vector_db_ids": list(selected_vector_dbs),
        #             },
        #         )
        #         toolgroup_selection[i] = tool_dict
        # return toolgroup_selection
        
        # Tool selection is done when agents are created with a post to /virtual_assistants
        return self.tools


    def _get_model(self):
        # Get the list of models from llama stack
        # models = self._get_client().models.list()
        # model_list = [model.identifier for model in models if model.api_model_type == "llm"]
        # return model_list[0]
        return self.model

    def _create_agent_with_id(self,
                           agent_type: AgentType,
                           agent_id: str,
                           agent_config: AgentConfig):
        """Create an agent with an existing agent_id without calling initialize()."""

        # TODO: Pass in agent_config and avoid calls to llama stack api

        if agent_type == AgentType.REACT:
            return ExistingReActAgent(
                self._get_client(),
                agent_id=agent_id,
                agent_config=agent_config,
                # parameters are populated from the agent config
                # sampling_params={"strategy": {"type": "greedy"}, "max_tokens": max_tokens},
                response_format={
                    "type": "json_schema",
                    "json_schema": ReActOutput.model_json_schema(),
                },

            )
        else:
            return ExistingAgent(
                self._get_client(),
                agent_id=agent_id,
                agent_config=agent_config,
                # parameters are populated from the agent config
                # instructions="You are a helpful assistant. When you use a tool always respond with a summary of the result.",
                # sampling_params={"strategy": {"type": "greedy"}, "max_tokens": max_tokens},
            )

    def _response_generator(self, turn_response):
        if self.session_state.get("agent_type") == AgentType.REACT:
            return self._handle_react_response(turn_response)
        else:
            return self._handle_regular_response(turn_response)

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

    def _handle_regular_response(self, turn_response):
        for response in turn_response:
            if hasattr(response.event, "payload"):
                print(response.event.payload)
                if response.event.payload.event_type == "step_progress":
                    if hasattr(response.event.payload.delta, "text"):
                        yield response.event.payload.delta.text
                if response.event.payload.event_type == "step_complete":
                    # if response.event.payload.step_details.step_type == "inference":
                    #     # TODO: Save assistant responses in session_state ?
                    #     if hasattr(response.event.payload.step_details, "api_model_response"):
                    #         completion_message = response.event.payload.step_details.api_model_response
                    #         self.session_state["messages"].append(completion_message.to_json())
                    #         yield "\n\nend_of_turn\n\n"
                    if response.event.payload.step_details.step_type == "tool_execution":
                        if response.event.payload.step_details.tool_calls:
                            tool_name = str(response.event.payload.step_details.tool_calls[0].tool_name)
                            yield f'\n\n🛠 :grey[_Using "{tool_name}" tool:_]\n\n'
                        else:
                            yield "No tool_calls present in step_details"
            else:
                yield f"Error occurred in the Llama Stack Cluster: {response}"

    def stream(self, prompt: str):
        # Force defaulting to REGULAR agent type
        agent_type = AgentType.REGULAR
        self.session_state["agent_type"] = str(agent_type)

        # Add agent_id to session state if not present in session state
        if "agent_id" not in self.session_state:
            self.session_state["agent_id"] = self.agent_id
            self.log.info(f"Added agent to session state with id: {self.session_state['agent_id']}")

        # Configure agent
        agent = None
        try:
            agent = self._create_agent_with_id(agent_type, self.agent_id, self.agent_config)
            self.log.info(f"Using existing agent: {agent.agent_id}")
        except Exception as e:
            self.log.error(f"Error getting existing agent: {str(e)}")
            # Invalidate old session
            del self.session_state["agent_id"]
            del self.session_state["agent_session_id"]
            del self.session_state["messages"]
            raise HTTPException(status_code=500, detail=f"Error using agent {self.session_state['agent_id']}")

        # Create session if not present in session state
        if "agent_session_id" not in self.session_state:
            self.session_state["agent_session_id"] = agent.create_session(session_name=f"tool_demo_{uuid.uuid4()}")
            self.log.info(f"Created a new session: {self.session_state['agent_session_id']}")
        else:
            self.log.info(f"Using existing session: {self.session_state['agent_session_id']}")

        # "Export" session_id so that the background task can save it to the database when the stream ends
        self.session_id = self.session_state["agent_session_id"]

        # Initialize messages array incase session was invalidated
        if "messages" not in self.session_state:
            self.session_state["messages"] = []

        # Append user message to session
        self.session_state["messages"].append({"role": "user", "content": prompt})

        turn_response = agent.create_turn(
            session_id=self.session_id,
            messages=self.session_state["messages"],
            stream=True,
        )

        yield from self._response_generator(turn_response)
