import re
from datetime import datetime, timedelta
from pathlib import Path
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from fastmcp.utilities.logging import get_logger
from dependencies import AllowedGroupsDep, AuthorizationDep, ExecutionModeDep
from ocp.chat import ChatClient, ChatError
from ocp.insights import InsightsClient
from ocp.integrations import IntegrationsClient
from ocp.metrics import MetricsClient
from ocp.miniapps import MiniAppsClient
from ocp.orchestrator import OrchestratorClient
from ocp.pathfinder import PathfinderClient
from ocp.environments_manager import EnvironmentsManagerClient
from tags import APPROVAL, AUTOMATION_LVL_1, AUTOMATION_LVL_4, EXPLAIN_FLOW, GROUP_FILTER, ONBOARDING_IMPLEMENTATION, PUBLIC
from tool_decorators import tool_with_callbacks
from utils import WS_RESPONSE_BODY, GroupAccessError, validate_available_locales
logger = get_logger(__name__)
_GUIDES_DIR = Path(__file__).parent / 'guides'
_AVAILABLE_GUIDES = ('index', 'build_concierge_app', 'add_knowledge', 'test_and_improve')

async def _resolve_group(client: OrchestratorClient, group: str | None, name: str) -> 'str | dict':
    """Return the group to use, or a structured response asking the user to pick one."""
    if group:
        return group
    groups = await client.list_groups()
    if not groups:
        raise ToolError('No groups found. Please specify a group explicitly.')
    if len(groups) == 1:
        return groups[0]
    return {'action_required': 'select_group', 'message': f"Multiple groups available. Which group should '{name}' be created in?", 'available_groups': groups}
mcp = FastMCP('OCP')
tool = tool_with_callbacks(mcp)

@tool(tags=['miniapps', PUBLIC])
async def search_miniapps(search_term: str | None=None, Authorization: AuthorizationDep=None, execution_mode: ExecutionModeDep='normal') -> dict:
    """Search miniapps. Useful to return a list of miniapps that match a search term.
    Args:
        search_term: Optional search term to filter miniapps
    """
    async with MiniAppsClient(auth_header=Authorization) as client:
        apps = await client.get_apps(search_term=search_term)
        return apps

@tool(tags=['miniapps', APPROVAL, GROUP_FILTER, ONBOARDING_IMPLEMENTATION, AUTOMATION_LVL_4, PUBLIC], meta={'ui_label': 'Creating Webservice Tool'})
async def create_webservice_miniapp(name: str, group: str, url: str, method: str='GET', body: str | None=None, headers: list[dict[str, str]] | None=None, form_data_pairs: list[dict[str, str]] | None=None, timeout: int | None=None, Authorization: AuthorizationDep=None, execution_mode: ExecutionModeDep='normal', allowed_groups: AllowedGroupsDep=None) -> dict:
    """
    Create a new WebService miniapp. Can be used as a tool in Task Agents to hit customer APIs.
    If you pass new values for the `headers` and `form_data_pairs`, existing data will be replaced. Make sure to pass the whole list.
    In `url`, `headers`, `body`, and `form_data_pairs`, you can enclose strings in double brackets to use 
    dynamic inputs, for example `[{"key": "field1", "value": "{{UserId}}"}]`

    Args:
        name: A descriptive name for the new miniapp in CamelCase
        group: The OCP group for the new miniapp
        url: The request URL. Use double brackets for dynamic inputs, e.g. .../users?userID={{ANI}}
        method: The HTTP method (e.g., GET, POST, PUT, DELETE). Defaults to "GET"
        body: The request body for the POST, PUT or DELETE methods.
        headers: List of header key-value pairs, e.g. [{"key": "Authorization", "value": "Bearer token"}]. Replaces existing headers.
        form_data_pairs: List of form data key-value pairs, e.g. [{"key": "field1", "value": "value1"}]. Replaces existing form data pairs.
        timeout: Request timeout in milliseconds

    Returns:
        A dictionary containing the miniapp_id.
    """
    if allowed_groups:
        if group not in allowed_groups:
            raise GroupAccessError(group)
    async with MiniAppsClient(auth_header=Authorization) as client:
        miniapp_id = await client._create_webservice_miniapp(name=name, group=group)
        miniapp_json = await client.get_miniapp(miniapp_id)
        request = miniapp_json['model']['wsCall']['request']
        request['url'] = url
        request['method'] = method
        if body is not None:
            request['body'] = body
        if headers is not None:
            request['header'] = headers
        if form_data_pairs is not None:
            request['formDataPairs'] = form_data_pairs
            request['isFormData'] = len(form_data_pairs) > 0
        if timeout is not None:
            request['timeout'] = timeout
        miniapp_json['model']['outputs'] = WS_RESPONSE_BODY
        await client.update_miniapp(miniapp_id, miniapp_json)
        return {'message': 'I have created a webservice tool with the given URL', 'miniapp_id': miniapp_id}

