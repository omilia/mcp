# OCP Co-Pilot MCP Server

A **Model Context Protocol (MCP)** server that provides intelligent access to the **Omilia Cloud Platform (OCP)** through AI assistants. This server enables natural language interactions with OCP's conversational AI platform, allowing developers and operators to manage voice applications, analyze dialog logs, and configure environments through AI-powered tools.

## About Omilia Cloud Platform

The **Omilia Cloud Platform (OCP)** is a comprehensive conversational AI platform that powers voice applications, contact centers, and automated customer interactions. It provides:

- **Voice Applications**: Intelligent voice apps with natural language understanding
- **Dialog Management**: Complex conversation flows and orchestration  
- **Analytics & Insights**: Real-time monitoring and conversation analytics
- **Multi-channel Support**: Voice, chat, and omnichannel experiences

## Features

This MCP server provides AI assistants with the ability to:

### 🎯 **MiniApps Management**
- Search and retrieve voice applications by name or keyword
- Update conversation prompts (welcome, error, reaction messages)
- Configure application settings and behaviors

### 🔧 **Dialog Orchestration** 
- Search and analyze Orchestrator applications
- Retrieve conversation flow canvases (nodes and edges)
- Understand complex dialog routing logic

### 📊 **Insights & Analytics**
- Search dialog logs with advanced filtering (date, app, region, caller)
- Retrieve detailed conversation histories 
- Analyze application performance and user interactions

### 📱 **Platform Integration**
- Manage phone number configurations
- Handle variable collections for environment management
- Configure multi-tenant deployments

### 🔐 **Secure Authentication**
- OAuth2/OpenID Connect integration with Keycloak
- Automatic token refresh and session management
- Multi-region API endpoint support

## Available Tools

The server exposes the following tools to AI assistants:

| Tool | Description |
|------|-------------|
| `search_miniapps` | Search voice applications by name or keyword |
| `get_miniapp` | Retrieve detailed information about a specific voice app |
| `set_miniapp_prompt` | Update conversation prompts and messages |
| `search_orchestrator_apps` | Find Orchestrator dialog flow applications |
| `get_orchestrator_app` | Get the complete dialog flow canvas (nodes/edges) |
| `search_dialog_logs` | Search conversation logs with advanced filters |
| `get_dialog_logs` | Retrieve detailed logs for a specific conversation |
| `search_numbers` | Find and manage phone number configurations |
| `search_variable_collections` | Search environment variable collections |
| `get_collection_variables` | List variables in a specific collection |

## Installation

### Prerequisites

- **Python 3.10** or newer
- [uv](https://github.com/astral-sh/uv) package manager
- Access to an Omilia Cloud Platform instance

### Setup

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd omilia-copilot-server
   ```

2. **Configure environment:**
   ```bash
   cp .env.example .env
   ```
   
   Edit `.env` with your OCP instance details:
   ```env
   OCP_HOST=https://your-instance.ocp.ai
   OCP_USERNAME=your-username
   OCP_PASSWORD=your-password
   ```

3. **Test the installation:**
   ```bash
   uv run mcp dev src/main.py
   ```
   
   This opens the MCP development server. Click "Connect" to test the tools.

## Usage

### MCP-Compatible AI Assistants

This server works with any MCP-compatible AI assistant:

- **[Claude Desktop](https://www.anthropic.com/claude)** - Anthropic's desktop AI assistant
- **[Cursor](https://www.cursor.com/)** - AI-powered code editor  
- **[Gemini CLI](https://github.com/google-gemini/gemini-cli)** - Google's command-line AI tool

### Configuration

Add this server to your MCP client configuration. For most clients, create or update `mcp.json`:

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

### Example Interactions

Once configured, you can interact with OCP through natural language:

**Voice App Management:**
> "Show me all miniapps with 'customer' in the name"
> 
> "Update the welcome prompt for app ABC123 to say 'Welcome to customer service'"

**Analytics & Monitoring:**  
> "Find dialog logs for app XYZ789 from yesterday with more than 5 conversation steps"
>
> "Show me the conversation history for dialog ID 12345"

**Flow Analysis:**
> "Get the canvas for orchestrator app 'Customer Journey' and explain the flow"

## Development

### Project Structure

```
src/
├── main.py                 # MCP server entry point
└── ocp/                   # OCP client modules
    ├── authentication.py  # OAuth2/OIDC authentication
    ├── base.py           # Base HTTP client with auth
    ├── miniapps.py       # Voice applications client
    ├── orchestrator.py   # Dialog flow client
    ├── insights.py       # Analytics and logs client
    ├── integrations.py   # Phone numbers client
    └── environments_manager.py  # Variables client
```

### Running Tests

```bash
uv run pytest src/tests/
```

### Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality  
5. Submit a pull request

## Architecture

The server follows a modular architecture:

- **MCP Server**: FastMCP framework handles tool registration and protocol
- **Authentication**: Centralized OAuth2 token management with auto-refresh
- **Client Modules**: Specialized clients for each OCP service area
- **Base Client**: Shared HTTP client with authentication headers

## API Coverage

This server provides access to key OCP APIs:

- **MiniApps API**: Voice application management
- **Orchestrator API**: Dialog flow configuration  
- **Dialogs API**: Conversation analytics and logs
- **Integrations API**: Channel and number management
- **Environment Manager API**: Configuration variables

## Security

- Uses OAuth2/OpenID Connect for secure API access
- Supports token refresh to maintain long-running sessions
- Environment variable configuration keeps credentials secure
- Region-specific endpoint routing for compliance

## Support

For issues related to:
- **OCP Platform**: Contact Omilia support
- **MCP Server**: Create an issue in this repository
- **AI Assistant Integration**: Consult your AI assistant's MCP documentation

---

**Transform how your team interacts with OCP through the power of AI-assisted platform management.**