# OCP Co-Pilot MCP Server

The **OCP Co-Pilot** is an intelligent assistant designed to augment the **Omilia Cloud Platform (OCP)** by leveraging **Large Language Models (LLMs)** and **AI Agents**. This repository contains the Model Context Protocol (MCP) server that provides the foundational tools for interacting with OCP through natural language interfaces.

## Overview

The Co-Pilot streamlines interactions with OCP by automating complex tasks, guiding users through workflows, and enabling natural language control over platform operations. With the Co-Pilot, developers, operators, and business teams can interact with the platform conversationally, reducing friction and improving efficiency across development, deployment, and monitoring activities.

This MCP server provides a comprehensive set of tools for:
- **MiniApps Management**: Search, retrieve, and configure voice applications
- **Orchestrator Integration**: Access and manage dialog flow applications  
- **Dialog Analytics**: Retrieve and analyze conversation logs and insights
- **Environment Management**: Handle variable collections and phone number configurations
- **Authentication**: Secure token-based authentication with OCP services

## Key Features

* **Natural Language Interface**: Execute OCP actions and queries using plain language commands through MCP-compatible clients
* **Task Automation**: Handle repetitive and routine tasks (deployments, monitoring, configuration updates) through AI-driven automation
* **Context-Aware Assistance**: Understands OCP-specific terminology, system state, and user intent
* **Comprehensive API Coverage**: Access to miniapps, orchestrator, insights, integrations, and environment management
* **Secure Authentication**: OAuth2-based authentication with token refresh capabilities

## Available Tools

### MiniApps Management
- **search_miniapps**: Search for miniapps by name or keyword
- **get_miniapp**: Retrieve detailed information for a specific miniapp
- **set_miniapp_prompt**: Update various prompts (welcome, error, reaction messages) for miniapps

### Dialog Analytics & Insights  
- **get_dialog_logs**: Fetch detailed logs for specific dialog sessions
- **search_dialog_logs**: Search dialog logs with filters (date, app, region, caller info, etc.)

### Orchestrator Applications
- **search_orchestrator_apps**: Search for Orchestrator applications by keyword
- **get_orchestrator_app**: Retrieve the complete canvas (nodes and edges) for dialog flows

### Environment & Integration Management
- **search_numbers**: Search for configured phone numbers
- **search_variable_collections**: Find variable collections by search term  
- **get_collection_variables**: List all variables in a specific collection

## Example Use Cases

* **Deployment Automation**: "Deploy the latest version of the customer service app to staging."
* **Monitoring & Alerts**: "Check the health of all voice AI services and alert me if latency exceeds threshold."
* **Configuration Management**: "Update the ASR model configuration to use the new speech dataset."
* **Knowledge Support**: "Explain how to set up a new tenant in OCP."
* **Dialog Analysis**: "Show me all failed conversations from last week for the billing application."

## Technical Architecture

The MCP server is built using:
- **FastMCP**: High-performance MCP server framework
- **Modular Client Architecture**: Separate clients for each OCP service (MiniApps, Insights, Orchestrator, etc.)
- **OAuth2 Authentication**: Secure token management with automatic refresh
- **RESTful API Integration**: Direct integration with OCP's REST APIs

### Project Structure
```
src/
├── main.py                    # MCP server entry point with tool definitions
└── ocp/
    ├── base.py               # Base HTTP client with authentication
    ├── authentication.py     # OAuth2 token management
    ├── miniapps.py          # MiniApps service client
    ├── insights.py          # Dialog analytics client  
    ├── orchestrator.py      # Orchestrator service client
    ├── integrations.py      # Phone numbers and integrations
    └── environments_manager.py # Environment variables client
```

## Installation

### Prerequisites
- **Python 3.10** or newer
- [uv](https://github.com/astral-sh/uv) package manager

### Setup
1. Clone this repository and navigate to the project directory
2. Create a `.env` file with your OCP credentials:
   ```env
   OCP_HOST=https://your-ocp-instance.com
   OCP_USERNAME=your-username
   OCP_PASSWORD=your-password
   ```
3. Test the installation:
   ```bash
   uv run mcp dev src/main.py
   ```
   This opens the MCP development server. Click "Connect" to test the tools.

## Usage

### MCP Client Integration

You can use this server with any MCP-compatible client:

- [Claude Desktop](https://www.anthropic.com/claude)
- [Cursor](https://www.cursor.com/)  
- [Gemini CLI](https://github.com/google-gemini/gemini-cli)

#### Example MCP Configuration

Add this to your MCP client configuration (e.g., `mcp.json`):

```json
{
  "mcpServers": {
    "OCP Co-Pilot": {
      "command": "uv",
      "args": [
        "run",
        "--with",
        "mcp",
        "mcp", 
        "run",
        "/path/to/ocp-copilot/src/main.py"
      ],
      "env": {
        "PATH": "/your/system/path"
      }
    }
  }
}
```

### Development

For development and testing:
```bash
# Install development dependencies
uv sync --dev

# Run tests
uv run pytest

# Start development server
uv run mcp dev src/main.py
```

## Authentication & Security

The server uses OAuth2 password grant flow to authenticate with OCP:
- Automatic token acquisition and refresh
- Secure token storage in memory
- Graceful error handling for authentication failures

Environment variables required:
- `OCP_HOST`: Your OCP instance URL
- `OCP_USERNAME`: Your OCP username
- `OCP_PASSWORD`: Your OCP password

## Vision

The OCP Co-Pilot is more than just an assistant—it's a **collaborative partner** that transforms how teams interact with OCP. By combining natural language understanding with robust automation through the MCP protocol, it empowers teams to focus on innovation while reducing operational overhead.

This MCP server serves as the foundation for building sophisticated AI agents that can understand context, execute complex workflows, and provide intelligent assistance across the entire OCP ecosystem.

## Contributing

This project is part of the broader OCP Co-Pilot initiative. For development guidelines and contribution information, please refer to the project documentation.

---

*Built with ❤️ for the Omilia Cloud Platform ecosystem*