@tool(tags=['miniapps', PUBLIC])
async def edit_webservice_miniapp(miniapp_id: str, url: str | None=None, method: str | None=None, body: str | None=None, headers: list[dict[str, str]] | None=None, form_data_pairs: list[dict[str, str]] | None=None, timeout: int | None=None, Authorization: AuthorizationDep=None, execution_mode: ExecutionModeDep='normal') -> dict:
    """
    Edit a WebService miniapp's request configuration. WebService miniapps are used as tools in Task Agents to hit customer APIs.
    If you pass new values for the `headers` and `form_data_pairs`, existing data will be replaced. Make sure to pass the whole list.
    In `url`, `headers`, `body`, and `form_data_pairs`, you can enclose strings in double brackets to use 
    dynamic inputs, for example `[{"key": "field1", "value": "{{UserId}}"}]`

    Args:
        miniapp_id: The ID of the WebService miniapp to edit
        url: The request URL
        method: The HTTP method (e.g., POST, GET, PUT, DELETE)
        body: The request body
        headers: List of header key-value pairs, e.g. [{"key": "Authorization", "value": "Bearer token"}]. Replaces existing headers.
        form_data_pairs: List of form data key-value pairs, e.g. [{"key": "field1", "value": "value1"}]. Replaces existing form data pairs.
        timeout: Request timeout in milliseconds
    """
    async with MiniAppsClient(auth_header=Authorization) as client:
        miniapp_json = await client.get_miniapp(miniapp_id)
        request = miniapp_json['model']['wsCall']['request']
        if url is not None:
            request['url'] = url
        if method is not None:
            request['method'] = method
        if body is not None:
            request['body'] = body
        if headers is not None:
            request['header'] = headers
        if form_data_pairs is not None:
            request['formDataPairs'] = form_data_pairs
            request['isFormData'] = len(form_data_pairs) > 0
        if timeout is not None:
            request['timeout'] = timeout
        return await client.update_miniapp(miniapp_id, miniapp_json)

@tool(tags=['miniapps', EXPLAIN_FLOW, PUBLIC])
async def get_miniapp(miniapp_id: str, Authorization: AuthorizationDep=None, execution_mode: ExecutionModeDep='normal') -> dict:
    """Get a specific miniapp by its ID. Useful to return various information about a miniapp.

    Args:
        miniapp_id: The ID of the miniapp to retrieve

    Returns:
        The miniapp data as a dictionary
    """
    async with MiniAppsClient(auth_header=Authorization) as client:
        return await client.get_miniapp(miniapp_id)

@tool(tags=['miniapps', APPROVAL, GROUP_FILTER, PUBLIC])
async def set_miniapp_prompt(miniapp_id: str, prompt_type: str, prompt: str, locale: str | None='en-US', Authorization: AuthorizationDep=None, execution_mode: ExecutionModeDep='normal', allowed_groups: AllowedGroupsDep=None) -> dict:
    """Set various types of prompts for a specific miniapp. Unified interface for setting welcome, initial, error and reaction prompts.

    Args:
        miniapp_id: The ID of the miniapp to set the prompt for
        prompt_type: The type of prompt to set. Can be one of:
            - "welcome" - The welcome message prompt
            - "initial" - The initial question prompt
            - "error_no_interpretation" - When system cannot interpret the user's input
            - "error_no_response" - When user provides no input
            - "error_global_errors" - For general system errors
            - "error_agent_request" - Response when user requests an agent
            - "error_critical_error" - For critical system errors
            - "error_max_disconfirmations" - When max confirmation retries reached
            - "error_max_wrong_inputs" - When max invalid inputs reached
            - "error_max_dtmf_inputs" - When max DTMF inputs reached
            - "reaction_greeting" - Response to user greetings
            - "reaction_no_match" - When input doesn't match expected responses
            - "reaction_same_state" - When user repeats same input
            - "reaction_nice_response" - Acknowledgement responses
        prompt: The prompt text to set
        locale: The locale to set the prompt for. Defaults to "en-US"
    """
    if allowed_groups:
        group = MiniAppsClient.get_miniapp_group(miniapp_id)
        if group not in allowed_groups:
            raise GroupAccessError(group)
    async with MiniAppsClient(auth_header=Authorization) as client:
        miniapp_json = await client.get_miniapp(miniapp_id)
        if prompt_type == 'welcome':
            miniapp_json_part = miniapp_json['model']['welcome']['locales']
            validate_available_locales(miniapp_json_part, locale)
            miniapp_json_part[locale]['omIVR']['normal'] = prompt
            return await client.update_miniapp(miniapp_id, miniapp_json)
        elif prompt_type == 'initial':
            miniapp_json_part = miniapp_json['model']['ask']['locales']
            validate_available_locales(miniapp_json_part, locale)
            miniapp_json_part[locale]['omIVR']['normal'] = prompt
            return await client.update_miniapp(miniapp_id, miniapp_json)
        error_type_map = {'error_no_interpretation': 'noInterpretation', 'error_no_response': 'noResponse', 'error_global_errors': 'globalErrors', 'error_agent_request': 'agentRequest', 'error_critical_error': 'criticalError', 'error_max_disconfirmations': 'maxDisconfirmations', 'error_max_wrong_inputs': 'maxWrongInputs', 'error_max_dtmf_inputs': 'maxDtmfInputs'}
        if prompt_type in error_type_map:
            error_path = error_type_map[prompt_type]
            miniapp_json_part = miniapp_json['model']['errors']['targetAction'][error_path]['locales']
            validate_available_locales(miniapp_json_part, locale)
            miniapp_json_part[locale]['omIVR']['normal'] = prompt
            return await client.update_miniapp(miniapp_id, miniapp_json)
        reaction_type_map = {'reaction_greeting': 'greetingReactionPrompts', 'reaction_no_match': 'noMatchReactionPrompts', 'reaction_same_state': 'sameStateReactionPrompts', 'reaction_nice_response': 'niceResponseReactionPrompts'}
        if prompt_type in reaction_type_map:
            reaction_path = reaction_type_map[prompt_type]
            miniapp_json_part = miniapp_json['model']['reactions'][reaction_path]['locales']
            validate_available_locales(miniapp_json_part, locale)
            miniapp_json_part[locale]['omIVR']['normal'] = prompt
            return await client.update_miniapp(miniapp_id, miniapp_json)
        valid_types = ['welcome', 'initial'] + list(error_type_map.keys()) + list(reaction_type_map.keys())
        raise ValueError(f"Invalid prompt_type. Must be one of: {', '.join(valid_types)}")

