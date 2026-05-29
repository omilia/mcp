from contextlib import asynccontextmanager
from typing import Annotated
from fastmcp import FastMCP
from fastmcp.utilities.logging import get_logger
from dependencies import AllowedGroupsDep, AuthorizationDep, ExecutionModeDep
from main import mcp as public_orc_mcp
from ocp.orchestrator import OrchestratorClient
from ocp.pathfinder import PathfinderClient
from payload_schemas import AgentInput, AvailableAgent, QueueInfo
from tags import APPROVAL, AUTOMATION_LVL_1, AUTOMATION_LVL_4, GROUP_FILTER, ONBOARDING_IMPLEMENTATION, PUBLIC
from tool_decorators import tool_with_callbacks
from utils import GroupAccessError
logger = get_logger(__name__)

@asynccontextmanager
async def lifespan(app: FastMCP):
    app.mount(public_orc_mcp)
    yield
mcp = FastMCP('OCP', lifespan=lifespan)
tool = tool_with_callbacks(mcp)

@tool(tags=[APPROVAL, GROUP_FILTER, ONBOARDING_IMPLEMENTATION, PUBLIC], meta={'ui_label': 'Adding a Knowledge Base to your Agent'})
async def add_faq_to_agent(url: str, pathfinder_project_id: str, agent_id: str, Authorization: AuthorizationDep=None, execution_mode: ExecutionModeDep='normal', allowed_groups: AllowedGroupsDep=None) -> dict:
    """
    Enhance an existing autonomous agent with a FAQ/knowledge base from a given URL using Pathfinder.
    This will analyze the content at the URL and generate a bot that can answer frequently asked questions.
    The user must have first chosen a Pathfinder project and an agent.

    Next: call `deploy_orc_app` to make the knowledge live, then `talk_to_app`
    with a knowledge-base question to verify the agent can answer from the new FAQ.

    Args:
        url: The URL to analyze and create FAQ from
        pathfinder_project_id: The ID of the Pathfinder project to use
        agent_id: The ID of the agent to enhance. This can not be a name or component_id, it must be the actual agent ID.

    Auth note: this Pathfinder call requires a Bearer JWT; PAT-only auth returns 401.
    """
    FAQ_TAG = 'Draft'
    async with PathfinderClient(auth_header=Authorization) as pathfinder_client:
        logger.info(f'Creating FAQ vector store: {pathfinder_project_id}')
        project = await pathfinder_client.get_project(pathfinder_project_id)
        project_name = project.get('name')
        project_group = project.get('group')
        if allowed_groups:
            if project_group not in allowed_groups:
                raise GroupAccessError(project_group)
        await pathfinder_client.create_faq(project_id=pathfinder_project_id, urls=url, follow_links_one_level_down=True)
        logger.info(f'Created FAQ vector store: {pathfinder_project_id}')
        logger.info(f'Project name: {project_name}, Project group: {project_group}')
        knowledge_bases = await pathfinder_client.list_faqs()
        faq_id = None
        for knowledge_base in knowledge_bases.get('data', []):
            if knowledge_base.get('project_name') == project_name and knowledge_base.get('group') == project_group and (knowledge_base.get('tag') == FAQ_TAG):
                faq_id = knowledge_base.get('index_name')
                break
        if not faq_id:
            raise ValueError(f'No FAQ vector store found for project {project_name} in group {project_group} with tag {FAQ_TAG}')
        logger.info(f'FoundFAQ vector store ID: {faq_id}')
    async with OrchestratorClient(auth_header=Authorization) as orchestrator_client:
        agent_info = await orchestrator_client.get_agent(agent_id)
        agent_component_id = agent_info.get('component_id')
        existing_sub_agents = agent_info.get('components', {}).get('agents', [])
        logger.info(f'Agent component ID: {agent_component_id}')
        knowledge_base_agent_data = {'name': f'Pathfinder.{faq_id}', 'description': 'A specialized FAQ Agent. Answers Why, What, How and When questions.', 'agent_id': faq_id, 'input': []}
        await orchestrator_client.update_agent(agent_id, agents=existing_sub_agents + [knowledge_base_agent_data])
        logger.info(f'Updated agent kb data: {agent_id}')
        return {'message': 'I have an agent with all of your information, ready to serve customers', 'concierge_agent_name': agent_info.get('name'), 'concierge_agent_id': agent_id}

