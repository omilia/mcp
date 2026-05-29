from .base import BaseClient
from utils import get_canvas_with_concierge


class OrchestratorClient(BaseClient):

    async def get_tts_voices(self, organization_id: str) -> list[dict]:
        """
        Get available TTS voices for an organization.

        Args:
            organization_id: The ID of the organization

        Returns:
            list[dict]: List of available voices with language, provider, name, and id
        """
        supported_locales = {"en-US", "es-ES", "fr-FR"}
        endpoint = "orchestrator/api/tts/voices/"
        params = {"organization": organization_id}
        response = await self.get(endpoint, params=params)
        voices = response.get("voices", [])
        return [
            {"language": v["language"], "provider": v["provider"], "name": v["name"], "id": v["id"]}
            for v in voices
            if v["language"] in supported_locales
        ]

    async def change_tts_configuration(
        self,
        app_id: str,
        provider: str,
        rate: str,
        voice: str,
        volume: str,
        organization_id: str,
        language: str = "en-US",
    ) -> dict:
        """
        Change the TTS configuration for an Orchestrator app.
        """

        endpoint = f"orchestrator/api/apps/{app_id}/tts/configuration/"
        payload = {"tts_configuration":[{
            "default": "true",
            "language": language,
            "name": "default",
            "organization": organization_id,
            "provider": provider,
            "rate": rate,
            "voice": voice,
            "volume": volume,
        }]}

        return await self.put(endpoint, json=payload)


    async def search_apps(self, search_term: str | None = None, page_size: int = 30) -> dict:
        """Search Orchestrator apps with optional search term.
        
        Args:
            search_term (str, optional): Search term to filter apps. Case insensitive.
            
        Returns:
            dict: The apps matching the search criteria
        """
        endpoint = "orchestrator/api/apps/pagination/"
        params = {"limit": page_size}
        if search_term:
            params['search_term'] = search_term
            
        return await self.get(endpoint, params=params)

    async def get_canvas(self, canvas_id: str) -> dict:
        """Get a canvas by ID.
        
        Args:
            canvas_id: The ID of the canvas to get
        """
        endpoint = f"orchestrator/api/canvases/{canvas_id}/"
        return await self.get(endpoint)

    async def get_app(self, app_id: str) -> dict:
        """Get an app by ID.
        
        Args:
            app_id: The ID of the app to get
        """
        endpoint = f"orchestrator/api/apps/{app_id}/"
        return await self.get(endpoint)

    async def get_chat_info_for_app(self, app_id: str) -> dict:
        """Get chat info for an Orchestrator app.
        
        Args:
            app_id: The ID of the app to get chat info for
            
        Returns:
            dict: Chat info containing chat_url, deployed_token, and live_token
        """
        endpoint = f"orchestrator/api/apps/{app_id}/web_chat/"
        return await self.get(endpoint)

    async def create_app(self, group: str, name: str) -> dict:
        """Create a new Orchestrator app.
        
        Args:
            group: The group for the app
            name: The name of the app
            
        Returns:
            dict: The created app data
        """
        endpoint = "orchestrator/api/apps/"
        data = {
            "group": group,
            "name": name,
            "application_type": "agentic",
        }
        return await self.post(endpoint, json=data)

    async def create_agent(self, group: str, name: str, agent_type: str = "concierge") -> dict:
        """Create a new agent.
        
        Args:
            group: The group for the agent
            name: The name of the agent
            agent_type: The type of the new agent. Possible values: 'concierge', 'task'. Default is 'concierge'.
            
        Returns:
            dict: The created agent data
        """
        endpoint = "orchestrator/api/agents/"
        data = {
            "name": name,
            "description": "",
            "labels": [],
            "input_fields": [],
            "output_fields": [],
            "group": group,
            "type": agent_type,
        }
        return await self.post(endpoint, json=data)

    async def create_flow(self, name: str, group: str, input_fields: list[str] = None) -> dict:
        """Create a new flow."""
        if input_fields is None:
            input_fields = []
            
        endpoint = "orchestrator/api/flows/"
        data = {
            "name": name,
            "input_fields": input_fields,
            "output_fields": [],
            "group": group,
            "description": "",
            "labels": [],
            "reportable": False,
            "schema_version": 1
        }
        resp = await self.post(endpoint, json=data)
        return resp

    async def get_agent(self, agent_id: str) -> dict:
        """
        Get an agent by ID.
        """
        endpoint = f"orchestrator/api/agents/{agent_id}/"
        return await self.get(endpoint)

    async def get_agent_from_any_id(self, agent_id_or_component_id: str) -> dict:
        """
        Get an agent by ID or component_id.

        Args:
            agent_id_or_component_id: Either an agent ID or a component_id in format "uuid.name.type.orc.group"

        Returns:
            The agent object
        """
        parts = agent_id_or_component_id.split(".")
        if len(parts) >= 5:
            agent_name = parts[1]
            group = parts[4]
            agents = await self.list_agents(group=group)
            for agent in agents:
                if agent.get("name") == agent_name:
                    return await self.get_agent(agent.get("id"))
            raise ValueError(
                f"No agent found with name '{agent_name}' in group '{group}'"
            )
        return await self.get_agent(agent_id_or_component_id)

    async def list_agents(self, group: str | None = None) -> list[dict]:
        """
        List all agents.
        """
        search_text = f"?group__iexact={group}" if group else ""
        endpoint = f"orchestrator/api/agents/{search_text}"
        return await self.get(endpoint)

    async def list_groups(self) -> list[str]:
        """Return sorted unique groups derived from accessible agents and apps."""
        groups: set[str] = set()
        agents = await self.list_agents()
        for agent in agents:
            if g := agent.get("group"):
                groups.add(g)
        apps_resp = await self.search_apps(page_size=100)
        apps = apps_resp.get("results", []) if isinstance(apps_resp, dict) else apps_resp
        for app in apps:
            if g := app.get("group"):
                groups.add(g)
        return sorted(groups)

    async def list_flows(self, group: str | None = None) -> list[dict]:
        """
        List all flows.
        """
        search_text = f"?group__iexact={group}" if group else ""
        endpoint = f"orchestrator/api/flows/{search_text}"
        return await self.get(endpoint)

    async def get_flow(self, flow_id: str) -> dict:
        """
        Get a flow by ID.
        """
        endpoint = f"orchestrator/api/flows/{flow_id}/"
        return await self.get(endpoint)

    async def update_agent(
        self, 
        agent_id: str, 
        instructions: list[str] | None = None, 
        tools: list[dict[str]] | None = None,
        agents:list[dict[str]] | None = None,
        escalate_to_human: list[dict[str]] | None = None
    ) -> dict:
        """
        Update an agent.
        """
        endpoint = f"orchestrator/api/agents/{agent_id}/"
        agent_data = await self.get_agent(agent_id)
        agent_data = self._agent_update_instructions(agent_data, instructions)
        agent_data = self._agent_add_tools(agent_data, tools)
        agent_data = self._agent_add_agents(agent_data, agents)
        agent_data = self._agent_add_escalation_queues(agent_data, escalate_to_human)
        return await self.put(endpoint, json=agent_data)

    async def update_canvas(self, canvas_id: str, data: dict) -> dict:
        """
        Update a canvas.
        """
        endpoint = f"orchestrator/api/canvases/{canvas_id}/"
        return await self.put(endpoint, json=data)

    async def get_agent_group(self, agent_id: str) -> str:
        """
        Get the group of an agent by ID.
        """
        agent = await self.get_agent(agent_id)
        return agent.get("group")

    def _agent_update_instructions(
        self,
        agent_data: dict,
        instructions: list[str] | None,
    ) -> dict:
        """
        Set the agent instructions.
        """
        if instructions is not None:
            agent_data["instructions"] = instructions
        return agent_data

    def _agent_add_tools(
        self,
        agent_data: dict,
        tools: list[dict[str]] | None,
    ) -> dict:
        """
        Set the agent tools.
        """
        if tools is not None:
            agent_data["components"]["tools"] = tools
        return agent_data

    def _agent_add_agents(
        self,
        agent_data: dict,
        agents: list[dict[str]] | None,
    ) -> dict:
        """
        Set the nested agents for the agent.
        """
        if agents is not None:
            agent_data["components"]["agents"] = agents
        return agent_data

    def _agent_add_escalation_queues(
        self,
        agent_data: dict,
        escalate_to_human: list[dict[str]] | None,
    ) -> dict:
        """
        Set the escalation queues for the agent.
        """
        if escalate_to_human is not None:
            agent_data["components"]["escalate_to_human"] = escalate_to_human
        return agent_data

    async def _update_canvas_with_concierge(self, canvas_id: str, agent_component_id: str) -> dict:
        """
        Update a canvas with a concierge agent.
        """
        endpoint = f"orchestrator/api/canvases/{canvas_id}/"
        data = get_canvas_with_concierge(agent_component_id, canvas_id)
        return await self.put(endpoint, json=data)

    async def _deploy_app(self, app_id: str) -> dict:
        """
        Deploy an app.
        """
        endpoint = f"orchestrator/api/apps/{app_id}/deploy/"
        return await self.post(endpoint)