@tool(tags=['orchestrator', PUBLIC])
async def search_orchestrator_apps(search_term: str | None=None, Authorization: AuthorizationDep=None, execution_mode: ExecutionModeDep='normal') -> dict:
    """Search Orchestrator apps with optional search term.

    Args:
        search_term: Optional search term to filter apps
    """
    async with OrchestratorClient(auth_header=Authorization) as client:
        return await client.search_apps(search_term=search_term)

@tool(tags=['orchestrator', AUTOMATION_LVL_1, AUTOMATION_LVL_4, EXPLAIN_FLOW, ONBOARDING_IMPLEMENTATION, PUBLIC], meta={'ui_label': 'Fetching your Agent'})
async def get_orchestrator_app(canvas_id: str | None=None, app_id: str | None=None, Authorization: AuthorizationDep=None, execution_mode: ExecutionModeDep='normal') -> dict:
    """Get an Orchestrator application canvas contents. Can be used with either canvas_id or app_id.
    Users can ask for this by saying "show me the app", "show me the canvas", "app contents" or "show me the flow".
    The resulting JSON is a graph structure of nodes and edges athat describes a dialog flow.

    Args:
        canvas_id: The ID of the canvas to get. This is the ID of the application canvas, contained in the search_orchestrator_apps results.
        app_id: The ID of the app to get. This is the ID of the application, contained in the search_orchestrator_apps results.
    """
    async with OrchestratorClient(auth_header=Authorization) as client:
        if canvas_id:
            return await client.get_canvas(canvas_id)
        elif app_id:
            app = await client.get_app(app_id)
            canvas = await client.get_canvas(app['canvas'])
            return {'app_info': app, 'canvas': canvas}
        else:
            raise ValueError('Either canvas_id or app_id must be provided')

@tool(tags=['orchestrator', 'agents', APPROVAL, AUTOMATION_LVL_1, GROUP_FILTER, ONBOARDING_IMPLEMENTATION, PUBLIC], meta={'ui_label': 'Updating Agent Instructions'})
async def update_agent_instructions(agent_id: str, instructions: list[str], Authorization: AuthorizationDep=None, execution_mode: ExecutionModeDep='normal', allowed_groups: AllowedGroupsDep=None) -> dict:
    """Update an agent's instructions.

    Next: call `deploy_orc_app` to make changes live, then `talk_to_app` to verify
    the new behavior.

    Args:
        agent_id: The ID of the agent to update
        instructions: The list of instruction strings for the agent

    Returns:
        dict: The updated agent data
    """
    async with OrchestratorClient(auth_header=Authorization) as client:
        if allowed_groups:
            group = await client.get_agent_group(agent_id)
            if group not in allowed_groups:
                raise GroupAccessError(group)
        return await client.update_agent(agent_id=agent_id, instructions=instructions)

@tool(tags=['orchestrator', 'agents', APPROVAL, GROUP_FILTER, ONBOARDING_IMPLEMENTATION, PUBLIC], meta={'ui_label': 'Adding Concierge to Application'})
async def add_concierge_to_orc_app(app_id: str, agent_id: str, Authorization: AuthorizationDep=None, execution_mode: ExecutionModeDep='normal', allowed_groups: AllowedGroupsDep=None) -> dict:
    """Add an agent to an Orchestrator app's canvas as a Concierge node and update the flow.
    Only use this tool when creating a brand new application from scratch and want to add a concierge to it.
    Do not call this tool if the application already has a concierge.

    Next: configure the agent (e.g. `update_agent_instructions`, `add_faq_to_agent`,
    or add Task sub-agents) and then call `deploy_orc_app` to make it live.

    Args:
        app_id: The ID of the Orchestrator app
        agent_id: The ID of the agent to add to the app canvas

    Returns:
        dict: The updated canvas data
    """
    async with OrchestratorClient(auth_header=Authorization) as client:
        app = await client.get_app(app_id)
        if allowed_groups:
            group = app.get('group')
            if group not in allowed_groups:
                raise GroupAccessError(group)
        canvas_id = app.get('canvas')
        agent_data = await client.get_agent(agent_id)
        agent_component_id = agent_data.get('component_id')
        logger.info(f'Adding agent {agent_id} to canvas {canvas_id} as component {agent_component_id}')
        if not canvas_id:
            raise ValueError('The specified app does not contain a canvas ID.')
        return await client._update_canvas_with_concierge(canvas_id=canvas_id, agent_component_id=agent_component_id)

@tool(tags=['orchestrator', AUTOMATION_LVL_1, APPROVAL, GROUP_FILTER, ONBOARDING_IMPLEMENTATION, PUBLIC], meta={'ui_label': 'Deploying Application'})
async def deploy_orc_app(app_id: str, Authorization: AuthorizationDep=None, execution_mode: ExecutionModeDep='normal', allowed_groups: AllowedGroupsDep=None) -> dict:
    """Deploy an Orchestrator app.

    Next: call `talk_to_app` to test the deployed agent end-to-end.

    Args:
        app_id: The ID of the Orchestrator app to deploy

    Returns:
        dict: The deployment response
    """
    async with OrchestratorClient(auth_header=Authorization) as client:
        if allowed_groups:
            app = await client.get_app(app_id)
            group = app.get('group')
            if group not in allowed_groups:
                raise GroupAccessError(group)
        return await client._deploy_app(app_id)