@tool(tags=['orchestrator', 'agents', APPROVAL, GROUP_FILTER, ONBOARDING_IMPLEMENTATION, AUTOMATION_LVL_4, PUBLIC], meta={'ui_label': 'Creating Webservice Agent'})
async def create_webservice_agent(miniapp_id: Annotated[str, 'The miniapp_id of a webservice tool'], group: str, agent_name: str, agent_instructions: str, tool_name: str, tool_description: str, webservice_tool_inputs: list[AgentInput] | None=None, Authorization: AuthorizationDep=None, execution_mode: ExecutionModeDep='normal', allowed_groups: AllowedGroupsDep=None) -> dict:
    """
    Create a new autonomous agent that uses a webservice tool. You must extract meaningful inputs from the
    info you have so far in order to create a descriptive agent and tool definition.
    Before calling this tool, you must first have creates a web_service_tool.

    Args:
        miniapp_id: The ID of the miniapp to use as the webservice tool
        group: The OCP group for the new agent. Ask the user if you don't know this.
        agent_name: A descriptive name for the new agent in CamelCase
        agent_instructions: A brief description of the new agent's instructions. Eg "You are in charge of making payments. Ask any info you need and call the respsctive tool.
        tool_name: A descriptive name for the new tool in CamelCase
        tool_description: A brief description for the tool. For example "Use this tool to make payments"
        tool_inputs: A list of dicts for the inputs for the webservice tool. For example [{"name": "amount", "description": "The amount to pay"}, {"name": "account_number", "description": "The account number to pay from"}]. Use this exact format!
    """
    if webservice_tool_inputs is None:
        webservice_tool_inputs = []
    if allowed_groups:
        if group not in allowed_groups:
            raise GroupAccessError(group)
    async with OrchestratorClient(auth_header=Authorization) as client:
        agent = await client.create_agent(group=group, name=agent_name, agent_type='task')
        agent_id = agent.get('id')
        if type(webservice_tool_inputs) is dict:
            webservice_tool_inputs = list(webservice_tool_inputs.values())
        webservice_tool_inputs = [i.model_dump() if isinstance(i, AgentInput) else i for i in webservice_tool_inputs]
        return await client.update_agent(agent_id=agent_id, instructions=[agent_instructions], tools=[{'name': tool_name, 'tool_id': miniapp_id, 'description': tool_description, 'inputs': webservice_tool_inputs}])

@tool(tags=['orchestrator', 'agents', APPROVAL, GROUP_FILTER, ONBOARDING_IMPLEMENTATION, PUBLIC], meta={'ui_label': 'Adding Escalation Queue'})
async def add_escalation_queue_to_agent(agent_id: str, queue_info: list[QueueInfo], Authorization: AuthorizationDep=None, execution_mode: ExecutionModeDep='normal', allowed_groups: AllowedGroupsDep=None) -> dict:
    """
    Add one or more escalation queues to an existing agent. This will allow the agent to escalate to humans using those queues.

    Args:
        agent_id: The ID of the agent to add the escalation queue to
        queue_info: A list of escalation queue information containing name, queue_id, and description
    """
    async with OrchestratorClient(auth_header=Authorization) as client:
        if allowed_groups:
            group = await client.get_agent_group(agent_id)
            if group not in allowed_groups:
                raise GroupAccessError(group)
        return await client.update_agent(agent_id=agent_id, escalate_to_human=[q.model_dump() for q in queue_info])

@tool(tags=['orchestrator', 'agents', APPROVAL, GROUP_FILTER, ONBOARDING_IMPLEMENTATION, AUTOMATION_LVL_4, PUBLIC], meta={'ui_label': 'Adding Tool to Agent'})
async def add_tool_to_webservice_agent(agent_id: str, miniapp_id: str, tool_name: str, tool_description: str, webservice_tool_inputs: list[AgentInput] | None=None, Authorization: AuthorizationDep=None, execution_mode: ExecutionModeDep='normal', allowed_groups: AllowedGroupsDep=None) -> dict:
    """
    Add a tool to an existing autonomous agent.

    Args:
        agent_id: The ID of the agent to add the tool to
        miniapp_id: The ID of the miniapp to use as the webservice tool
        tool_name: A descriptive name for the new tool in CamelCase
        tool_description: A brief description for the tool. For example "Use this tool to make payments"
        tool_inputs: A list of dicts for the inputs for the webservice tool. For example [{"name": "amount", "description": "The amount to pay"}, {"name": "account_number", "description": "The account number to pay from"}]. You must follow this exact input format.
    """
    if webservice_tool_inputs is None:
        webservice_tool_inputs = []
    async with OrchestratorClient(auth_header=Authorization) as client:
        agent = await client.get_agent(agent_id)
        if allowed_groups:
            if agent.get('group') not in allowed_groups:
                raise GroupAccessError(agent.get('group'))
        agent_data = agent.get('components', [])
        existing_tools = agent_data.get('tools', [])
        if type(webservice_tool_inputs) is dict:
            webservice_tool_inputs = list(webservice_tool_inputs.values())
        webservice_tool_inputs = [i.model_dump() if isinstance(i, AgentInput) else i for i in webservice_tool_inputs]
        existing_tools.append({'name': tool_name, 'tool_id': miniapp_id, 'description': tool_description, 'inputs': webservice_tool_inputs})
        return await client.update_agent(agent_id=agent_id, tools=existing_tools)

