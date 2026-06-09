import assert from "node:assert/strict";
import crypto from "node:crypto";
import { existsSync, mkdtempSync, readFileSync, statSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { Readable } from "node:stream";
import test from "node:test";

import { runCli } from "../lib/cli.js";
import { buildClientConfig, buildCursorConfig, clientConfigPath, getEnvBlock, JSON_MCP_CLIENTS } from "../lib/config.js";
import { buildRunCommand } from "../lib/runtime.js";

// Regression gate: SHA-256 of `init --client claude --print` output
// with no --auth arg (defaults to PAT). Updating this value is a
// deliberate API change — it is the contract that PAT-only users see
// byte-identical output across releases. Update this constant only
// alongside an intentional change to the PAT-default emission.
const PAT_INIT_GOLDEN_SHA256 = "9f03b6648fc1e5573acf9bc3fc5bc0c7f56ee3f839fe5bb8acf5d4d498103647";

function createIo() {
  const output = {
    stderr: "",
    stdout: ""
  };

  return {
    output,
    stderr: {
      write(value) {
        output.stderr += value;
      }
    },
    stdout: {
      write(value) {
        output.stdout += value;
      }
    }
  };
}

test("builds Cursor config with inline literal placeholders by default", () => {
  const config = buildCursorConfig();

  assert.deepEqual(config, {
    mcpServers: {
      OCP: {
        command: "npx",
        args: ["-y", "github:omilia/mcp", "run"],
        env: {
          OCP_BASE_URL: "your-ocp-base-url",
          OCP_ACCESS_TOKEN: "your-ocp-access-token"
        }
      }
    }
  });
});

test("builds Cursor config with --use-env-vars indirection", () => {
  const config = buildCursorConfig({ useEnvVars: true });

  assert.deepEqual(config.mcpServers.OCP.env, {
    OCP_BASE_URL: "${OCP_BASE_URL}",
    OCP_ACCESS_TOKEN: "${OCP_ACCESS_TOKEN}"
  });
});

test("builds Cursor config with explicit base-url and access-token", () => {
  const config = buildCursorConfig({
    baseUrl: "https://us1-m.ocp.ai",
    accessToken: "pat-abc123"
  });

  assert.deepEqual(config.mcpServers.OCP.env, {
    OCP_BASE_URL: "https://us1-m.ocp.ai",
    OCP_ACCESS_TOKEN: "pat-abc123"
  });
});

test("prints Cursor config by default", () => {
  const io = createIo();
  const exitCode = runCli(["init", "--client", "cursor"], io);

  assert.equal(exitCode, 0);
  assert.equal(io.output.stderr, "");
  assert.deepEqual(JSON.parse(io.output.stdout), buildCursorConfig());
});

test("supports explicit print flag", () => {
  const io = createIo();
  const exitCode = runCli(["init", "--client", "cursor", "--print"], io);

  assert.equal(exitCode, 0);
  assert.deepEqual(JSON.parse(io.output.stdout), buildCursorConfig());
});

test("default printed config has placeholder (not secret) values", () => {
  const io = createIo();
  const exitCode = runCli(["init", "--client", "cursor", "--print"], io);

  assert.equal(exitCode, 0);
  assert.equal(io.output.stdout.includes("Bearer "), false);
  assert.equal(io.output.stdout.includes("sk-"), false);
  assert.equal(io.output.stdout.includes("your-ocp-access-token"), true);
  assert.equal(io.output.stdout.includes("your-ocp-base-url"), true);
});

test("--access-token and --base-url inject real values", () => {
  const io = createIo();
  const exitCode = runCli([
    "init", "--client", "cursor", "--print",
    "--base-url", "https://us1-m.ocp.ai",
    "--access-token", "pat-xyz"
  ], io);

  assert.equal(exitCode, 0);
  const parsed = JSON.parse(io.output.stdout);
  assert.equal(parsed.mcpServers.OCP.env.OCP_BASE_URL, "https://us1-m.ocp.ai");
  assert.equal(parsed.mcpServers.OCP.env.OCP_ACCESS_TOKEN, "pat-xyz");
});

test("--use-env-vars emits ${VAR} indirection", () => {
  const io = createIo();
  const exitCode = runCli(["init", "--client", "cursor", "--print", "--use-env-vars"], io);

  assert.equal(exitCode, 0);
  const parsed = JSON.parse(io.output.stdout);
  assert.equal(parsed.mcpServers.OCP.env.OCP_BASE_URL, "${OCP_BASE_URL}");
  assert.equal(parsed.mcpServers.OCP.env.OCP_ACCESS_TOKEN, "${OCP_ACCESS_TOKEN}");
});

test("--use-env-vars rejects combination with --access-token", () => {
  const io = createIo();
  const exitCode = runCli([
    "init", "--client", "cursor", "--print",
    "--use-env-vars", "--access-token", "pat-xyz"
  ], io);

  assert.equal(exitCode, 1);
  assert.match(io.output.stderr, /--use-env-vars cannot be combined/);
});

test("rejects unsupported clients", () => {
  const io = createIo();
  const exitCode = runCli(["init", "--client", "gemini"], io);

  assert.equal(exitCode, 1);
  assert.equal(io.output.stdout, "");
  assert.match(io.output.stderr, /Unsupported client: gemini/);
});

test("prints VS Code config shape", () => {
  const io = createIo();
  const exitCode = runCli(["init", "--client", "vscode", "--print"], io);

  assert.equal(exitCode, 0);
  assert.deepEqual(JSON.parse(io.output.stdout), buildClientConfig("vscode"));
});

test("prints Codex TOML config shape with literal placeholder by default", () => {
  const io = createIo();
  const exitCode = runCli(["init", "--client", "codex", "--print"], io);

  assert.equal(exitCode, 0);
  assert.match(io.output.stdout, /\[mcp_servers\."OCP"\]/);
  assert.match(io.output.stdout, /command = "npx"/);
  assert.match(io.output.stdout, /OCP_ACCESS_TOKEN = "your-ocp-access-token"/);
});

test("Codex TOML supports --use-env-vars indirection", () => {
  const io = createIo();
  const exitCode = runCli(["init", "--client", "codex", "--print", "--use-env-vars"], io);

  assert.equal(exitCode, 0);
  assert.match(io.output.stdout, /OCP_ACCESS_TOKEN = "\$\{OCP_ACCESS_TOKEN\}"/);
});

test("writes Cursor config to an explicit path", () => {
  const io = createIo();
  const directory = mkdtempSync(join(tmpdir(), "ocp-mcp-"));
  const outputPath = join(directory, "mcp.json");
  const exitCode = runCli(["init", "--client", "cursor", "--write", "--path", outputPath], io);

  assert.equal(exitCode, 0);
  assert.deepEqual(JSON.parse(readFileSync(outputPath, "utf8")), buildCursorConfig());
});

test("refuses to overwrite existing server config without force", () => {
  const io = createIo();
  const directory = mkdtempSync(join(tmpdir(), "ocp-mcp-"));
  const outputPath = join(directory, "mcp.json");

  assert.equal(runCli(["init", "--client", "cursor", "--write", "--path", outputPath], createIo()), 0);
  const exitCode = runCli(["init", "--client", "cursor", "--write", "--path", outputPath], io);

  assert.equal(exitCode, 1);
  assert.equal(io.output.stdout, "");
  assert.match(io.output.stderr, /Re-run with --force/);
});

test("clientConfigPath returns undefined for claude-code (CLI-02: no settings.json write path)", () => {
  // CLI-02: claude-code is installed via `claude mcp add`, not JSON config file.
  const result = clientConfigPath("claude-code", { HOME: "/home/user" });
  assert.equal(result, undefined);
});

test("init --client claude-code invokes claude mcp add with correct argv (CLI-01)", () => {
  const recorded = [];
  const io = createIo();
  // Attach fake spawn directly on io (CANONICAL SPAWN CONTRACT — NOT via createScriptedIo).
  io.spawn = (cmd, args) => { recorded.push({ cmd, args }); return { status: 0 }; };

  const exitCode = runCli([
    "init", "--client", "claude-code",
    "--base-url", "https://ocp.example.com",
    "--access-token", "pat-cc-1234"
  ], io);

  assert.equal(exitCode, 0);
  // The version-check spawn + the mcp add spawn are both recorded
  const mcpCall = recorded.find((r) => r.args && r.args[0] === "mcp");
  assert.ok(mcpCall, "must have recorded the claude mcp add spawn");
  assert.equal(mcpCall.cmd, "claude");
  assert.deepEqual(mcpCall.args, [
    "mcp", "add", "OCP", "--scope", "user",
    "--env", "OCP_BASE_URL=https://ocp.example.com",
    "--env", "OCP_ACCESS_TOKEN=pat-cc-1234",
    "--", "npx", "-y", "github:omilia/mcp", "run"
  ]);
  // No file written, no settings.json reference
  assert.equal(io.output.stdout.includes("settings.json"), false);
});

test("PAT init for claude produces byte-identical output to golden SHA", () => {
  const io = createIo();
  const exitCode = runCli(["init", "--client", "claude", "--print"], io);

  assert.equal(exitCode, 0);
  const actualSha = crypto.createHash("sha256").update(io.output.stdout).digest("hex");
  assert.equal(
    actualSha,
    PAT_INIT_GOLDEN_SHA256,
    `PAT-default output changed; SHA was ${actualSha}. ` +
    "This breaks the byte-identical PAT-default contract. " +
    "Update PAT_INIT_GOLDEN_SHA256 only alongside an intentional change to PAT emission."
  );
});

test("builds Keycloak config via buildClientConfig direct call", () => {
  const config = buildClientConfig("claude", { authChoice: "keycloak" });

  assert.deepEqual(config.mcpServers.OCP.env, {
    OCP_BASE_URL: "your-ocp-base-url",
    OCP_USERNAME: "your-ocp-username",
    OCP_PASSWORD: "your-ocp-password",
    OCP_KEYCLOAK_REALM: "master"
  });
});

test("builds Keycloak config with literal placeholders via CLI", () => {
  const io = createIo();
  const exitCode = runCli(["init", "--client", "claude", "--auth", "keycloak", "--print"], io);

  assert.equal(exitCode, 0);
  const parsed = JSON.parse(io.output.stdout);
  assert.deepEqual(parsed.mcpServers.OCP.env, {
    OCP_BASE_URL: "your-ocp-base-url",
    OCP_USERNAME: "your-ocp-username",
    OCP_PASSWORD: "your-ocp-password",
    OCP_KEYCLOAK_REALM: "master"
  });
  // PAT key must NOT appear in the Keycloak shape.
  assert.equal(io.output.stdout.includes("OCP_ACCESS_TOKEN"), false);
});

test("builds Keycloak config with --use-env-vars indirection", () => {
  const io = createIo();
  const exitCode = runCli(
    ["init", "--client", "claude", "--auth", "keycloak", "--use-env-vars", "--print"],
    io
  );

  assert.equal(exitCode, 0);
  const parsed = JSON.parse(io.output.stdout);
  assert.deepEqual(parsed.mcpServers.OCP.env, {
    OCP_BASE_URL: "${OCP_BASE_URL}",
    OCP_USERNAME: "${OCP_USERNAME}",
    OCP_PASSWORD: "${OCP_PASSWORD}",
    OCP_KEYCLOAK_REALM: "${OCP_KEYCLOAK_REALM}"
  });
});

test("rejects --auth oauth with exit code 2", () => {
  const io = createIo();
  const exitCode = runCli(
    ["init", "--client", "claude", "--auth", "oauth", "--print"],
    io
  );

  assert.equal(exitCode, 2);
  assert.match(io.output.stderr, /supported/i);
  assert.match(io.output.stderr, /pat/i);
  assert.match(io.output.stderr, /keycloak/i);
});

test("--auth keycloak threads --username / --password / --realm into env block", () => {
  const io = createIo();
  const exitCode = runCli([
    "init", "--client", "claude", "--auth", "keycloak", "--print",
    "--username", "alice",
    "--password", "wonderland",
    "--realm", "ocp"
  ], io);

  assert.equal(exitCode, 0);
  const parsed = JSON.parse(io.output.stdout);
  assert.equal(parsed.mcpServers.OCP.env.OCP_USERNAME, "alice");
  assert.equal(parsed.mcpServers.OCP.env.OCP_PASSWORD, "wonderland");
  assert.equal(parsed.mcpServers.OCP.env.OCP_KEYCLOAK_REALM, "ocp");
});

test("prints run dry-run command without leaking token values", () => {
  const io = createIo();
  const exitCode = runCli(["run", "--dry-run"], io);

  assert.equal(exitCode, 0);
  const output = JSON.parse(io.output.stdout);
  assert.equal(output.command, "uv");
  assert.equal(output.args.includes("fastmcp"), true);
  assert.equal(io.output.stdout.includes("Bearer "), false);
  assert.equal(io.output.stdout.includes("sk-"), false);
});

test("builds run command against the development Python source", () => {
  const command = buildRunCommand();

  assert.equal(command.command, "uv");
  assert.equal(command.args.includes("fastmcp"), true);
  assert.equal(command.args.at(-1).endsWith("src/server.py:mcp"), true);
});

test("run rejects unsupported entrypoints", () => {
  assert.throws(
    () => buildRunCommand({ entrypoint: "bogus" }),
    /Unsupported entrypoint/
  );
});

// ─── Scripted TTY helper ──────────────────────────────────────────────────────
// Creates an io object with a scripted stdin Readable (lazy async generator so
// readline sees EOF only when all lines are consumed) and isTTY=true, plus
// stdout/stderr capture. Used for interactive wizard tests.
function createScriptedIo(answers) {
  const outputCapture = {
    stderr: "",
    stdout: ""
  };

  const lines = answers.slice();

  const input = Readable.from(
    (async function* () {
      for (const line of lines) {
        yield line + "\n";
      }
    })()
  );
  // Signal to runInit that this is a TTY environment.
  input.isTTY = true;

  return {
    io: {
      input,
      stderr: {
        write(value) {
          outputCapture.stderr += value;
        }
      },
      stdout: {
        write(value) {
          outputCapture.stdout += value;
        }
      }
    },
    output: outputCapture
  };
}

// ─── Task 1 / Task 2 integration tests ───────────────────────────────────────

test("no-TTY bare init returns 1 and stderr names --client (WIZ-06)", async () => {
  // Inject io.input with isTTY=false to simulate a non-interactive (CI) environment.
  const outputCapture = { stderr: "", stdout: "" };
  const io = {
    input: { isTTY: false },
    stderr: { write(v) { outputCapture.stderr += v; } },
    stdout: { write(v) { outputCapture.stdout += v; } }
  };
  const result = await Promise.resolve(runCli(["init"], io));

  assert.equal(result, 1);
  assert.match(outputCapture.stderr, /--client/);
  // Must NOT be the old parseInitOptions throw message
  assert.equal(outputCapture.stderr.includes("Missing required option: --client"), false);
});

test("interactive bare init reaches masked confirmation summary (WIZ-01, WIZ-04)", async () => {
  // parseInitOptions defaults authChoice to "pat", so the wizard only prompts for:
  // client, baseUrl, accessToken (3 fields). Auth choice is already resolved.
  // Script "2" (claude / Claude Desktop) — a JSON_MCP_CLIENTS member — so finishInit
  // emits the confirmation summary + config JSON without routing to the real spawnSync.
  // (createScriptedIo has no io.spawn; "1" = claude-code would hit the real claude CLI.)
  const { io, output } = createScriptedIo(["2", "https://ocp.example.com", "super-secret-token-1234"]);
  const result = await Promise.resolve(runCli(["init"], io));

  assert.equal(result, 0);
  // Confirmation summary must be present on stdout
  assert.match(output.stdout, /Configuration summary/);

  // Extract just the confirmation summary section (before the config JSON output).
  // The confirmation summary is emitted before finishInit prints the config.
  const summaryEnd = output.stdout.indexOf("{");
  const summaryPortion = summaryEnd >= 0 ? output.stdout.slice(0, summaryEnd) : output.stdout;

  // Raw token must NOT appear in the confirmation summary (WIZ-04, T-01-07)
  assert.equal(summaryPortion.includes("super-secret-token-1234"), false,
    "Raw token must not appear in confirmation summary");
  // The masked tail should appear in the summary (last 4 of "super-secret-token-1234" = "1234")
  assert.match(summaryPortion, /1234/);
});

test("fully-flagged --print returns config JSON only, no prompts (WIZ-05)", async () => {
  // Use cursor (a JSON client) so the --print path emits config JSON.
  // (claude-code --print emits a masked `claude mcp add` snippet, not JSON.)
  const io = createIo();
  const result = await Promise.resolve(runCli([
    "init", "--client", "cursor",
    "--auth", "pat",
    "--base-url", "https://ocp.example.com",
    "--access-token", "pat-test-token",
    "--print"
  ], io));

  assert.equal(result, 0);
  // Stdout must parse as JSON (config only)
  const parsed = JSON.parse(io.output.stdout);
  assert.ok(parsed.mcpServers ?? parsed.servers ?? parsed);
  // No prompt labels on stdout
  assert.equal(io.output.stdout.includes("Base URL"), false);
  assert.equal(io.output.stdout.includes("Select"), false);
  assert.equal(io.output.stdout.includes("MCP client"), false);
});

test("claude-code --print emits the masked mcp add command, no spawn (CLI-01)", async () => {
  const recorded = [];
  const io = createIo();
  // Attach fake spawn directly on io (CANONICAL SPAWN CONTRACT — NOT via createScriptedIo).
  io.spawn = (cmd, args) => { recorded.push({ cmd, args }); return { status: 0 }; };

  const result = await Promise.resolve(runCli([
    "init", "--client", "claude-code",
    "--auth", "pat",
    "--base-url", "https://ocp.example.com",
    "--access-token", "pat-print-9999",
    "--print"
  ], io));

  assert.equal(result, 0);
  // print mode must NOT spawn any process
  assert.equal(recorded.length, 0, "print mode must not invoke spawn at all");
  // stdout must reference mcp add
  assert.ok(io.output.stdout.includes("mcp add"), "stdout must include 'mcp add'");
  // raw token must NOT appear
  assert.ok(!io.output.stdout.includes("pat-print-9999"),
    "raw token must not appear in print mode stdout");
  // masked tail must appear (last 4 chars of "pat-print-9999" = "9999")
  assert.ok(io.output.stdout.includes("9999"),
    "masked tail '9999' must appear in print mode stdout");
});

test("wizard + --write: confirmation summary emitted before file write (WIZ-04 ordering)", async () => {
  const directory = mkdtempSync(join(tmpdir(), "ocp-mcp-wiz-"));
  const outputPath = join(directory, "config.json");

  // parseInitOptions defaults authChoice to "pat"; wizard prompts for: client, baseUrl, accessToken.
  // Script "2" (claude / Claude Desktop) — a JSON client — so the file-write assertions remain valid.
  // ("1" = claude-code routes through installClaudeCode and does not write JSON config files.)
  const { io, output } = createScriptedIo(["2", "https://ocp.example.com", "wiz-write-token-9999"]);
  const result = await Promise.resolve(runCli(["init", "--write", "--path", outputPath], io));

  assert.equal(result, 0);
  // (a) confirmation summary on stdout
  assert.match(output.stdout, /Configuration summary/);
  // (b) file was created
  assert.equal(existsSync(outputPath), true);
  // (c) file parses as JSON
  const fileContent = JSON.parse(readFileSync(outputPath, "utf8"));
  assert.ok(fileContent.mcpServers ?? fileContent.servers);
  // Raw token must NOT appear in stdout (write path sends token to file, not stdout)
  assert.equal(output.stdout.includes("wiz-write-token-9999"), false);
});

// ─── CLI-04 / CLI-05: Claude Desktop write-path tests ────────────────────────

test("claude remains a JSON client after Plan 02 (CLI-04 invariant)", () => {
  // CLI-05: ASSERT — do NOT silently restore. If this fails, 02-02 removed it incorrectly.
  assert.ok(
    JSON_MCP_CLIENTS.has("claude"),
    "claude must stay in JSON_MCP_CLIENTS; 02-02 removed it incorrectly — fix 02-02, do not patch here"
  );
});

test("clientConfigPath('claude') resolves to macOS claude_desktop_config.json path (CLI-04 location)", () => {
  const result = clientConfigPath("claude", { HOME: "/home/user" });
  assert.equal(
    result,
    "/home/user/Library/Application Support/Claude/claude_desktop_config.json"
  );
});

test("init --client claude --write writes valid mcpServers JSON with npx github:omilia/mcp run (CLI-04, CLI-05)", () => {
  const io = createIo();
  const directory = mkdtempSync(join(tmpdir(), "ocp-mcp-claude-"));
  const outputPath = join(directory, "claude_desktop_config.json");

  const exitCode = runCli([
    "init", "--client", "claude", "--write",
    "--path", outputPath,
    "--base-url", "https://ocp.example.com",
    "--access-token", "pat-desktop-1234"
  ], io);

  assert.equal(exitCode, 0);

  // File must exist and be readable
  const content = readFileSync(outputPath, "utf8");
  const parsed = JSON.parse(content);

  // mcpServers block must be present with the OCP key
  assert.ok(parsed.mcpServers, "written file must have mcpServers");
  assert.ok(parsed.mcpServers.OCP, "mcpServers must contain OCP");

  // CLI-05: command and args must use npx -y github:omilia/mcp run
  assert.equal(parsed.mcpServers.OCP.command, "npx");
  assert.deepEqual(parsed.mcpServers.OCP.args, ["-y", "github:omilia/mcp", "run"]);

  // env must carry the supplied base URL and token
  assert.equal(parsed.mcpServers.OCP.env.OCP_BASE_URL, "https://ocp.example.com");
  assert.equal(parsed.mcpServers.OCP.env.OCP_ACCESS_TOKEN, "pat-desktop-1234");

  // T-02-07: file mode must be 0o600
  const stat = statSync(outputPath);
  // On non-Windows platforms, verify mode bits; process.platform guard for CI portability
  if (process.platform !== "win32") {
    assert.equal(
      (stat.mode & 0o777).toString(8),
      "600",
      "claude_desktop_config.json must be written with mode 0o600"
    );
  }
});

// ─── CLI-04: .mcpb bundle manifest consistency test ───────────────────────────

test(".mcpb manifest.json env keys deep-equal PAT getEnvBlock keys and args end with 'run' (CLI-04 T-02-08)", () => {
  // Resolve manifest.json relative to this test file (repo root)
  const __filename = fileURLToPath(import.meta.url);
  const __dirname = dirname(__filename);
  const manifestPath = resolve(__dirname, "../manifest.json");
  const manifest = JSON.parse(readFileSync(manifestPath, "utf8"));

  const mcpConfig = manifest.server.mcp_config;

  // Args must end with "run"
  assert.equal(
    mcpConfig.args.at(-1),
    "run",
    "manifest mcp_config.args last element must be 'run'"
  );

  // Args must reference bin/ocp-mcp.js (bundle entry point)
  assert.ok(
    mcpConfig.args.some((a) => a.includes("bin/ocp-mcp.js")),
    "manifest mcp_config.args must contain the bin/ocp-mcp.js path"
  );

  // Env keys must deep-equal the PAT getEnvBlock keys (T-02-08 — locks env contract)
  const patEnvKeys = Object.keys(getEnvBlock("pat", { useEnvVars: true }));
  const manifestEnvKeys = Object.keys(mcpConfig.env);
  assert.deepEqual(
    manifestEnvKeys.sort(),
    patEnvKeys.sort(),
    "manifest mcp_config.env keys must exactly match the PAT getEnvBlock keys"
  );
});

test("wizard skips pre-supplied flag fields, prompts only for missing ones (WIZ-05 partial)", async () => {
  // Provide --client and --base-url; only --access-token is missing.
  // parseInitOptions defaults authChoice to "pat"; missingPromptFields only returns ["accessToken"].
  // Use --client claude (a JSON client) so finishInit emits the confirmation summary + config JSON.
  // (claude-code would route through installClaudeCode and not emit the JSON/summary the test asserts.)
  const { io, output } = createScriptedIo(["partial-access-token-5678"]);
  const result = await Promise.resolve(runCli([
    "init", "--client", "claude", "--base-url", "https://ocp.example.com"
  ], io));

  assert.equal(result, 0);
  // Confirmation summary present
  assert.match(output.stdout, /Configuration summary/);
  // Client CHOICE prompt must NOT appear (--client was pre-supplied).
  // askChoice always emits "Enter number or value:" — its absence proves askChoice did not run.
  assert.equal(output.stdout.includes("Enter number or value:"), false,
    "--client was supplied so askChoice for client must not run");
  // Only the "Access token: " prompt should appear before the confirmation summary —
  // the wizard prompts only for the single missing field (accessToken).
  // Check that the preamble (before "Configuration summary") contains exactly one
  // prompt marker (the "Access token: " label from askSecret).
  const summaryStart = output.stdout.indexOf("Configuration summary");
  const preamble = summaryStart >= 0 ? output.stdout.slice(0, summaryStart) : output.stdout;
  assert.match(preamble, /Access token:/);
  // Base URL askText prompt must NOT appear in the preamble (--base-url was pre-supplied).
  // askText emits "<label>: " — this substring would be in the preamble only if prompted.
  // (The summary section is excluded above, so we only see the prompt region.)
  assert.equal(preamble.includes("Base URL:"), false,
    "--base-url was supplied so askText for baseUrl must not run");
  // Raw token must NOT appear in the summary portion
  const summaryEnd = output.stdout.indexOf("{");
  const summaryPortion = summaryEnd >= 0 ? output.stdout.slice(0, summaryEnd) : output.stdout;
  assert.equal(summaryPortion.includes("partial-access-token-5678"), false);
});

// ─── Production-shape regression (process exposes stdin, NOT input) ───────────
// bin/ocp-mcp.js passes the real `process` to runCli. `process` has
// stdin/stdout/stderr — there is no `process.input`. The original runInit read
// `io.input`, so in production it was always undefined, the wizard never ran,
// and bare `init` errored with "Unsupported client: undefined". All prior tests
// injected `io.input`, masking the bug. This helper mirrors the REAL shape.
function createProcessShapedIo(answers, { isTty = true } = {}) {
  const outputCapture = { stderr: "", stdout: "" };
  const lines = answers.slice();
  const stdin = Readable.from(
    (async function* () {
      for (const line of lines) {
        yield line + "\n";
      }
    })()
  );
  stdin.isTTY = isTty; // real terminals set this; no setRawMode → askSecret uses muted readline
  return {
    io: {
      stdin,
      stderr: { write(value) { outputCapture.stderr += value; } },
      stdout: { write(value) { outputCapture.stdout += value; } }
    },
    output: outputCapture
  };
}

test("bare init triggers the wizard via process-shaped io (stdin, not input) (production-TTY regression)", async () => {
  // client "claude" (Desktop): default (no --write) prints the config — no file write, no spawn.
  // authChoice defaults to "pat", so the wizard prompts only: client, baseUrl, accessToken.
  // Pass choice VALUES (not indices) so the test is order-independent.
  const { io, output } = createProcessShapedIo([
    "claude",
    "https://ocp.example.com",
    "prod-shape-token-1234"
  ]);

  const code = await Promise.resolve(runCli(["init"], io));

  assert.equal(code, 0, "wizard path should complete with exit 0");
  // The wizard actually ran: client choices were presented.
  assert.match(output.stdout, /Claude Desktop|claude-code/, "wizard should have prompted for client");
  // It must NOT have fallen through to the unsupported-client error.
  assert.doesNotMatch(output.stderr, /Unsupported client/, "must not hit unsupported-client fallthrough");
  assert.doesNotMatch(output.stdout, /Unsupported client/);
});

test("--print with --client emits placeholders on process-shaped io and never prompts (manual-config regression)", async () => {
  // The documented "Manual config" method: `init --client <name> --print` must emit a
  // fill-in-the-blanks config snippet WITHOUT prompting or requiring base-url/token —
  // even on a real process-shaped io where io.stdin exists. (Regression: the io.stdin
  // fallback once made the no-TTY guard fire here and error instead of printing.)
  const { io, output } = createProcessShapedIo([], { isTty: false });

  const code = await Promise.resolve(runCli(["init", "--client", "cursor", "--print"], io));

  assert.equal(code, 0, "--print should emit placeholders and exit 0");
  assert.doesNotMatch(output.stderr, /missing required options|Unsupported client/i, "must not error");
  const cfg = JSON.parse(output.stdout);
  assert.equal(cfg.mcpServers.OCP.env.OCP_BASE_URL, "your-ocp-base-url", "emits base-url placeholder");
  assert.equal(cfg.mcpServers.OCP.env.OCP_ACCESS_TOKEN, "your-ocp-access-token", "emits token placeholder");
});
