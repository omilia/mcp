import { spawn as nodeSpawn } from "node:child_process";
import { createInterface as nodeCreateInterface } from "node:readline";

import { buildRunCommand } from "./runtime.js";

/**
 * smokeTest(deps) — performs an MCP stdio handshake against the OCP server.
 *
 * Spawns the resolved run command (from buildRunCommand), sends:
 *   1. JSON-RPC `initialize` request (id 1)
 *   2. `notifications/initialized` notification
 *   3. JSON-RPC `tools/list` request (id 2)
 *
 * Returns:
 *   { ok: true,  toolCount: N, hasReadGuide: bool }  — non-empty tools array
 *   { ok: false, reason: string }                     — empty/timeout/spawn-error
 *
 * NEVER throws. NEVER places child stdout, stderr, or command.env in the result.
 * ALWAYS calls child.kill() exactly once (settled guard).
 *
 * Injectable deps (for unit tests):
 *   deps.spawn          — replaces node:child_process spawn
 *   deps.createInterface — replaces node:readline createInterface
 *   deps.buildRunCommand — replaces lib/runtime.js buildRunCommand
 *   deps.timeoutMs      — override timeout (default 30000 ms)
 */
export async function smokeTest(deps = {}) {
  // ── Resolve injections (CANONICAL SPAWN CONTRACT) ──────────────────────────
  const spawnFn = deps.spawn ?? nodeSpawn;
  const createInterface = deps.createInterface ?? nodeCreateInterface;
  const buildCmd = deps.buildRunCommand ?? buildRunCommand;
  const timeoutMs = deps.timeoutMs ?? 30000;

  // ── Settled guard — resolve exactly once ───────────────────────────────────
  let settled = false;
  let resolveResult;
  const resultPromise = new Promise((res) => { resolveResult = res; });

  function settle(value) {
    if (settled) return;
    settled = true;
    cleanup();
    resolveResult(value);
  }

  // ── Build command (may throw if Python sources absent) ─────────────────────
  let command;
  try {
    command = buildCmd();
  } catch (err) {
    return { ok: false, reason: `failed to start server: ${err.message}` };
  }

  // ── Spawn child ────────────────────────────────────────────────────────────
  const child = spawnFn(command.command, command.args, {
    stdio: ["pipe", "pipe", "pipe"],
    env: command.env
  });

  // ── Cleanup: kill child and clear timer — runs exactly once via settled ────
  let timer = null;
  function cleanup() {
    if (timer !== null) {
      clearTimeout(timer);
      timer = null;
    }
    try { child.kill(); } catch { /* ignore errors on already-dead process */ }
  }

  // ── Bounded timeout ────────────────────────────────────────────────────────
  timer = setTimeout(() => {
    settle({ ok: false, reason: `smoke test timed out after ${timeoutMs}ms` });
  }, timeoutMs);

  // ── Spawn error (e.g. uv ENOENT) ──────────────────────────────────────────
  child.on("error", (err) => {
    // Static template — never interpolate env values (VER-03).
    settle({ ok: false, reason: `failed to start server: ${err.message}` });
  });

  // ── Handshake state machine ────────────────────────────────────────────────
  const rl = createInterface({ input: child.stdout });

  const initializeRequest = JSON.stringify({
    jsonrpc: "2.0",
    id: 1,
    method: "initialize",
    params: {
      protocolVersion: "2024-11-05",
      capabilities: {},
      clientInfo: { name: "ocp-mcp-smoketest", version: "1.0.0" }
    }
  });

  const initializedNotification = JSON.stringify({
    jsonrpc: "2.0",
    method: "notifications/initialized"
  });

  const toolsListRequest = JSON.stringify({
    jsonrpc: "2.0",
    id: 2,
    method: "tools/list",
    params: {}
  });

  // Send initial request.
  try {
    child.stdin.write(initializeRequest + "\n");
  } catch {
    // stdin write failure — will surface via child error event or timeout.
  }

  rl.on("line", (line) => {
    if (settled) return;

    let msg;
    try {
      msg = JSON.parse(line);
    } catch {
      // Unparseable line (log output, etc.) — ignore.
      return;
    }

    // Response to initialize (id 1): send notification + tools/list.
    if (msg.id === 1) {
      try {
        child.stdin.write(initializedNotification + "\n");
        child.stdin.write(toolsListRequest + "\n");
      } catch {
        // stdin write failure — will surface via child error event or timeout.
      }
      return;
    }

    // Response to tools/list (id 2): inspect tools array.
    if (msg.id === 2) {
      const tools = msg.result && Array.isArray(msg.result.tools) ? msg.result.tools : [];
      if (tools.length === 0) {
        settle({ ok: false, reason: "server returned no tools" });
      } else {
        settle({
          ok: true,
          toolCount: tools.length,
          hasReadGuide: tools.some((t) => t.name === "read_guide")
        });
      }
    }
  });

  return resultPromise;
}