@tool(tags=['orchestrator', APPROVAL, GROUP_FILTER, ONBOARDING_IMPLEMENTATION, PUBLIC], meta={'ui_label': 'Creating Application'})
async def create_orchestrator_app(name: str, group: str | None=None, Authorization: AuthorizationDep=None, execution_mode: ExecutionModeDep='normal', allowed_groups: AllowedGroupsDep=None) -> dict:
    """Create a new Orchestrator application.

    If `group` is omitted, available groups are fetched automatically. When only
    one group exists it is used; when multiple exist the tool returns an
    `action_required` response listing them so the user can pick one.

    Next: call `create_agent` (agent_type="concierge") to make a Concierge,
    then `add_concierge_to_orc_app` to wire it into this app's canvas.

    Args:
        name: The name of the new app. Must contain only letters and underscores.
        group: The OCP group for the new app. Omit to auto-detect.

    Returns:
        dict: The created app data including its ID and other metadata
    """
    async with OrchestratorClient(auth_header=Authorization) as client:
        resolved = await _resolve_group(client, group, name)
        if isinstance(resolved, dict):
            return resolved
        group = resolved
        if allowed_groups and group not in allowed_groups:
            raise GroupAccessError(group)
        return await client.create_app(group=group, name=name)

@tool(tags=['orchestrator', 'agents', APPROVAL, GROUP_FILTER, ONBOARDING_IMPLEMENTATION, PUBLIC], meta={'ui_label': 'Creating Agent'})
async def create_agent(name: str, group: str | None=None, agent_type: str='concierge', Authorization: AuthorizationDep=None, execution_mode: ExecutionModeDep='normal', allowed_groups: AllowedGroupsDep=None) -> dict:
    """
    Create a new agent. This can be either a Concierge agent—serving as the main block in an orchestrator
    application and containing all other agents as components—or a Task agent, which handles a single task and is
    typically included as a component of a Concierge agent.

    If `group` is omitted, available groups are fetched automatically. When only
    one group exists it is used; when multiple exist the tool returns an
    `action_required` response listing them so the user can pick one.

    Next: if this is a Concierge for a fresh app, call `add_concierge_to_orc_app`
    to add it to the canvas. If it's a Task agent, call
    `add_agent_to_concierge_by_id` to attach it as a sub-agent.

    Args:
        name: The name of the new agent
        group: The OCP group for the new agent. Omit to auto-detect.
        agent_type: The type of the new agent. Possible values: 'concierge', 'task'. Default is 'concierge'.

    Returns:
        dict: The created agent data including its ID and other metadata
    """
    async with OrchestratorClient(auth_header=Authorization) as client:
        resolved = await _resolve_group(client, group, name)
        if isinstance(resolved, dict):
            return resolved
        group = resolved
        if allowed_groups and group not in allowed_groups:
            raise GroupAccessError(group)
        return await client.create_agent(group=group, name=name, agent_type=agent_type)

@tool(tags=['orchestrator', 'agents', PUBLIC])
async def list_agents(Authorization: AuthorizationDep=None, execution_mode: ExecutionModeDep='normal') -> list[dict]:
    """List all agents.

    Returns:
        dict: The response containing the list of all agents
    """
    async with OrchestratorClient(auth_header=Authorization) as client:
        return await client.list_agents()

@tool(tags=['orchestrator', PUBLIC])
async def list_groups(Authorization: AuthorizationDep=None, execution_mode: ExecutionModeDep='normal') -> list[str]:
    """List all OCP groups the current user has access to.

    Useful before creating agents or apps to know which groups are available.
    Groups are derived from the user's accessible agents and apps.

    Returns:
        list[str]: Sorted list of group names
    """
    async with OrchestratorClient(auth_header=Authorization) as client:
        return await client.list_groups()

@tool(tags=['insights', PUBLIC])
async def search_dialog_logs(dialog_group: str=None, apps: list[str]=None, from_date: str=None, to_date: str=None, size: int=10, ani: list[str]=None, application_layer: bool=True, Authorization: AuthorizationDep=None, execution_mode: ExecutionModeDep='normal') -> list[dict]:
    """
    Search dialogs using various filter criteria. Can also be requested by users by saying
    "find sessions", "search logs" or "identify dialog logs".
    At least one of dialog_group or apps must be provided!

    Args:
        dialog_group (str, optional): The name of the OCP group to filter by
        apps (list): List of miniApp_ids or sandbox_flowapp_app_ids to filter by. This is not the same as the orchestrator app ID! One MUST get the sandbox_flowapp_app_id from the search_orchestrator_apps tool first.
        from_date (str, optional): Start date/time in ISO format or milliseconds timestamp. Defaults to 24 hours ago.
        to_date (str, optional): End date/time in ISO format or milliseconds timestamp. Defaults to now.
        size (int, optional): Number of results to return. Defaults to 10
        ani (list, optional): List of ANIs to filter by. ANI is the phone number of the caller.
        application_layer (bool, optional): Whether to include application layer. Defaults to True

    Returns:
        list[dict]: Search results containing matching dialogs
    """
    if not dialog_group and (not apps):
        raise ToolError('At least one of dialog_group or apps must be provided')
    if to_date is None:
        to_date = (datetime.utcnow() + timedelta(hours=2)).isoformat() + 'Z'
    if from_date is None:
        from_date = (datetime.utcnow() - timedelta(days=1)).isoformat() + 'Z'
    if apps is None:
        apps = []
    if dialog_group is None:
        dialog_group = apps[0].split('.')[-1]
    async with InsightsClient(auth_header=Authorization) as client:
        return await client.search_dialogs(apps=apps, from_date=from_date, to_date=to_date, size=size, ani=ani, dialog_group=dialog_group, application_layer=application_layer)

