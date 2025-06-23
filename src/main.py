import random

from mcp.server.fastmcp import FastMCP

from ocp.insights import InsightsClient
from ocp.miniapps import MiniAppsClient

mcp = FastMCP("OCP")


@mcp.tool()
def search_miniapps(search_term: str | None = None) -> list[str]:
    """Search miniapps. Useful to return a list of miniapps that match a search term.
    Args:
        search_term: Optional search term to filter miniapps
    """
    client = MiniAppsClient()
    apps = client.get_apps(search_term=search_term)
    return apps

@mcp.tool()
def get_miniapp(miniapp_id: str) -> dict:
    """Get a specific miniapp by its ID. Useful to return various information about a miniapp.
    
    Args:
        miniapp_id: The ID of the miniapp to retrieve
        
    Returns:
        The miniapp data as a dictionary
    """
    client = MiniAppsClient()
    return client.get_miniapp(miniapp_id)


@mcp.tool()
def set_miniapp_prompt(miniapp_id: str, prompt_type: str, prompt: str) -> dict:
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
    """
    client = MiniAppsClient()
    miniapp_json = client.get_miniapp(miniapp_id)

    # Handle welcome/initial prompts
    if prompt_type == "welcome":
        miniapp_json["model"]["welcome"]["locales"]["en-US"]["omIVR"]["normal"] = prompt
        return client.update_miniapp(miniapp_id, miniapp_json)
    elif prompt_type == "initial":
        miniapp_json["model"]["ask"]["locales"]["en-US"]["omIVR"]["normal"] = prompt
        return client.update_miniapp(miniapp_id, miniapp_json)

    # Handle error prompts
    error_type_map = {
        "error_no_interpretation": "noInterpretation",
        "error_no_response": "noResponse",
        "error_global_errors": "globalErrors",
        "error_agent_request": "agentRequest",
        "error_critical_error": "criticalError",
        "error_max_disconfirmations": "maxDisconfirmations",
        "error_max_wrong_inputs": "maxWrongInputs",
        "error_max_dtmf_inputs": "maxDtmfInputs"
    }

    if prompt_type in error_type_map:
        error_path = error_type_map[prompt_type]
        miniapp_json["model"]["errors"]["targetAction"][error_path]["locales"]["en-US"]["omIVR"]["normal"] = prompt
        return client.update_miniapp(miniapp_id, miniapp_json)

    # Handle reaction prompts
    reaction_type_map = {
        "reaction_greeting": "greetingReactionPrompts",
        "reaction_no_match": "noMatchReactionPrompts",
        "reaction_same_state": "sameStateReactionPrompts",
        "reaction_nice_response": "niceResponseReactionPrompts"
    }

    if prompt_type in reaction_type_map:
        reaction_path = reaction_type_map[prompt_type]
        miniapp_json["model"]["reactions"][reaction_path]["locales"]["en-US"]["omIVR"]["normal"] = prompt
        return client.update_miniapp(miniapp_id, miniapp_json)

    valid_types = (["welcome", "initial"] + 
                  list(error_type_map.keys()) + 
                  list(reaction_type_map.keys()))
    raise ValueError(f"Invalid prompt_type. Must be one of: {', '.join(valid_types)}")



@mcp.tool()
def get_dialog_logs(dialog_id: str) -> str:
    """Get the dialog logs for a specific dialog ID. Useful for retrieving conversation history and analytics.
    
    Args:
        dialog_id: The ID of the dialog to retrieve logs for
        
    Returns:
        The dialog log data as a dictionary
    """
    client = InsightsClient()
    return client.get_dialog_log(dialog_id)


    
# Add a dynamic greeting resource
@mcp.resource("greeting://{name}")
def get_greeting(name: str) -> str:
    """Get a personalized greeting"""
    return f"Hello, {name}!"


# run with $env:DANGEROUSLY_OMIT_AUTH="true"; uv run mcp dev src/main.py
