import assert from "node:assert/strict";
import crypto from "node:crypto";
import { existsSync, mkdtempSync, readFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { Readable } from "node:stream";
import test from "node:test";

import { runCli } from "../lib/cli.js";
import { buildClientConfig, buildCursorConfig, clientConfigPath } from "../lib/config.js";
import { buildRunCommand } from "../lib/runtime.js";

// Regression gate: SHA-256 of `init --client claude --print` output
// with no --auth arg (defaults to PAT). Updating this value is a
// deliberate API change — it is the contract that PAT-only users see
// byte-identical output across releases. Update this constant only
// alongside an intentional change to the PAT-default emission.
const PAT_INIT_GOLDEN_SHA256 = "556844bc833b7eab9c565c70d990961c2357ec11da138b1f0ca9842b9a59284c";

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
        args: ["-y", "@omilia/mcp-server", "run"],
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

test("clientConfigPath resolves claude-code to ~/.claude/settings.json", () => {
  const result = clientConfigPath("claude-code", { HOME: "/home/user" });
  assert.equal(result, "/home/user/.claude/settings.json");
});

test("writes claude-code config to an explicit path", () => {
  const io = createIo();
  const directory = mkdtempSync(join(tmpdir(), "ocp-mcp-"));
  const outputPath = join(directory, "settings.json");
  const exitCode = runCli(["init", "--client", "claude-code", "--write", "--path", outputPath], io);

  assert.equal(exitCode, 0);
  assert.deepEqual(JSON.parse(readFileSync(outputPath, "utf8")), buildClientConfig("claude-code"));
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
  const io = createIo(); // no isTTY — io.input is undefined (falsy)
  const result = await Promise.resolve(runCli(["init"], io));

  assert.equal(result, 1);
  assert.match(io.output.stderr, /--client/);
  // Must NOT be the old parseInitOptions throw message
  assert.equal(io.output.stderr.includes("Missing required option: --client"), false);
});

test("interactive bare init reaches masked confirmation summary (WIZ-01, WIZ-04)", async () => {
  // Scripted answers: 1=claude-code, 1=pat, base-url, access-token
  const { io, output } = createScriptedIo(["1", "1", "https://ocp.example.com", "super-secret-token-1234"]);
  const result = await Promise.resolve(runCli(["init"], io));

  assert.equal(result, 0);
  // Confirmation summary must be present on stdout
  assert.match(output.stdout, /Configuration summary/);
  // Raw token must NOT appear in stdout (WIZ-04, T-01-07)
  assert.equal(output.stdout.includes("super-secret-token-1234"), false);
  // The masked tail should appear (last 4 of "super-secret-token-1234" = "1234")
  assert.match(output.stdout, /1234/);
});

test("fully-flagged --print returns config JSON only, no prompts (WIZ-05)", async () => {
  const io = createIo();
  const result = await Promise.resolve(runCli([
    "init", "--client", "claude-code",
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

test("wizard + --write: confirmation summary emitted before file write (WIZ-04 ordering)", async () => {
  const directory = mkdtempSync(join(tmpdir(), "ocp-mcp-wiz-"));
  const outputPath = join(directory, "config.json");

  // Scripted answers: 1=claude-code, 1=pat, base-url, access-token
  const { io, output } = createScriptedIo(["1", "1", "https://ocp.example.com", "wiz-write-token-9999"]);
  const result = await Promise.resolve(runCli(["init", "--write", "--path", outputPath], io));

  assert.equal(result, 0);
  // (a) confirmation summary on stdout
  assert.match(output.stdout, /Configuration summary/);
  // (b) file was created
  assert.equal(existsSync(outputPath), true);
  // (c) file parses as JSON
  const fileContent = JSON.parse(readFileSync(outputPath, "utf8"));
  assert.ok(fileContent.mcpServers ?? fileContent.servers);
  // Raw token must NOT appear in stdout
  assert.equal(output.stdout.includes("wiz-write-token-9999"), false);
});
