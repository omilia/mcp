export const DEFAULT_SERVER_NAME = "OCP";
export const PACKAGE_NAME = "github:omilia/mcp";
export const DEFAULT_BASE_URL_PLACEHOLDER = "your-ocp-base-url";
export const DEFAULT_ACCESS_TOKEN_PLACEHOLDER = "your-ocp-access-token";
// Inline literal placeholders for the Keycloak shape (same pattern as
// the PAT defaults above — no `${VAR}` indirection). `master` is itself
// the production-default realm value; the placeholder is the value, NOT
// a "your-ocp-realm" stand-in.
export const DEFAULT_USERNAME_PLACEHOLDER = "your-ocp-username";
export const DEFAULT_PASSWORD_PLACEHOLDER = "your-ocp-password";
export const DEFAULT_REALM_PLACEHOLDER = "master";

export const SUPPORTED_AUTH_CHOICES = ["pat", "keycloak"];

export const JSON_MCP_CLIENTS = new Set(["cursor", "claude", "claude-code"]);
export const SUPPORTED_CLIENTS = new Set([...JSON_MCP_CLIENTS, "codex", "vscode"]);

export function buildClientConfig(client, options = {}) {
  const {
    serverName = DEFAULT_SERVER_NAME,
    baseUrl = DEFAULT_BASE_URL_PLACEHOLDER,
    accessToken = DEFAULT_ACCESS_TOKEN_PLACEHOLDER,
    username = DEFAULT_USERNAME_PLACEHOLDER,
    password = DEFAULT_PASSWORD_PLACEHOLDER,
    realm = DEFAULT_REALM_PLACEHOLDER,
    useEnvVars = false,
    authChoice = "pat"
  } = options;
  const serverOptions = { baseUrl, accessToken, username, password, realm, useEnvVars, authChoice };

  if (JSON_MCP_CLIENTS.has(client)) {
    return buildMcpServersConfig({ serverName, ...serverOptions });
  }

  if (client === "vscode") {
    return buildVsCodeConfig({ serverName, ...serverOptions });
  }

  if (client === "codex") {
    return buildCodexConfig({ serverName, ...serverOptions });
  }

  throw new Error(`Unsupported client: ${client}`);
}

export function buildCursorConfig(options = {}) {
  return buildClientConfig("cursor", options);
}

export function serializeClientConfig(client, config) {
  if (client === "codex") {
    return serializeCodexConfig(config);
  }

  return serializeConfig(config);
}

export function clientConfigPath(client, env = process.env) {
  const home = env.HOME || env.USERPROFILE;

  if (!home) {
    return undefined;
  }

  if (client === "cursor") {
    return `${home}/.cursor/mcp.json`;
  }

  if (client === "claude") {
    return `${home}/Library/Application Support/Claude/claude_desktop_config.json`;
  }

  if (client === "claude-code") {
    return `${home}/.claude/settings.json`;
  }

  return undefined;
}

function buildMcpServersConfig({ serverName, ...serverOptions }) {
  return {
    mcpServers: {
      [serverName]: buildServerDefinition(serverOptions)
    }
  };
}

function buildVsCodeConfig({ serverName, ...serverOptions }) {
  return {
    servers: {
      [serverName]: buildServerDefinition(serverOptions)
    }
  };
}

function buildCodexConfig({ serverName, ...serverOptions }) {
  return {
    serverName,
    command: "npx",
    args: ["-y", PACKAGE_NAME, "run"],
    env: getEnvBlock(serverOptions.authChoice, serverOptions)
  };
}

function buildServerDefinition({ authChoice, ...rest }) {
  return {
    command: "npx",
    args: ["-y", PACKAGE_NAME, "run"],
    env: getEnvBlock(authChoice, rest)
  };
}

/**
 * Return the env-block object for the given auth choice.
 *
 * For `authChoice === "pat"` the shape carries OCP_BASE_URL + OCP_ACCESS_TOKEN.
 * For `authChoice === "keycloak"` the shape carries Keycloak password-grant
 * inputs (OCP_USERNAME, OCP_PASSWORD, OCP_KEYCLOAK_REALM) — no OCP_ACCESS_TOKEN.
 * Both honor `useEnvVars` for `${VAR}` indirection.
 */
export function getEnvBlock(authChoice, options = {}) {
  const {
    baseUrl = DEFAULT_BASE_URL_PLACEHOLDER,
    accessToken = DEFAULT_ACCESS_TOKEN_PLACEHOLDER,
    username = DEFAULT_USERNAME_PLACEHOLDER,
    password = DEFAULT_PASSWORD_PLACEHOLDER,
    realm = DEFAULT_REALM_PLACEHOLDER,
    useEnvVars = false
  } = options;

  if (authChoice === "pat") {
    if (useEnvVars) {
      // Indirection mode: values resolve from the launching shell's env.
      // Use this when the MCP client supports ${VAR} expansion AND you would
      // rather not store the token in a config file.
      return {
        OCP_BASE_URL: "${OCP_BASE_URL}",
        OCP_ACCESS_TOKEN: "${OCP_ACCESS_TOKEN}"
      };
    }
    // Default: inline literal values, no `${VAR}` indirection.
    // Users paste the real values into the config file; the MCP client never
    // depends on shell-env propagation (which is brittle for GUI apps on macOS).
    return {
      OCP_BASE_URL: baseUrl,
      OCP_ACCESS_TOKEN: accessToken
    };
  }

  if (authChoice === "keycloak") {
    if (useEnvVars) {
      return {
        OCP_BASE_URL: "${OCP_BASE_URL}",
        OCP_USERNAME: "${OCP_USERNAME}",
        OCP_PASSWORD: "${OCP_PASSWORD}",
        OCP_KEYCLOAK_REALM: "${OCP_KEYCLOAK_REALM}"
      };
    }
    return {
      OCP_BASE_URL: baseUrl,
      OCP_USERNAME: username,
      OCP_PASSWORD: password,
      OCP_KEYCLOAK_REALM: realm
    };
  }

  throw new Error(
    `Unsupported --auth value: ${authChoice}. Supported values are: pat, keycloak.`
  );
}

export function serializeConfig(config) {
  return `${JSON.stringify(config, null, 2)}\n`;
}

function serializeCodexConfig(config) {
  const envLines = Object.entries(config.env)
    .map(([key, value]) => `${key} = ${JSON.stringify(value)}`)
    .join("\n");
  return `[mcp_servers.${quoteTomlKey(config.serverName)}]
command = "npx"
args = ["-y", "${PACKAGE_NAME}", "run"]

[mcp_servers.${quoteTomlKey(config.serverName)}.env]
${envLines}
`;
}

function quoteTomlKey(key) {
  return JSON.stringify(key);
}
