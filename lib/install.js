import { spawnSync } from "node:child_process";

import { DEFAULT_SERVER_NAME, PACKAGE_NAME, getEnvBlock } from "./config.js";
import { maskSecret } from "./wizard.js";

/**
 * buildClaudeMcpAddArgs(opts) — returns the argument array for `claude mcp add`.
 *
 * Produces:
 *   ["mcp","add","<serverName>","--scope","user",
 *    "--env","KEY=value", ...         (one pair per env entry, in object order)
 *    "--","npx","-y","github:omilia/mcp","run"]
 *
 * The token is a SINGLE array element ("OCP_ACCESS_TOKEN=<value>") — it is never
 * shell-interpolated, so shell history / ps visibility is minimised (T-02-03).
 */
export function buildClaudeMcpAddArgs(opts) {
  const {
    serverName = DEFAULT_SERVER_NAME,
    authChoice = "pat"
  } = opts;

  const envBlock = getEnvBlock(authChoice, opts);

  // Flatten { KEY: value, ... } → ["--env", "KEY=value", ...]
  // Each value is a single array element — never concatenated into a shell string.
  const envPairs = [];
  for (const [key, value] of Object.entries(envBlock)) {
    envPairs.push("--env", `${key}=${value}`);
  }

  return [
    "mcp", "add", serverName, "--scope", "user",
    ...envPairs,
    "--", "npx", "-y", PACKAGE_NAME, "run"
  ];
}

/**
 * buildSnippet(opts) — renders the masked, human-facing `claude mcp add` command
 * string. Used for both the CLI-absent fallback and the --print path so both
 * emit identical, masked output (T-02-04: raw token never lands on stdout).
 *
 * Each env value is passed through maskSecret before composing the snippet so
 * the raw secret is absent from the returned string.
 */
function buildSnippet(opts) {
  const { serverName = DEFAULT_SERVER_NAME, authChoice = "pat" } = opts;
  const envBlock = getEnvBlock(authChoice, opts);

  // Build the env pairs with masked values — masked output is intentional (T-02-04).
  const maskedEnvParts = [];
  for (const [key, value] of Object.entries(envBlock)) {
    maskedEnvParts.push(`--env ${key}=${maskSecret(value)}`);
  }

  const parts = [
    `claude mcp add ${serverName} --scope user`,
    ...maskedEnvParts,
    `-- npx -y ${PACKAGE_NAME} run`
  ];

  return parts.join(" ");
}

/**
 * claudeAvailable(spawn) — returns true when the injected spawn for
 * `claude --version` exits with status 0; false when spawn throws ENOENT
 * or returns a non-zero / null status (T-02-06: ENOENT treated as unavailable).
 */
export function claudeAvailable(spawn = spawnSync) {
  try {
    const result = spawn("claude", ["--version"]);
    return result !== null && result !== undefined && result.status === 0;
  } catch {
    // ENOENT or any other spawn error means claude is not available.
    return false;
  }
}

/**
 * installClaudeCode(options, io, deps = {}) — installs the OCP MCP server for
 * Claude Code by invoking `claude mcp add` via the injected spawn (or the real
 * spawnSync when no inject is provided).
 *
 * CANONICAL SPAWN CONTRACT:
 *   The caller resolves spawn ONCE here: `const spawn = deps.spawn ?? spawnSync`.
 *   Tests attach a fake spawn on the io object; finishInit (lib/cli.js) forwards
 *   `{ spawn: io.spawn ?? spawnSync }` — so the io.spawn → deps.spawn chain is
 *   fixed, with a single injection surface.
 *
 * Three execution paths:
 *   (1) options.print === true  → write masked snippet to stdout, return 0 (no spawn).
 *   (2) claude not on PATH      → write masked guidance to stdout, return 0 (graceful, CLI-03).
 *   (3) claude on PATH          → run mcp add, return 0 on success, 1 on failure.
 *
 * Never throws (CONVENTIONS: catch and return code).
 *
 * @returns {number} Integer exit code.
 */
export function installClaudeCode(options, io, deps = {}) {
  // Single injection surface per CANONICAL SPAWN CONTRACT.
  const spawn = deps.spawn ?? spawnSync;

  // Path 1: --print mode — emit masked snippet only, do NOT spawn (CLI-01).
  if (options.print) {
    const snippet = buildSnippet(options);
    io.stdout.write(`Run this command to register the OCP MCP server in Claude Code:\n\n  ${snippet}\n`);
    return 0;
  }

  // Path 2: claude CLI absent (CLI-03) — emit masked guidance, return 0 gracefully.
  if (!claudeAvailable(spawn)) {
    const snippet = buildSnippet(options);
    io.stdout.write(
      `claude CLI not found on PATH. To register the OCP MCP server in Claude Code, ` +
      `install the Claude CLI (https://claude.ai/download) and then run:\n\n` +
      `  ${snippet}\n`
    );
    return 0;
  }

  // Path 3: invoke claude mcp add.
  const argv = buildClaudeMcpAddArgs(options);

  try {
    const result = spawn("claude", argv);
    const exitCode = result?.status ?? 1;

    if (exitCode === 0) {
      io.stdout.write("OCP MCP server registered in Claude Code via `claude mcp add`.\n");
      return 0;
    }

    io.stderr.write(`claude mcp add exited with code ${exitCode}.\n`);
    return 1;
  } catch (error) {
    io.stderr.write(`Failed to run claude mcp add: ${error.message}\n`);
    return 1;
  }
}