@tool(tags=['orchestrator', 'agents', APPROVAL, GROUP_FILTER, PUBLIC])
async def add_knowledge_base_to_agent(agent_id: str, knowledge_base_id: str, Authorization: AuthorizationDep=None, execution_mode: ExecutionModeDep='normal', allowed_groups: AllowedGroupsDep=None) -> dict:
    """
    Add a knowledge base to an existing agent.

    Next: call `deploy_orc_app` to make the knowledge live, then `talk_to_app`
    with a knowledge-base question to verify the agent can answer from it.

    Args:
        agent_id: The ID of the agent to add the knowledge base to
        knowledge_base_id: The ID of the knowledge base to add to the agent

    Auth note: this Pathfinder call requires a Bearer JWT; PAT-only auth returns 401.
    """
    async with OrchestratorClient(auth_header=Authorization) as client:
        agent = await client.get_agent(agent_id)
        if allowed_groups:
            if agent.get('group') not in allowed_groups:
                raise GroupAccessError(agent.get('group'))
        agent_data = agent.get('components', [])
        existing_agents = agent_data.get('agents', [])
        existing_agents.append({'name': f'Pathfinder.{knowledge_base_id}', 'description': 'A specialized FAQ Agent. Answers Why, What, How and When questions.', 'input': []})
        return await client.update_agent(agent_id=agent_id, agents=existing_agents)

@tool(tags=['orchestrator', 'agents', APPROVAL, GROUP_FILTER, PUBLIC])
async def add_agent_to_concierge(agent_id: str, group: str, agent_name: str, agent_description: str, Authorization: AuthorizationDep=None, execution_mode: ExecutionModeDep='normal', allowed_groups: AllowedGroupsDep=None) -> dict:
    """
    Add an agent to the concierge agent.

    Args:
        agent_id: The ID of the agent to add to the concierge
        group: The OCP group for the new agent. Use same group as the concierge agent or ask the user if you dont know it.
        agent_name: A descriptive name for the agent you are about to add. For example "PaymentAgent"
        agent_description: A brief description of the agent's capabilities so that the concierge agent can delegate to it. for example "Use this agent to process payments"
    """
    async with OrchestratorClient(auth_header=Authorization) as client:
        if allowed_groups:
            if group not in allowed_groups:
                raise GroupAccessError(group)
        all_agents = await client.list_agents(group=group)
        concierge_agent = next((agent for agent in all_agents if 'concierge' in agent.get('name', '').lower()), None)
        if not concierge_agent:
            return {'error': 'No concierge agent found'}
        concierge_agent_id = concierge_agent.get('id')
        concierge_agent = await client.get_agent(concierge_agent_id)
        existing_concierge_agents = concierge_agent.get('components', {}).get('agents', [])
        concierge_agent_id = concierge_agent.get('id')
        added_agent = await client.get_agent(agent_id)
        added_agent_id = added_agent.get('component_id')
        return await client.update_agent(agent_id=concierge_agent_id, agents=existing_concierge_agents + [{'name': agent_name, 'agent_id': added_agent_id, 'description': agent_description, 'input': []}])

@tool(tags=['pathfinder', PUBLIC])
async def list_knowledge_bases(Authorization: AuthorizationDep=None, execution_mode: ExecutionModeDep='normal') -> dict:
    """List knowledge bases (FAQ vector stores).

    Returns:
        dict: The response containing the list of FAQ vector stores

    Auth note: this Pathfinder call requires a Bearer JWT; PAT-only auth returns 401.
    """
    async with PathfinderClient(auth_header=Authorization) as client:
        return await client.list_faqs()
FAQ_TASK_AGENT_BASE_INSTRUCTION = "You are an FAQ assistant. Answer questions only based on the information you have been explicitly provided in your instructions. If you don't have the information to answer a question, politely indicate that you cannot help with that specific topic."

@tool(tags=['orchestrator', 'agents', AUTOMATION_LVL_1, APPROVAL, GROUP_FILTER, PUBLIC])
async def update_concierge(concierge_agent_id: str, agents: list[AvailableAgent], Authorization: AuthorizationDep=None, execution_mode: ExecutionModeDep='normal', allowed_groups: AllowedGroupsDep=None) -> dict:
    """Update the concierge agent."""
    async with OrchestratorClient(auth_header=Authorization) as client:
        if allowed_groups:
            group = await client.get_agent_group(concierge_agent_id)
            if group not in allowed_groups:
                raise GroupAccessError(group)
        return await client.update_agent(agent_id=concierge_agent_id, agents=[a.model_dump() for a in agents])
if __name__ == '__main__':
    mcp.run()