@tool(tags=['insights', ONBOARDING_IMPLEMENTATION, PUBLIC], meta={'ui_label': 'Fetching Dialog Logs'})
async def get_dialog_logs(dialog_id: str, Authorization: AuthorizationDep=None, execution_mode: ExecutionModeDep='normal'):
    """Get the dialog logs for a specific dialog ID. Useful for retrieving conversation history and analytics.

    Args:
        dialog_id: The ID of the dialog to retrieve logs for

    Returns:
        The dialog log data as a dictionary
    """
    async with InsightsClient(auth_header=Authorization) as client:
        return await client.get_dialog_log(dialog_id)

@tool(tags=['integrations', PUBLIC])
async def search_numbers(search_term: str | None=None, Authorization: AuthorizationDep=None, execution_mode: ExecutionModeDep='normal') -> dict:
    """Search (phone) numbers with optional search term.

    Args:
        search_term: Optional search term to filter numbers
    """
    async with IntegrationsClient(auth_header=Authorization) as client:
        return await client.search_numbers(search_term=search_term)

@tool(tags=['envs-manager', PUBLIC])
async def search_variable_collections(search_term: str | None=None, Authorization: AuthorizationDep=None, execution_mode: ExecutionModeDep='normal') -> dict:
    """Search variable collections with optional search term.

    Args:
        search_term: Optional search term to filter variable collections
    """
    client = EnvironmentsManagerClient(auth_header=Authorization)
    return client.get_variable_collections(search_term=search_term)

@tool(tags=['envs-manager', PUBLIC])
async def get_collection_variables(collection_id: str, Authorization: AuthorizationDep=None, execution_mode: ExecutionModeDep='normal') -> dict:
    """Get a list of all variables in a collection.

    Args:
        collection_id: The ID of the collection to get variables for
    """
    async with EnvironmentsManagerClient(auth_header=Authorization) as client:
        return await client.get_collection_variables(collection_id=collection_id)

@tool(tags=['pathfinder', ONBOARDING_IMPLEMENTATION, PUBLIC], meta={'ui_label': 'Creating Pathfinder Project'})
async def create_pathfinder_project(name: str, group: str, domain: str='banking 2.0', Authorization: AuthorizationDep=None, execution_mode: ExecutionModeDep='normal') -> dict:
    """Create a new pathfinder project. 

    Args:
        name: The name of the project. Must contain only letters and underscores.
        group: The OCP group of the project
        domain: The domain of the project. Possible values: 'banking 2.0','energy', 'car retail', 'Telecommunications', 'universal'. Leave the default if unsure.

    Returns:
        dict: The response containing the new project

    Auth note: this Pathfinder call requires a Bearer JWT; PAT-only auth returns 401.
    """
    async with PathfinderClient(auth_header=Authorization) as client:
        return await client.create_project(name=name, group=group, language='en-US', domain=domain, mode='online')

@tool(tags=['pathfinder', ONBOARDING_IMPLEMENTATION, PUBLIC])
async def list_pathfinder_projects(search_term: str | None=None, Authorization: AuthorizationDep=None, execution_mode: ExecutionModeDep='normal') -> dict:
    """List pathfinder projects with optional search filtering. If you find none, you can use the `redirect_to_pathfinder` action to help the user create one.

    Args:
        search_term: Optional search term to filter projects

    Returns:
        dict: The response containing the list of projects

    Auth note: this Pathfinder call requires a Bearer JWT; PAT-only auth returns 401.
    """
    async with PathfinderClient(auth_header=Authorization) as client:
        return await client.list_projects(search_term=search_term)

@tool(tags=['orchestrator', ONBOARDING_IMPLEMENTATION, PUBLIC], meta={'ui_label': 'Testing Application'})
async def talk_to_app(app_id: str, message: str, session_id: str | None=None, timeout_seconds: int=60, Authorization: AuthorizationDep=None, execution_mode: ExecutionModeDep='normal') -> dict:
    """Send a message to a deployed Orchestrator app and return the agent's reply.

    Use this to smoke-test an agent after deployment, or to drive multi-turn
    test conversations while iterating on instructions and knowledge. The app
    must be deployed first via `deploy_orc_app`.

    Multi-turn: omit `session_id` on the first call to start a new session,
    then pass back the returned `session_id` on each subsequent call to
    continue the same conversation. OCP supports session resumption across
    independent WebSocket connections via `session_resume_req`, so the agent
    retains context (history, named entities, slot values) between turns.

    Args:
        app_id: The ID of the deployed Orchestrator app.
        message: The user message to send to the agent.
        session_id: Optional OCP session ID from a previous turn. Omit to
            start a new session.
        timeout_seconds: Maximum seconds to wait for the agent's reply. Capped at 300.

    Returns:
        dict with keys:
            - reply: the agent's text response
            - greeting: the app's opening line on a fresh session, None when resuming
            - session_id: the OCP session ID. Pass this back on the next call
              to continue the conversation.
            - app_id: echoed for convenience
    """
    if timeout_seconds <= 0 or timeout_seconds > 300:
        timeout_seconds = min(max(timeout_seconds, 1), 300)
    async with ChatClient(auth_header=Authorization) as client:
        try:
            result = await client.send_message(app_id=app_id, message=message, session_id=session_id, timeout_seconds=timeout_seconds)
        except ChatError as exc:
            raise ToolError(str(exc)) from exc
        return {'app_id': app_id, 'session_id': result['session_id'], 'greeting': result.get('greeting'), 'reply': result.get('reply')}

