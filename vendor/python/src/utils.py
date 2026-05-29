from fastmcp.exceptions import ToolError


WS_RESPONSE_BODY = {"wsResponseBody": {"type": "path", "value": "wsResponseBody"}}


def get_intent_announce_list(vectorStoreId: str) -> list[dict]:
    """
    Return the content to be injected to an Intent miniApp in order to configure a knowledge base.
    It should go under the "announceList" top level key.
    """
    return [
        {
            "order": 0,
            "md5": "f964dbdc997df60d196dfe5285ca0586",
            "enabled": True,
            "postAction": {"type": "exit", "reask": 0, "transferNumber": ""},
            "fieldValuePairs": [
                {"field": "Intent", "path": "", "operator": "", "values": ["*"]}
            ],
            "announcement": {
                "locales": {
                    "en-US": {
                        "vectorStoreId": vectorStoreId,
                        "promptType": "KnowledgeBase",
                        "llmInstructions": "",
                        "omIVR": {"normal": "", "error": "", "unrecovered": ""},
                        "web-chat": {
                            "normal": "",
                            "error": "",
                            "unrecovered": "",
                            "dataModelsLink": [],
                        },
                    }
                },
                "bargeIn": {"normal": False, "error": False, "unrecovered": False},
                "replay": {"normal": "true"},
            },
        }
    ]


def get_announcement_announce_list(announcement: str) -> list[dict]:
    return [
        {
            "order": 0,
            "md5": "bf16097c7c67218fe6564eb9d9badc3b",
            "enabled": True,
            "fieldValuePairs": [],
            "postAction": {"type": "exit", "reask": 0, "transferNumber": ""},
            "announcement": {
                "locales": {
                    "en-US": {
                        "omIVR": {
                            "normal": announcement,
                            "error": "",
                            "unrecovered": "",
                        },
                        "vectorStoreId": "",
                        "promptType": "Text",
                        "llmInstructions": "",
                        "web-chat": {
                            "normal": "",
                            "error": "",
                            "unrecovered": "",
                            "dataModelsLink": [],
                        },
                    }
                },
                "bargeIn": {"normal": False, "error": False, "unrecovered": False},
                "replay": {"normal": "true"},
            },
        }
    ]


def get_canvas_with_concierge(agent_component_id: str, canvas_id: str) -> dict:
    node_title = agent_component_id.split(".")[1]
    return {
        "content": {
            "nodes": [
                {
                    "title": node_title,
                    "node_id": "e579330e-0094-4456-8e9e-295841322d30",
                    "component_id": agent_component_id,
                    "configuration": {
                        "output_fields": [],
                        "reset_on_intent": False,
                        "input_fields": {},
                        "referents": [],
                        "log_as_kvp": {"input_fields": [], "output_fields": []},
                    },
                    "x_value": 542.0,
                    "y_value": 216.0,
                    "type": "Flow",
                }
            ],
            "edges": [],
        },
        "name": canvas_id,
    }


def get_faq_flow_initial_contents() -> dict:
    return {
        "content": {
            "nodes": [
                {
                    "title": "Set Field",
                    "type": "set-field",
                    "node_id": "3b2febc3-d8d0-4461-9f33-a396b0eb2829",
                    "component_id": "user-id.set-field.builtins.orc.group",
                    "x_value": 350,
                    "y_value": 150,
                    "configuration": {
                        "output_fields": [],
                        "reset_on_intent": False,
                        "input_fields": {},
                        "extra_fields": [
                            {"field": "status", "value": "started", "operator": "EQUAL"}
                        ],
                        "referents": [],
                        "log_as_kvp": {"input_fields": [], "output_fields": []},
                    },
                },
                {
                    "title": "Condition",
                    "type": "condition",
                    "node_id": "4f5513a8-f416-46ba-911b-6f35432a7c27",
                    "component_id": "user_id.condition.builtins.orc.my_group",
                    "x_value": 350,
                    "y_value": 310,
                    "configuration": {
                        "reset_on_intent": False,
                        "input_fields": {},
                        "output_fields": [],
                        "extra_fields": [],
                    },
                },
            ],
            "edges": [
                {
                    "id": "3b86d2f6-9373-4aa3-8819-5cf96a26aed9",
                    "port": "out",
                    "source": "3b2febc3-d8d0-4461-9f33-a396b0eb2829",
                    "target": "4f5513a8-f416-46ba-911b-6f35432a7c27",
                    "conditions": [],
                }
            ],
        },
    }


def calculate_announcement_node_position(
    condition_node: dict, nodes: list, edges: list
) -> tuple[float, float]:
    """
    Calculate the optimal x,y position for a new announcement node to maintain symmetric layout.

    Args:
        condition_node: The condition node to connect to
        nodes: List of all nodes in the canvas
        edges: List of all edges in the canvas

    Returns:
        Tuple of (x_value, y_value) for the new announcement node
    """
    condition_node_id = condition_node["node_id"]
    condition_x = condition_node["x_value"]
    condition_y = condition_node["y_value"]

    # Nodes connected to the condition node
    connected_node_ids = set()

    # Edges where condition node is source
    for edge in edges:
        if edge["source"] == condition_node_id:
            connected_node_ids.add(edge["target"])

    # Get x coordinates of connected nodes
    connected_x_values = []
    for node in nodes:
        if node["node_id"] in connected_node_ids:
            connected_x_values.append(node["x_value"])

    announcement_x = condition_x  # Default to same x as condition

    if connected_x_values:
        connected_x_values.sort()
        leftmost_x = connected_x_values[0]
        rightmost_x = connected_x_values[-1]

        # Calculate distances from condition node
        left_distance = condition_x - leftmost_x
        right_distance = rightmost_x - condition_x

        # Choose position that maintains better symmetry
        if left_distance <= right_distance:
            announcement_x = rightmost_x + 200
        else:
            announcement_x = leftmost_x - 200

    announcement_y = condition_y + 200

    return announcement_x, announcement_y


def validate_available_locales(miniapp_json_part: dict, locale: str) -> None:
    """
    Validate that the locale is available in the miniapp json part.
        Raises a ToolError if the locale is not found.
    """

    if locale not in miniapp_json_part:
        raise ToolError(
            f"Locale not found. Available locales: {miniapp_json_part.keys()}"
        )


class GroupAccessError(ToolError):
    """
    Common error to be raised when trying to modify a resource in a group that the user has disallowed access to.
    """
    def __init__(self, group: str):
        super().__init__(
            f"Access denied: the user has disallowed access to the group {group}. They need to update their access settings to use this resource."
        )

class NameMustBeUniqueError(ToolError):
    """
    Common error to be raised when trying to create a miniapp with a name that already exists.
    """
    def __init__(self, name: str):
        super().__init__(
            f"You can not create a miniapp with a name that already exists. The name {name} is already in use. Please use a different name."
        )
