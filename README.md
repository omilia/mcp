# Omilia MCP Tools

This repository contains a set of tools for working with the Omilia Cloud Platform (OCP). These utilities help manage miniapps, orchestrator apps, and dialog logs.

## Tools Overview

- **search_miniapps**: Search for miniapps by name or keyword.
- **get_miniapp**: Retrieve details for a specific miniapp using its ID.
- **set_miniapp_prompt**: Update prompts (welcome, error, reaction messages) for a miniapp.
- **get_dialog_logs**: Fetch logs for a specific dialog session.
- **search_orchestrator_apps**: Search for Orchestrator apps by keyword.
- **get_orchestrator_app**: Retrieve the canvas (nodes and edges) for an Orchestrator app by ID.
- **search_dialog_logs**: Search dialog logs with various filters (date, app, region, etc.).
- **search_numbers**: Search for phone numbers with optional search term.
- **search_variable_collections**: Search variable collections with optional search term.
- **get_collection_variables**: Get a list of all variables in a collection by ID.


---

## Installation

- Make sure you have **Python 3.10** or newer installed.
- Install [uv](https://github.com/astral-sh/uv).
- Clone this repository and navigate to the project directory.
- Copy the file `.env.example` to `.env` and set the appropriate values.
- Test if the istallation is correct by running `uv run mcp dev src/main.py`. This should open the mcp development server. Click on connect and try it out.

## Usage

You can use these tools in two main ways:

### 1. Self-hosting (MCP Python SDK)

You can run your own MCP server using the [official Python MCP SDK](https://github.com/modelcontextprotocol/python-sdk). This is the most flexible option and is recommended for advanced users. For full instructions, see the [MCP Python SDK README](https://github.com/modelcontextprotocol/python-sdk#running-your-server).

### 2. Local usage with Gemini CLI, Cursor, or Claude Desktop

You can also use this project locally with any MCP-compatible client, such as:

- [Gemini CLI](https://github.com/google-gemini/gemini-cli)
- [Cursor](https://www.cursor.com/)
- [Claude Desktop](https://www.anthropic.com/claude)

Each of these clients allows you to connect to local MCP servers. For more information, see their respective documentation:
- [Gemini CLI: Configuring custom MCP servers](https://github.com/google-gemini/gemini-cli/blob/main/docs/tools/mcp-server.md#how-to-set-up-your-mcp-server)
- [Claude Desktop: MCP servers](https://modelcontextprotocol.info/docs/quickstart/user/)
- [Cursor: Configuring custom MCP servers](https://docs.cursor.com/context/model-context-protocol#manual-configuration)

#### Configuring MCP Servers

To use this project with any of the above clients, you need to configure your MCP servers. For example, you can use the following `mcp.json` configuration (place it in the appropriate config directory for your client):

```json
{
  "mcpServers": {
    "Omilia MCP": {
      "command": "uv",
      "args": [
        "run",
        "--with",
        "mcp",
        "mcp",
        "run",
        "<path_to_cloned_repository>>/omilia-mcp/src/main.py"
      ],
      "env": {
        "PATH": "<depending on how you installed the needed tools you may need to paste your PATH here>"
      }
    }
  }
}
```
---