@tool(tags=[ONBOARDING_IMPLEMENTATION, PUBLIC])
async def read_guide(name: str | None=None, execution_mode: ExecutionModeDep='normal') -> dict:
    """Return a markdown guide describing a canonical OCP MCP workflow.

    Call this at the start of an agent-build session to get the recommended
    tool sequence for common journeys: building a Concierge app, adding
    knowledge, or testing and improving.

    Args:
        name: One of "index", "build_concierge_app", "add_knowledge",
            "test_and_improve". Omit or pass "index" to list available guides.

    Returns:
        dict with keys:
            - name: the requested guide name
            - content: the markdown body
            - available: list of all guide names
    """
    requested = name or 'index'
    if requested not in _AVAILABLE_GUIDES:
        raise ToolError(f"Unknown guide '{requested}'. Available: {', '.join(_AVAILABLE_GUIDES)}")
    guide_path = _GUIDES_DIR / f'{requested}.md'
    if not guide_path.is_file():
        raise ToolError(f'Guide file missing on disk: {guide_path.name}')
    return {'name': requested, 'content': guide_path.read_text(encoding='utf-8'), 'available': list(_AVAILABLE_GUIDES)}
@tool(tags=['metrics', PUBLIC])
async def list_metrics_tables(Authorization: AuthorizationDep=None, execution_mode: ExecutionModeDep='normal') -> list[str]:
    """List all queryable OCP metrics table names.

    Returns the available metrics tables for the authenticated tenant.
    Call describe_metrics_table next to learn a table's columns before querying.

    Returns:
        list[str]: Table name strings, e.g. ["DIALOGS_METRICS", "AGENT_ASSIST_AGENT_KPIS"].
    """
    async with MetricsClient(auth_header=Authorization) as client:
        return await client.list_tables()


@tool(tags=['metrics', PUBLIC])
async def describe_metrics_table(table_name: str, Authorization: AuthorizationDep=None, execution_mode: ExecutionModeDep='normal') -> dict:
    """Describe the columns of an OCP metrics table with dimension/measure classification.

    Returns each column's name, SQL type, and whether it is a filterable dimension
    (pk=True) or an aggregatable measure (pk=False). Dimensions are usable for
    filters and group-by in query tools; measures are numeric values to aggregate.

    Args:
        table_name: The table identifier, e.g. "DIALOGS_METRICS". Use
            list_metrics_tables to discover available tables.

    Returns:
        dict with keys:
            - table: echoed table name
            - columns: full list of column dicts (name, type, pk)
            - dimensions: columns where pk=True (filterable / group-by keys)
            - measures: columns where pk=False (aggregatable numeric values)

    Raises:
        ToolError: If the table is unknown or has no columns.
    """
    async with MetricsClient(auth_header=Authorization) as client:
        columns = await client.describe_table(table_name)
    if not columns:
        raise ToolError(
            f"No columns found for metrics table '{table_name}'. "
            "Use list_metrics_tables to see available tables."
        )
    dimensions = [c for c in columns if c.get("pk")]
    measures = [c for c in columns if not c.get("pk")]
    return {"table": table_name, "columns": columns, "dimensions": dimensions, "measures": measures}


# --- Metrics query helpers (shared by query_metrics_aggregation / query_metrics_grouped) ---

_METRICS_OPERATORS = {"sum", "avg", "min", "max", "count"}
# Columns that may never be used as a filter/group-by dimension (handled via ocp_group_names).
_EXCLUDED_DIMENSION_COLUMNS = {"OCP_GROUP_NAME", "OCP_ORGANIZATION_ID"}
# Trailing timezone offset (e.g. "+02:00", "-08:00", "Z") that the metrics API rejects.
_TZ_OFFSET_RE = re.compile(r"(Z|[+-]\d{2}:\d{2})$")


def _validate_metrics_operators(measures: list[dict]) -> None:
    """Raise ToolError if any measure carries an operator outside the allowed enum."""
    for m in measures:
        op = m.get("operator")
        if op not in _METRICS_OPERATORS:
            raise ToolError(
                f"Invalid operator '{op}' for measure '{m.get('name')}'. "
                f"Allowed operators: {', '.join(sorted(_METRICS_OPERATORS))}."
            )


def _validate_metrics_time_format(value: str, field: str) -> None:
    """Reject ISO-offset / 'T'-separated time input at the tool boundary.

    The metrics API requires 'yyyy-MM-dd HH:mm:ss' with the timezone passed
    separately; a clear tool-layer error beats a raw API 400.
    """
    if "T" in value or _TZ_OFFSET_RE.search(value):
        raise ToolError(
            f"'{field}' must be formatted 'yyyy-MM-dd HH:mm:ss' (no 'T' separator, "
            "no timezone offset). Pass the timezone via the separate 'timezone' parameter."
        )


def _resolve_metrics_window(start, end):
    """Resolve the query time range, defaulting to the last 24h when omitted.

    Returns (start, end) as 'yyyy-MM-dd HH:mm:ss' strings. Provided values are
    validated for format; omitted values default to now / now-24h.
    """
    now = datetime.now()
    if start is None:
        start = (now - timedelta(hours=24)).strftime("%Y-%m-%d %H:%M:%S")
    else:
        _validate_metrics_time_format(start, "start")
    if end is None:
        end = now.strftime("%Y-%m-%d %H:%M:%S")
    else:
        _validate_metrics_time_format(end, "end")
    return start, end


