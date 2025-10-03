# OCP Co-Pilot Server

The **OCP Co-Pilot** is an intelligent assistant designed to augment the **Omilia Cloud Platform (OCP)** by leveraging **Large Language Models (LLMs)** and **AI Agents**. It streamlines interactions with OCP, automating complex tasks, guiding users through workflows, and enabling natural language control over platform operations.

With OCP Co-Pilot, developers, operators, and business teams can interact with the platform conversationally, reducing friction and improving efficiency across development, deployment, and monitoring activities.

## 🚀 Key Features

* **Natural Language Interface**: Execute OCP actions and queries using plain language commands.
* **Task Automation**: Handle repetitive and routine tasks (e.g., deployments, monitoring, configuration updates) through AI-driven automation.
* **Context-Aware Assistance**: Understands user intent, OCP-specific terminology, and system state to provide relevant responses.
* **Agentic Workflows**: Uses LLM-powered agents to plan, decompose, and execute multi-step tasks in OCP.
* **Guided Operations**: Provides step-by-step support for complex processes such as environment setup, scaling, or troubleshooting.
* **Extensibility**: Designed to plug into custom OCP APIs and services, allowing teams to extend capabilities easily.

## 💡 Example Use Cases

* **Deployment Automation**: "Deploy the latest version of the customer service app to staging."
* **Monitoring & Alerts**: "Check the health of all voice AI services and alert me if latency exceeds threshold."
* **Configuration Management**: "Update the ASR model configuration to use the new speech dataset."
* **Knowledge Support**: "Explain how to set up a new tenant in OCP."
* **Dialog Analysis**: "Show me all failed conversations from yesterday for the customer support app."
* **System Troubleshooting**: "Find all dialog logs with errors in the past 24 hours."

## 🛠️ Available Tools

The Co-Pilot server provides a comprehensive set of tools for OCP management:

### MiniApps Management
- **search_miniapps**: Search for miniapps by name or keyword
- **get_miniapp**: Retrieve details for a specific miniapp using its ID
- **set_miniapp_prompt**: Update prompts (welcome, error, reaction messages) for a miniapp

### Orchestrator Apps
- **search_orchestrator_apps**: Search for Orchestrator apps by keyword
- **get_orchestrator_app**: Retrieve the canvas (nodes and edges) for an Orchestrator app by ID

### Analytics & Insights
- **get_dialog_logs**: Fetch logs for a specific dialog session
- **search_dialog_logs**: Search dialog logs with various filters (date, app, region, etc.)

### System Integration
- **search_numbers**: Search for phone numbers with optional search term
- **search_variable_collections**: Search variable collections with optional search term  
- **get_collection_variables**: Get a list of all variables in a collection by ID

---

## 📦 Installation

