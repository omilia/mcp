# OCP Co-Pilot Server

The **OCP Co-Pilot Server** is an intelligent assistant server that provides natural language interface capabilities for the **Omilia Cloud Platform (OCP)**. This server implements the Model Context Protocol (MCP) to enable AI agents and Large Language Models (LLMs) to interact with OCP through a rich set of tools and APIs.

## Overview

The OCP Co-Pilot Server serves as a bridge between conversational AI systems and the Omilia Cloud Platform, enabling:

- **Natural Language Operations**: Execute OCP tasks through conversational commands
- **Automated Workflows**: Handle complex multi-step operations across OCP services
- **Context-Aware Assistance**: Provide intelligent responses based on OCP state and user intent
- **Comprehensive Platform Integration**: Access all major OCP components through unified APIs

## Architecture

The server is built around several specialized clients that interact with different OCP services:

- **MiniApps Client**: Manage voice applications and conversational flows
- **Orchestrator Client**: Handle complex dialog orchestration and canvas management
- **Insights Client**: Access analytics, logs, and conversation data
- **Integrations Client**: Manage phone numbers and external integrations  
- **Environments Manager Client**: Handle configuration variables and environment settings

## Available Tools

### MiniApps Management
- **search_miniapps**: Search for voice applications by name or keyword
- **get_miniapp**: Retrieve detailed configuration for a specific voice app
- **set_miniapp_prompt**: Update conversational prompts (welcome, error, reaction messages)

### Dialog Orchestration
- **search_orchestrator_apps**: Find orchestrator applications by keyword
- **get_orchestrator_app**: Retrieve canvas structure (nodes and edges) for dialog flows

### Analytics & Insights
- **search_dialog_logs**: Search conversation logs with advanced filtering (date, app, region, caller)
- **get_dialog_logs**: Fetch complete conversation history for a specific dialog session

### System Configuration
- **search_numbers**: Find and manage phone numbers in the system
- **search_variable_collections**: Locate configuration variable collections
- **get_collection_variables**: Retrieve all variables within a collection

## Installation

### Prerequisites
- **Python 3.10** or newer
- [uv](https://github.com/astral-sh/uv) package manager

### Setup Steps
1. Clone this repository and navigate to the project directory
2. Copy `.env.example` to `.env` and configure your OCP credentials:
   ```bash
   cp .env.example .env
   # Edit .env with your OCP instance details
   ```
3. Test the installation:
   ```bash
   uv run mcp dev src/main.py
   ```
   This opens the MCP development server - click "Connect" to test the tools.

## Configuration

Update your `.env` file with your OCP environment details:

```env
# OCP Host URL (e.g., https://us1-m.ocp.ai, https://eu1-m.ocp.ai)
OCP_HOST=https://your-ocp-instance.ocp.ai

# OCP Authentication Credentials
OCP_USERNAME=your_username
OCP_PASSWORD=your_password
```

## Usage

The OCP Co-Pilot Server can be integrated with various AI systems and applications:

### 1. MCP-Compatible Clients

Use with any MCP-compatible client such as:
- [Claude Desktop](https://www.anthropic.com/claude)
- [Cursor](https://www.cursor.com/)
- [Gemini CLI](https://github.com/google-gemini/gemini-cli)

#### MCP Configuration Example

Add this configuration to your MCP client's config file:

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
        "/path/to/omilia-copilot-server/src/main.py"
      ],
      "env": {
        "PATH": "/usr/local/bin:/usr/bin:/bin"
      }
    }
  }
}
```

### 2. Self-Hosting with MCP Python SDK

For advanced use cases, run your own MCP server using the [official Python MCP SDK](https://github.com/modelcontextprotocol/python-sdk).

## Example Use Cases

### Deployment Management
```
"Deploy the customer service miniapp to production environment"
"Update the welcome message for the support bot application"
```

### Analytics & Monitoring  
```
"Show me all failed conversations from yesterday in the US region"
"Get the dialog logs for session ID abc-123 to debug the issue"
```

### Configuration Management
```
"Find all miniapps that use the billing orchestrator flow"
"Update the error message for when ASR fails to understand input"
```

### Operational Support
```
"Search for phone numbers containing area code 555"
"List all environment variables in the production configuration"
```

## Authentication

The server uses OAuth 2.0 with Keycloak for authentication to OCP services. Authentication is handled automatically through the `Authentication` class, which manages:

- Token acquisition and refresh
- Automatic token validation
- Secure credential handling
- Multi-region support (US, EU)

## Development

### Project Structure
```
src/
├── main.py                 # MCP server entry point
└── ocp/                   # OCP client modules
    ├── base.py            # Base client with authentication
    ├── authentication.py  # OAuth 2.0 authentication handler  
    ├── miniapps.py        # MiniApps API client
    ├── orchestrator.py    # Orchestrator API client
    ├── insights.py        # Analytics API client
    ├── integrations.py    # Integrations API client
    └── environments_manager.py # Environment configuration client
```

### Running Tests
```bash
uv run pytest src/tests/
```

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/new-capability`
3. Make your changes and add tests
4. Commit your changes: `git commit -am 'Add new capability'`  
5. Push to the branch: `git push origin feature/new-capability`
6. Submit a pull request

## Support

For issues and questions:
- Check the [OCP Documentation](https://docs.ocp.ai) for platform-specific guidance
- Review the [MCP Protocol Documentation](https://modelcontextprotocol.info/) for integration help
- Contact your OCP administrator for authentication and access issues

---

*The OCP Co-Pilot Server empowers teams to interact with the Omilia Cloud Platform through natural language, reducing operational overhead and enabling focus on innovation.*
