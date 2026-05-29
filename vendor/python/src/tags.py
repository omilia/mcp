"""
Constants for tool tagging and filtering.

These tags are used to filter which tools are available to specific agents.
See TOOL_TAGGING.md for documentation.
"""

# Agent-specific tool tags
NLU_AGENT = "nlu_specialist"
AUTOMATION_LVL_1 = "automation_lvl_1"
AUTOMATION_LVL_1_DETERMINISTIC = "automation_lvl_1_deterministic"
AUTOMATION_LVL_4 = "automation_lvl_4"
EXPLAIN_FLOW = "explain_flow"
DEPRECATED = "deprecated"

# Tag for tools requiring approval via Human-in-the-Loop
APPROVAL = "requires_approval"

# Tag for tools that support group filtering
GROUP_FILTER = "group_filter"

# Tag for tools in the implementation step of the onboarding process.
ONBOARDING_IMPLEMENTATION = "onboarding_implementation"

# Tag for tools that opt into the public GitHub mirror.
PUBLIC = "public"