def _resolve_time_column(time_column, columns):
    """Resolve the TIMESTAMP column to filter the range on.

    Explicit time_column must exist; otherwise auto-detect a single TIMESTAMP
    column. Zero or multiple candidates (with no explicit value) is an error.
    """
    names = {c.get("name") for c in columns}
    if time_column:
        if time_column not in names:
            raise ToolError(
                f"time_column '{time_column}' is not a column of this table. "
                "Use describe_metrics_table to see available columns."
            )
        return time_column
    timestamp_cols = [c["name"] for c in columns if "TIMESTAMP" in str(c.get("type", "")).upper()]
    if len(timestamp_cols) == 1:
        return timestamp_cols[0]
    detail = (
        f"found {len(timestamp_cols)} TIMESTAMP columns ({', '.join(timestamp_cols)})"
        if timestamp_cols
        else "no TIMESTAMP column found"
    )
    raise ToolError(
        f"Could not auto-detect a time_column ({detail}). Pass time_column explicitly. "
        "Use describe_metrics_table to see column types."
    )


def _classify_metrics_columns(columns):
    """Return (pk_names, measure_names) sets from a describe_table result."""
    pk_names = {c["name"] for c in columns if c.get("pk")}
    measure_names = {c["name"] for c in columns if not c.get("pk")}
    return pk_names, measure_names


def _validate_measures(measures, measure_names):
    """Each measure name must be an existing non-pk (measure) column."""
    for m in measures:
        if m.get("name") not in measure_names:
            raise ToolError(
                f"'{m.get('name')}' is not a measure of this table (must be a non-pk column). "
                "Use describe_metrics_table to see available measures."
            )


def _validate_dimension_columns(cols, pk_names, kind):
    """Each filter/group-by column must be a pk dimension and not an excluded column."""
    if not cols:
        return
    for col in cols:
        if col in _EXCLUDED_DIMENSION_COLUMNS or col not in pk_names:
            raise ToolError(
                f"{kind} column '{col}' must be a filterable dimension (a pk column) and "
                f"cannot be one of {' / '.join(sorted(_EXCLUDED_DIMENSION_COLUMNS))}. "
                "Use describe_metrics_table to see available dimensions."
            )


def _build_api_metrics(measures):
    """Build the API metrics array; alias is required and defaults to operator_name."""
    api_metrics = []
    for m in measures:
        name = m["name"]
        op = m["operator"]
        alias = m.get("alias") or f"{op}_{name}"
        api_metrics.append({"name": name, "operator": op, "alias": alias})
    return api_metrics


@tool(tags=['metrics', PUBLIC])
async def query_metrics_aggregation(table: str, measures: list[dict], ocp_group_names: list[str] | None=None, start: str | None=None, end: str | None=None, time_column: str | None=None, filters: list[dict] | None=None, timezone: str='UTC', ocp_organization_id: str | None=None, Authorization: AuthorizationDep=None, execution_mode: ExecutionModeDep='normal') -> dict:
    """Compute overall metric totals for an OCP metrics table, scoped to an OCP group.

    Answers "how many / what is the total/average …" questions. Each measure is
    {name, operator} where operator is one of sum, avg, min, max, count (an optional
    alias may be supplied). When start/end are omitted the range defaults to the last
    24 hours (UTC). Columns are pre-validated against the table schema.

    Args:
        table: Table identifier. Use list_metrics_tables to discover tables.
        measures: List of {"name", "operator"[, "alias"]} dicts. Operators:
            sum/avg/min/max/count. Names must be measure (pk=False) columns.
        ocp_group_names: REQUIRED. OCP group names scoping the query. Use
            list_groups to discover valid groups.
        start, end: Optional range bounds as 'yyyy-MM-dd HH:mm:ss' (no offset).
            Omitted → last 24h. Pass timezone separately.
        time_column: Optional TIMESTAMP column to filter the range on; auto-detected
            when the table has exactly one TIMESTAMP column.
        filters: Optional list of {"column", "values"} on dimension (pk) columns.
        timezone: IANA-style timezone string (default "UTC").
        ocp_organization_id: Optional org-id passthrough.

    Returns:
        dict: { table, version, range:{start,end,timezone}, ocp_group_names,
                results:[{measure, operator, alias, value}] }

    Raises:
        ToolError: missing ocp_group_names (names list_groups); invalid operator;
            non-measure name, non-pk filter column, or unresolved time_column
            (names describe_metrics_table).
    """
    if not ocp_group_names:
        raise ToolError(
            "query_metrics_aggregation requires ocp_group_names. "
            "Use list_groups to discover valid OCP groups."
        )
    _validate_metrics_operators(measures)

    async with MetricsClient(auth_header=Authorization) as client:
        columns = await client.describe_table(table)
        if not columns:
            raise ToolError(
                f"No columns found for metrics table '{table}'. "
                "Use describe_metrics_table to inspect a table or list_metrics_tables to see tables."
            )
        pk_names, measure_names = _classify_metrics_columns(columns)
        _validate_measures(measures, measure_names)
        _validate_dimension_columns([f.get("column") for f in filters] if filters else None, pk_names, "Filter")
        resolved_tc = _resolve_time_column(time_column, columns)
        start, end = _resolve_metrics_window(start, end)
        api_metrics = _build_api_metrics(measures)
        resp = await client.aggregate(
            table,
            metrics=api_metrics,
            start=start,
            end=end,
            time_column=resolved_tc,
            ocp_group_names=ocp_group_names,
            filters=filters,
            timezone=timezone,
            ocp_organization_id=ocp_organization_id,
        )
        version = client.version

    resp_metrics = resp.get("metrics", []) if isinstance(resp, dict) else []
    # The aggregations response keys each metric by its alias with a singular
    # "value" scalar (confirmed against the live API).
    by_alias = {m.get("name"): m.get("value") for m in resp_metrics}
    results = [
        {"measure": am["name"], "operator": am["operator"], "alias": am["alias"], "value": by_alias.get(am["alias"])}
        for am in api_metrics
    ]
    return {
        "table": table,
        "version": version,
        "range": {"start": start, "end": end, "timezone": timezone},
        "ocp_group_names": ocp_group_names,
        "results": results,
    }


