import assert from "node:assert/strict";
import test from "node:test";

import {
  buildClaudeMcpAddArgs,
  claudeAvailable,
  installClaudeCode
} from "../lib/install.js";

// ─── Fake spawn factory ───────────────────────────────────────────────────────

/**
 * makeSpawn(status) — returns a fake spawnSync-like function that records
 * { cmd, args } into a closure array and returns { status }.
 */
function makeSpawn(status) {
  const recorded = [];
  const spawn = (cmd, args) => {
    recorded.push({ cmd, args });
    return { status };
  };
  spawn.recorded = recorded;
  return spawn;
}

/**
 * enoentSpawn — throws an ENOENT-shaped error, simulating a missing executable.
 */
function enoentSpawn(_cmd, _args) {
  const err = new Error("spawn claude ENOENT");
  err.code = "ENOENT";
  throw err;
}

// ─── Test io helper ───────────────────────────────────────────────────────────

function createIo() {
  const output = { stderr: "", stdout: "" };
  return {
    output,
    stderr: { write(v) { output.stderr += v; } },
    stdout: { write(v) { output.stdout += v; } }
  };
}

// ─── buildClaudeMcpAddArgs — PAT ──────────────────────────────────────────────

test("buildClaudeMcpAddArgs PAT: returns expected argv array", () => {
  const opts = {
    authChoice: "pat",
    baseUrl: "https://ocp.example.com",
    accessToken: "pat-token-1234"
  };
  const argv = buildClaudeMcpAddArgs(opts);

  assert.deepEqual(argv, [
    "mcp", "add", "OCP", "--scope", "user",
    "--env", "OCP_BASE_URL=https://ocp.example.com",
    "--env", "OCP_ACCESS_TOKEN=pat-token-1234",
    "--", "npx", "-y", "github:omilia/mcp", "run"
  ]);
});

test("buildClaudeMcpAddArgs PAT: token is a single array element (never shell-interpolated)", () => {
  const opts = {
    authChoice: "pat",
    baseUrl: "https://ocp.example.com",
    accessToken: "super-secret; rm -rf /"
  };
  const argv = buildClaudeMcpAddArgs(opts);
  // The token must appear as exactly one element ending with the shell-hostile string
  const tokenElement = argv.find((el) => el.startsWith("OCP_ACCESS_TOKEN="));
  assert.ok(tokenElement, "must have OCP_ACCESS_TOKEN= element");
  assert.equal(tokenElement, "OCP_ACCESS_TOKEN=super-secret; rm -rf /",
    "dangerous chars stay inside a single array element");
});

test("buildClaudeMcpAddArgs PAT: --scope user present", () => {
  const argv = buildClaudeMcpAddArgs({ authChoice: "pat", baseUrl: "b", accessToken: "t" });
  const idx = argv.indexOf("--scope");
  assert.ok(idx >= 0, "--scope flag must be present");
  assert.equal(argv[idx + 1], "user");
});

test("buildClaudeMcpAddArgs PAT: ends with -- npx -y github:omilia/mcp run", () => {
  const argv = buildClaudeMcpAddArgs({ authChoice: "pat", baseUrl: "b", accessToken: "t" });
  const sepIdx = argv.indexOf("--");
  assert.ok(sepIdx >= 0, "-- separator must be present");
  assert.deepEqual(argv.slice(sepIdx), ["--", "npx", "-y", "github:omilia/mcp", "run"]);
});

test("buildClaudeMcpAddArgs PAT: custom server name used", () => {
  const argv = buildClaudeMcpAddArgs({ authChoice: "pat", serverName: "MYSERVER", baseUrl: "b", accessToken: "t" });
  assert.equal(argv[2], "MYSERVER");
});

// ─── buildClaudeMcpAddArgs — Keycloak ─────────────────────────────────────────

