from typing import List
from pydantic import BaseModel, Field


class AgentInput(BaseModel):
    """Model for agent input fields."""
    name: str = Field(..., description="The name of the input field")
    description: str = Field(..., description="Description of the input field")


class QueueInfo(BaseModel):
    """Model for escalation queue information."""
    name: str = Field(..., description="The name of the escalation queue")
    queue_id: int = Field(..., description="The unique identifier of the queue")
    description: str = Field(..., description="Description of what the queue handles")


class AvailableAgent(BaseModel):
    """Model for an available agent entry."""
    name: str = Field(..., description="The name of the agent")
    input: List[AgentInput] = Field(default=[], description="List of input fields for the agent")
    agent_id: str = Field(..., description="The unique identifier of the agent")
    description: str = Field(..., description="Description of the agent's capabilities")