### Prerequisites
- **Python 3.10** or newer
- [uv](https://github.com/astral-sh/uv) for dependency management

### Setup Steps

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd ocp-copilot-server
   ```

2. **Install dependencies**:
   ```bash
   uv sync
   ```

3. **Environment Configuration**:
   Create a `.env` file in the project root with your OCP credentials:
   ```env
   OCP_HOST=https://your-ocp-instance.com
   OCP_USERNAME=your_username
   OCP_PASSWORD=your_password
   ```

4. **Verify Installation**:
   Test the installation by running the MCP development server:
   ```bash
   uv run mcp dev src/main.py
   ```
   This opens the MCP development server interface. Click "Connect" to test the tools.

## 🏗️ Architecture

The OCP Co-Pilot Server is built using the [Model Context Protocol (MCP)](https://modelcontextprotocol.info/), which enables seamless integration with AI assistants and LLM applications. The server exposes OCP functionality through a standardized protocol that can be consumed by various AI clients.

### Key Components

- **MCP Server**: FastMCP-based server that exposes OCP tools
- **Authentication Layer**: OAuth2/OpenID Connect integration with OCP
- **Client Modules**: Specialized clients for different OCP services:
  - **MiniAppsClient**: Manages voice applications and prompts
  - **OrchestratorClient**: Handles complex dialog flows and canvases
  - **InsightsClient**: Provides analytics and dialog log access
  - **IntegrationsClient**: Manages phone numbers and external integrations
  - **EnvironmentsManagerClient**: Handles variable collections and configurations

### How It Works

1. **AI Client** (Cursor, Claude Desktop, etc.) connects to the MCP server
2. **User** issues natural language commands like "Show me failed dialogs from yesterday"
3. **MCP Server** translates the request into appropriate OCP API calls
4. **OCP APIs** return data which is processed and presented to the user

This architecture enables the **Co-Pilot vision** by providing a conversational interface to OCP's complex functionality.

## 🚀 Usage

The OCP Co-Pilot Server can be integrated with various AI clients through the Model Context Protocol (MCP). Here are the main usage patterns:

### 1. With AI Clients (Recommended)

Connect the server to MCP-compatible AI clients for natural language interaction:

#### Claude Desktop
Add this configuration to your Claude Desktop MCP settings:
```json
{
  "mcpServers": {
    "OCP Co-Pilot": {
      "command": "uv",
      "args": [
        "run",
        "mcp",
        "run",
        "/path/to/ocp-copilot-server/src/main.py"
      ],
      "env": {
        "PATH": "/usr/local/bin:/usr/bin:/bin"
      }
    }
  }
}
```

#### Cursor
Configure in your Cursor MCP settings with the same configuration structure.

#### Other MCP Clients
- [Gemini CLI](https://github.com/google-gemini/gemini-cli)
- Any application built with the [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)

### 2. Development Mode

For development and testing:
```bash
uv run mcp dev src/main.py
```
This opens the MCP Inspector where you can test tools directly.

### 3. Example Conversations

Once connected to an AI client, you can use natural language commands:

**Deployment Management:**
```
User: "Deploy the customer service miniapp to production"
AI: I'll help you with that. Let me first search for the customer service miniapp...
```

**Analytics & Troubleshooting:**
```
User: "Show me all failed conversations from yesterday"
AI: I'll search for dialog logs with errors from the past 24 hours...
```

**Configuration Updates:**
```
User: "Update the welcome message for the support app"
AI: I'll help you update the welcome prompt. First, let me find the support app...
```

## 🔧 Tool Reference

### MiniApps Management

#### `search_miniapps(search_term?: string)`
Search for miniapps by name or keyword.
```typescript
// Find all miniapps with "customer" in the name
search_miniapps("customer")
// List all miniapps
search_miniapps()
```

#### `get_miniapp(miniapp_id: string)`
Retrieve complete configuration for a specific miniapp.
```typescript
get_miniapp("12345")
```

#### `set_miniapp_prompt(miniapp_id: string, prompt_type: string, prompt: string)`
Update various prompt types for a miniapp:
- `"welcome"` - Welcome message
- `"initial"` - Initial question prompt
- `"error_no_interpretation"` - When system cannot interpret user input
- `"error_no_response"` - When user provides no input
- `"reaction_greeting"` - Response to user greetings

### Orchestrator Apps

#### `search_orchestrator_apps(search_term?: string)`
Search for Orchestrator applications by keyword.

#### `get_orchestrator_app(canvas_id: string)`
Retrieve the complete canvas (dialog flow graph) for an Orchestrator app.

### Analytics & Insights

#### `get_dialog_logs(dialog_id: string)`
Fetch complete conversation history and analytics for a specific dialog session.

#### `search_dialog_logs(apps: string[], options?)`
Advanced dialog log search with filtering options:
- `from_date` / `to_date`: Time range filtering
- `ani`: Filter by phone numbers
- `region`: Filter by geographic region
- `steps_gt`: Filter conversations with more than N steps

### System Integration

#### `search_numbers(search_term?: string)`
Search for configured phone numbers in the system.

#### `search_variable_collections(search_term?: string)`
Find variable collections used across environments.

#### `get_collection_variables(collection_id: string)`
List all variables within a specific collection.

## 🔐 Security & Authentication

The OCP Co-Pilot Server uses OAuth2/OpenID Connect for secure authentication with OCP:

- **Token Management**: Automatic token acquisition, refresh, and revocation
- **Secure Storage**: Credentials stored in environment variables
- **Session Management**: Intelligent token caching and expiry handling

### Required Permissions

Ensure your OCP user account has appropriate permissions for:
- Reading miniapp configurations
- Updating miniapp prompts (if modification is needed)
- Accessing dialog logs and analytics
- Viewing orchestrator canvases
- Managing system integrations

## 🚦 Development & Testing

### Running Tests
```bash
uv run pytest src/tests/
```

### Code Quality
The project follows Python best practices:
- Type hints for better code clarity
- Comprehensive error handling
- Modular client architecture
- Extensive logging and debugging support

### Adding New Tools
To extend the Co-Pilot with new OCP functionality:

1. Create a new client module in `src/ocp/`
2. Extend the base client class
3. Add MCP tool functions in `src/main.py`
4. Update documentation and tests

## 📊 Monitoring & Observability

The server provides logging and monitoring capabilities:
- Authentication status and token lifecycle
- API request/response logging
- Error tracking and diagnostics
- Performance metrics for tool execution

## 🌟 Vision & Future

The OCP Co-Pilot represents a fundamental shift in how teams interact with complex cloud platforms. By providing a **conversational interface** to OCP's powerful capabilities, it transforms operational complexity into natural language simplicity.

### Roadmap

- **Enhanced AI Workflows**: More sophisticated multi-step task automation
- **Predictive Analytics**: Proactive monitoring and issue detection
- **Custom Integrations**: Plugin architecture for custom OCP extensions
- **Multi-Modal Interface**: Support for voice, visual, and text interactions
- **Team Collaboration**: Shared contexts and collaborative workflows

The Co-Pilot is more than just an assistant—it's a **collaborative partner** that empowers teams to focus on innovation while reducing operational overhead.

## 📝 License

[Add appropriate license information]

## 🤝 Contributing

We welcome contributions! Please see our contributing guidelines for details on:
- Code style and standards
- Testing requirements
- Pull request process
- Issue reporting

## 📞 Support

For support and questions:
- Technical documentation: [Link to docs]
- Issue tracking: [Link to issue tracker]
- Community: [Link to community channels]

---

**Built with ❤️ for the OCP Community**