test("buildClaudeMcpAddArgs keycloak: has correct env pairs, no OCP_ACCESS_TOKEN", () => {
  const opts = {
    authChoice: "keycloak",
    baseUrl: "https://ocp.example.com",
    username: "alice",
    password: "wonderland",
    realm: "ocp"
  };
  const argv = buildClaudeMcpAddArgs(opts);

  // Must contain keycloak env pairs
  assert.ok(argv.includes("OCP_BASE_URL=https://ocp.example.com"), "must have OCP_BASE_URL");
  assert.ok(argv.includes("OCP_USERNAME=alice"), "must have OCP_USERNAME");
  assert.ok(argv.includes("OCP_PASSWORD=wonderland"), "must have OCP_PASSWORD");
  assert.ok(argv.includes("OCP_KEYCLOAK_REALM=ocp"), "must have OCP_KEYCLOAK_REALM");
  // Must NOT contain PAT token pair
  assert.ok(!argv.some((el) => el.startsWith("OCP_ACCESS_TOKEN=")),
    "must NOT have OCP_ACCESS_TOKEN for keycloak");
});

test("buildClaudeMcpAddArgs keycloak: full expected argv", () => {
  const opts = {
    authChoice: "keycloak",
    baseUrl: "https://ocp.example.com",
    username: "alice",
    password: "wonderland",
    realm: "ocp"
  };
  const argv = buildClaudeMcpAddArgs(opts);

  assert.deepEqual(argv, [
    "mcp", "add", "OCP", "--scope", "user",
    "--env", "OCP_BASE_URL=https://ocp.example.com",
    "--env", "OCP_USERNAME=alice",
    "--env", "OCP_PASSWORD=wonderland",
    "--env", "OCP_KEYCLOAK_REALM=ocp",
    "--", "npx", "-y", "github:omilia/mcp", "run"
  ]);
});

// ─── claudeAvailable ──────────────────────────────────────────────────────────

test("claudeAvailable returns true when spawn returns status 0", () => {
  const spawn = makeSpawn(0);
  assert.equal(claudeAvailable(spawn), true);
});

test("claudeAvailable returns false when spawn throws ENOENT", () => {
  assert.equal(claudeAvailable(enoentSpawn), false);
});

test("claudeAvailable returns false when spawn returns non-zero status", () => {
  const spawn = makeSpawn(1);
  assert.equal(claudeAvailable(spawn), false);
});

test("claudeAvailable returns false when spawn returns null status", () => {
  const spawn = (_cmd, _args) => ({ status: null });
  assert.equal(claudeAvailable(spawn), false);
});

test("claudeAvailable checks with --version arg", () => {
  const spawn = makeSpawn(0);
  claudeAvailable(spawn);
  assert.equal(spawn.recorded[0].cmd, "claude");
  assert.deepEqual(spawn.recorded[0].args, ["--version"]);
});

// ─── installClaudeCode — CLI present, normal install ─────────────────────────

test("installClaudeCode with available claude: records argv and returns 0", () => {
  const spawn = makeSpawn(0);
  const io = createIo();
  const opts = {
    authChoice: "pat",
    baseUrl: "https://ocp.example.com",
    accessToken: "pat-cc-1234"
  };

  const code = installClaudeCode(opts, io, { spawn });

  assert.equal(code, 0, "must return 0 on success");
  // The spawn recorded the --version check + the mcp add call
  const mcpCall = spawn.recorded.find((r) => r.args && r.args[0] === "mcp");
  assert.ok(mcpCall, "must have recorded the mcp add spawn");
  assert.equal(mcpCall.cmd, "claude");
  assert.deepEqual(mcpCall.args, buildClaudeMcpAddArgs(opts));
});

test("installClaudeCode with available claude: stdout contains success notice", () => {
  const spawn = makeSpawn(0);
  const io = createIo();
  const opts = { authChoice: "pat", baseUrl: "b", accessToken: "t" };

  installClaudeCode(opts, io, { spawn });

  assert.ok(io.output.stdout.length > 0, "must write a success notice to stdout");
});

test("installClaudeCode with failed claude (status 1): returns 1 and writes to stderr", () => {
  const spawn = makeSpawn(1);
  const io = createIo();
  const opts = { authChoice: "pat", baseUrl: "b", accessToken: "t" };

  // Make first spawn (version check) succeed, mcp add fail
  let callCount = 0;
  const mixedSpawn = (cmd, args) => {
    callCount += 1;
    if (callCount === 1) return { status: 0 }; // version check ok
    return { status: 1 }; // mcp add fails
  };

  const code = installClaudeCode(opts, io, { spawn: mixedSpawn });

  assert.equal(code, 1);
  assert.ok(io.output.stderr.length > 0, "must write error to stderr on non-zero exit");
});