@tool(tags=['metrics', PUBLIC])
async def query_metrics_grouped(table: str, measures: list[dict], group_by: list[str], ocp_group_names: list[str] | None=None, percentage: bool=False, start: str | None=None, end: str | None=None, time_column: str | None=None, filters: list[dict] | None=None, timezone: str='UTC', ocp_organization_id: str | None=None, Authorization: AuthorizationDep=None, execution_mode: ExecutionModeDep='normal') -> dict:
    """Break OCP metric totals down per dimension, scoped to an OCP group.

    Answers "… by status / by region / by skill" questions. Same measure and time
    semantics as query_metrics_aggregation (last-24h default, 'yyyy-MM-dd HH:mm:ss'
    format). group_by columns must be dimension (pk) columns. When percentage=True,
    the API computes per-group percentages server-side.

    Args:
        table: Table identifier. Use list_metrics_tables to discover tables.
        measures: List of {"name", "operator"[, "alias"]} dicts (sum/avg/min/max/count).
        group_by: REQUIRED non-empty list of dimension (pk) columns to break down by.
        ocp_group_names: REQUIRED. OCP group names. Use list_groups to discover groups.
        percentage: When True, request server-side percentages for the group-by columns.
        start, end: Optional 'yyyy-MM-dd HH:mm:ss' bounds; omitted → last 24h.
        time_column: Optional TIMESTAMP column; auto-detected when unambiguous.
        filters: Optional list of {"column", "values"} on dimension (pk) columns.
        timezone: IANA-style timezone string (default "UTC").
        ocp_organization_id: Optional org-id passthrough.

    Returns:
        dict: { table, version, range, ocp_group_names, dimensions:[...],
                rows:[{ <dim>: keyvalue, measures:{alias:value}, percentage? }] }

    Raises:
        ToolError: missing ocp_group_names (names list_groups); empty group_by;
            invalid operator; non-measure name; non-pk group-by/filter column or
            unresolved time_column (names describe_metrics_table).
    """
    if not ocp_group_names:
        raise ToolError(
            "query_metrics_grouped requires ocp_group_names. "
            "Use list_groups to discover valid OCP groups."
        )
    if not group_by:
        raise ToolError(
            "query_metrics_grouped requires at least one group_by dimension. "
            "Use describe_metrics_table to see available dimensions."
        )
    _validate_metrics_operators(measures)

    async with MetricsClient(auth_header=Authorization) as client:
        columns = await client.describe_table(table)
        if not columns:
            raise ToolError(
                f"No columns found for metrics table '{table}'. "
                "Use describe_metrics_table to inspect a table or list_metrics_tables to see tables."
            )
        pk_names, measure_names = _classify_metrics_columns(columns)
        _validate_measures(measures, measure_names)
        _validate_dimension_columns(group_by, pk_names, "group_by")
        _validate_dimension_columns([f.get("column") for f in filters] if filters else None, pk_names, "Filter")
        resolved_tc = _resolve_time_column(time_column, columns)
        start, end = _resolve_metrics_window(start, end)
        api_metrics = _build_api_metrics(measures)
        resp = await client.query_grouped(
            table,
            metrics=api_metrics,
            start=start,
            end=end,
            time_column=resolved_tc,
            ocp_group_names=ocp_group_names,
            group_by_columns=group_by,
            percentage=(group_by if percentage else None),
            filters=filters,
            timezone=timezone,
            ocp_organization_id=ocp_organization_id,
        )
        version = client.version

    # Normalize per-dimension rows. Merge by key tuple (NOT positional index) so
    # metrics with sparse/differently-ordered groups[] pair to the correct dimension.
    resp_metrics = resp.get("metrics", []) if isinstance(resp, dict) else []
    rows_by_key = {}
    order = []
    for metric in resp_metrics:
        alias = metric.get("name")
        for g in metric.get("groups", []):
            key = tuple(g.get("key", []))
            if key not in rows_by_key:
                row = {col: key[i] for i, col in enumerate(group_by) if i < len(key)}
                row["measures"] = {}
                rows_by_key[key] = row
                order.append(key)
            rows_by_key[key]["measures"][alias] = g.get("value")
            pct = g.get("percentage")
            if isinstance(pct, dict) and "value" in pct:
                rows_by_key[key]["percentage"] = pct["value"]
    rows = [rows_by_key[k] for k in order]
    return {
        "table": table,
        "version": version,
        "range": {"start": start, "end": end, "timezone": timezone},
        "ocp_group_names": ocp_group_names,
        "dimensions": group_by,
        "rows": rows,
    }


if __name__ == '__main__':
    mcp.run()