// ─── installClaudeCode — CLI absent (CLI-03) ──────────────────────────────────

test("installClaudeCode CLI-absent path: returns 0 (graceful)", () => {
  const io = createIo();
  const opts = {
    authChoice: "pat",
    baseUrl: "https://ocp.example.com",
    accessToken: "pat-absent-9999"
  };

  const code = installClaudeCode(opts, io, { spawn: enoentSpawn });

  assert.equal(code, 0, "must return 0 when claude is absent (graceful guidance delivery)");
});

test("installClaudeCode CLI-absent path: writes guidance to stdout", () => {
  const io = createIo();
  const opts = {
    authChoice: "pat",
    baseUrl: "https://ocp.example.com",
    accessToken: "pat-absent-9999"
  };

  installClaudeCode(opts, io, { spawn: enoentSpawn });

  assert.ok(io.output.stdout.includes("mcp add"), "guidance must reference 'mcp add'");
});

test("installClaudeCode CLI-absent path: raw token absent from stdout (T-02-04)", () => {
  const io = createIo();
  const opts = {
    authChoice: "pat",
    baseUrl: "https://ocp.example.com",
    accessToken: "pat-absent-9999"
  };

  installClaudeCode(opts, io, { spawn: enoentSpawn });

  assert.ok(!io.output.stdout.includes("pat-absent-9999"),
    "raw token must NOT appear in stdout");
});

test("installClaudeCode CLI-absent path: masked tail present in stdout (T-02-04)", () => {
  const io = createIo();
  const opts = {
    authChoice: "pat",
    baseUrl: "https://ocp.example.com",
    accessToken: "pat-absent-9999"
  };

  installClaudeCode(opts, io, { spawn: enoentSpawn });

  // Last 4 chars of "pat-absent-9999" = "9999"
  assert.ok(io.output.stdout.includes("9999"),
    "masked tail (last 4 chars) must appear in stdout");
});

test("installClaudeCode CLI-absent path: does NOT throw", () => {
  const io = createIo();
  const opts = { authChoice: "pat", baseUrl: "b", accessToken: "t" };

  assert.doesNotThrow(() => installClaudeCode(opts, io, { spawn: enoentSpawn }));
});

// ─── installClaudeCode — print mode (CLI-01 / --print) ───────────────────────

test("installClaudeCode print mode: returns 0 without spawning", () => {
  const spawn = makeSpawn(0);
  const io = createIo();
  const opts = {
    print: true,
    authChoice: "pat",
    baseUrl: "https://ocp.example.com",
    accessToken: "pat-print-9999"
  };

  const code = installClaudeCode(opts, io, { spawn });

  assert.equal(code, 0, "print mode must return 0");
  // No spawn calls at all (not even --version check)
  assert.equal(spawn.recorded.length, 0, "print mode must NOT spawn any process");
});

test("installClaudeCode print mode: stdout contains 'mcp add'", () => {
  const spawn = makeSpawn(0);
  const io = createIo();
  const opts = {
    print: true,
    authChoice: "pat",
    baseUrl: "https://ocp.example.com",
    accessToken: "pat-print-9999"
  };

  installClaudeCode(opts, io, { spawn });

  assert.ok(io.output.stdout.includes("mcp add"), "print mode must include 'mcp add' in stdout");
});

test("installClaudeCode print mode: raw token absent from stdout (T-02-04)", () => {
  const spawn = makeSpawn(0);
  const io = createIo();
  const opts = {
    print: true,
    authChoice: "pat",
    baseUrl: "https://ocp.example.com",
    accessToken: "pat-print-9999"
  };

  installClaudeCode(opts, io, { spawn });

  assert.ok(!io.output.stdout.includes("pat-print-9999"),
    "raw token must NOT appear in print mode stdout");
});

test("installClaudeCode print mode: masked tail present in stdout (T-02-04)", () => {
  const spawn = makeSpawn(0);
  const io = createIo();
  const opts = {
    print: true,
    authChoice: "pat",
    baseUrl: "https://ocp.example.com",
    accessToken: "pat-print-9999"
  };

  installClaudeCode(opts, io, { spawn });

  // Last 4 chars of "pat-print-9999" = "9999"
  assert.ok(io.output.stdout.includes("9999"),
    "masked tail (last 4 chars) must appear in print mode stdout");
});
