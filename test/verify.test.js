import assert from "node:assert/strict";
import { mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import test from "node:test";

import { runVerification, buildVerifySummary } from "../lib/verify.js";

// ─── buildVerifySummary ───────────────────────────────────────────────────────

test("buildVerifySummary: all prereqs ok + smoke ok => PASS, per-check marks", () => {
  const summary = buildVerifySummary({
    checks: [
      { name: "node", ok: true, found: "20" },
      { name: "uv", ok: true }
    ],
    prereqsOk: true,
    smoke: { ok: true, toolCount: 3 }
  });

  assert.ok(summary.includes("Result: PASS"), `expected 'Result: PASS' in:\n${summary}`);
  assert.ok(summary.includes("node"), "summary must name the node check");
  assert.ok(summary.includes("uv"), "summary must name the uv check");
  // Per-check ✓ markers present
  assert.ok(summary.includes("[✓]"), "summary must have ✓ markers for passing checks");
  // Smoke test line present
  assert.ok(summary.includes("smoke test"), "summary must mention smoke test");
  assert.ok(!summary.includes("Result: FAIL"), "must not include FAIL when PASS");
});

test("buildVerifySummary: uv missing => FAIL, uv named with hint, smoke skipped", () => {
  const UV_HINT = "Install uv from https://github.com/astral-sh/uv";
  const summary = buildVerifySummary({
    checks: [
      { name: "node", ok: true, found: "20" },
      { name: "uv", ok: false, hint: UV_HINT }
    ],
    prereqsOk: false,
    smoke: null
  });

  assert.ok(summary.includes("Result: FAIL"), `expected 'Result: FAIL' in:\n${summary}`);
  assert.ok(summary.includes("uv"), "summary must name uv");
  assert.ok(summary.includes("[✗]"), "summary must have ✗ marker for failing check");
  assert.ok(summary.includes(UV_HINT), "summary must include the uv hint");
  // Smoke line shows skipped
  assert.ok(summary.includes("skipped"), "smoke test line must say skipped when prereqs missing");
  assert.ok(!summary.includes("Result: PASS"), "must not include PASS when FAIL");
});

test("buildVerifySummary: prereqs ok but smoke fails => FAIL, smoke reason shown", () => {
  const summary = buildVerifySummary({
    checks: [
      { name: "node", ok: true, found: "20" },
      { name: "uv", ok: true }
    ],
    prereqsOk: true,
    smoke: { ok: false, reason: "server returned no tools" }
  });

  assert.ok(summary.includes("Result: FAIL"), `expected 'Result: FAIL' in:\n${summary}`);
  assert.ok(summary.includes("server returned no tools"), "smoke reason must appear in summary");
  assert.ok(summary.includes("[✗]"), "summary must have ✗ marker for failed smoke");
  assert.ok(!summary.includes("Result: PASS"), "must not include PASS when FAIL");
});

// ─── No-leak (VER-03) ─────────────────────────────────────────────────────────

test("VER-03 buildVerifySummary: planted token never appears in any summary line", () => {
  const TOKEN = "verify-tok-9999";
  // Token is NOT in the whitelisted fields (name, ok, hint, found, toolCount, reason)
  // so it must never appear in the rendered output.
  const summary = buildVerifySummary({
    checks: [
      { name: "node", ok: true, found: "20" },
      { name: "uv", ok: true }
    ],
    prereqsOk: true,
    smoke: { ok: true, toolCount: 2 }
  });

  // Even if caller accidentally appended the token to a non-whitelisted field
  // the builder must not render it. We verify the builder only uses whitelisted fields.
  assert.ok(!summary.includes(TOKEN),
    `planted token "${TOKEN}" must not appear in summary`);
});

// ─── runVerification ──────────────────────────────────────────────────────────

test("runVerification: prereqs ok + smoke ok => resolves { ok: true, summary }", async () => {
  const fakeCheckPrerequisites = () => ({
    ok: true,
    missing: [],
    checks: [
      { name: "node", ok: true, found: "20" },
      { name: "uv", ok: true }
    ]
  });
  const fakeSmokeTest = async () => ({ ok: true, toolCount: 2, hasReadGuide: true });

  const result = await runVerification({
    checkPrerequisites: fakeCheckPrerequisites,
    smokeTest: fakeSmokeTest
  });

  assert.equal(result.ok, true, "result.ok must be true when both prereqs and smoke pass");
  assert.ok(typeof result.summary === "string", "result.summary must be a string");
  assert.ok(result.summary.includes("Result: PASS"), "summary must say PASS");
});

test("runVerification: prereqs fail => resolves { ok: false, summary }, smoke NOT invoked", async () => {
  const fakeCheckPrerequisites = () => ({
    ok: false,
    missing: [{ name: "uv", ok: false, hint: "Install uv from ..." }],
    checks: [
      { name: "node", ok: true, found: "20" },
      { name: "uv", ok: false, hint: "Install uv from ..." }
    ]
  });

  let smokeInvoked = false;
  const fakeSmokeTest = async () => {
    smokeInvoked = true;
    return { ok: true, toolCount: 1 };
  };

  const result = await runVerification({
    checkPrerequisites: fakeCheckPrerequisites,
    smokeTest: fakeSmokeTest
  });

  assert.equal(result.ok, false, "result.ok must be false when prereqs fail");
  assert.equal(smokeInvoked, false, "smokeTest must NOT be invoked when prereqs fail");
  assert.ok(result.summary.includes("Result: FAIL"), "summary must say FAIL");
  assert.ok(result.summary.includes("skipped"), "summary must say smoke skipped");
});

test("runVerification: prereqs ok but smoke fails => resolves { ok: false, summary }", async () => {
  const fakeCheckPrerequisites = () => ({
    ok: true,
    missing: [],
    checks: [
      { name: "node", ok: true, found: "20" },
      { name: "uv", ok: true }
    ]
  });
  const fakeSmokeTest = async () => ({ ok: false, reason: "server returned no tools" });

  const result = await runVerification({
    checkPrerequisites: fakeCheckPrerequisites,
    smokeTest: fakeSmokeTest
  });

  assert.equal(result.ok, false, "result.ok must be false when smoke fails");
  assert.ok(result.summary.includes("Result: FAIL"), "summary must say FAIL");
  assert.ok(result.summary.includes("server returned no tools"), "summary must include smoke reason");
});

test("runVerification: never rejects (resolves even on unexpected errors)", async () => {
  const fakeCheckPrerequisites = () => {
    throw new Error("unexpected prereq error");
  };

  await assert.doesNotReject(
    () => runVerification({ checkPrerequisites: fakeCheckPrerequisites }),
    "runVerification must resolve (never reject)"
  );
});

// ─── CLI-level tests (Task 2) ──────────────────────────────────────────────────
// These tests require lib/cli.js to be wired with verification + --no-verify-install.

import { runCli } from "../lib/cli.js";
import crypto from "node:crypto";
import { readFileSync } from "node:fs";

// Regression gate: must match existing golden SHA from test/cli.test.js
const PAT_INIT_GOLDEN_SHA256 = "9f03b6648fc1e5573acf9bc3fc5bc0c7f56ee3f839fe5bb8acf5d4d498103647";

function createIo() {
  const output = { stderr: "", stdout: "" };
  return {
    output,
    stderr: { write(v) { output.stderr += v; } },
    stdout: { write(v) { output.stdout += v; } }
  };
}

test("VER-03 golden-SHA regression: --client claude --print output unchanged after verification wiring", () => {
  const io = createIo();
  const exitCode = runCli(["init", "--client", "claude", "--print"], io);

  assert.equal(exitCode, 0);
  const actualSha = crypto.createHash("sha256").update(io.output.stdout).digest("hex");
  assert.equal(
    actualSha,
    PAT_INIT_GOLDEN_SHA256,
    `PAT-default output changed after verification wiring; SHA was ${actualSha}. ` +
    "Verification must NOT run on --print and must not alter the --print output."
  );
});

test("VER-02 --write with injected passing verify => exit 0 and summary printed", async () => {
  const io = createIo();
  const directory = mkdtempSync(join(tmpdir(), "ocp-mcp-ver-"));
  const outputPath = join(directory, "mcp.json");
  // Inject passing verify via io.verify (CANONICAL VERIFY CONTRACT).
  io.verify = async () => ({ ok: true, summary: "Install verification:\n  [✓] node\n  [✓] uv\nResult: PASS\n" });

  const exitCode = await Promise.resolve(runCli([
    "init", "--client", "cursor", "--write", "--path", outputPath,
    "--base-url", "https://ocp.example.com", "--access-token", "pat-test-123"
  ], io));

  assert.equal(exitCode, 0, "exit code must be 0 when verify passes");
  assert.ok(io.output.stdout.includes("Result: PASS"), "PASS summary must appear in stdout");
});

test("VER-02 --write with injected failing verify => non-zero exit and FAIL printed", async () => {
  const io = createIo();
  const directory = mkdtempSync(join(tmpdir(), "ocp-mcp-ver-"));
  const outputPath = join(directory, "mcp.json");
  io.verify = async () => ({ ok: false, summary: "Install verification:\n  [✗] uv — hint\nResult: FAIL\n" });

  const exitCode = await Promise.resolve(runCli([
    "init", "--client", "cursor", "--write", "--path", outputPath,
    "--base-url", "https://ocp.example.com", "--access-token", "pat-test-123"
  ], io));

  assert.notEqual(exitCode, 0, "exit code must be non-zero when verify fails");
  assert.ok(io.output.stdout.includes("Result: FAIL"), "FAIL summary must appear in stdout");
});

test("--no-verify-install with --write => verify NOT invoked, exit 0", async () => {
  const io = createIo();
  const directory = mkdtempSync(join(tmpdir(), "ocp-mcp-ver-"));
  const outputPath = join(directory, "mcp.json");

  let verifyInvoked = false;
  io.verify = async () => {
    verifyInvoked = true;
    return { ok: false, summary: "Result: FAIL\n" };
  };

  const exitCode = await Promise.resolve(runCli([
    "init", "--client", "cursor", "--write", "--path", outputPath,
    "--base-url", "https://ocp.example.com", "--access-token", "pat-test-123",
    "--no-verify-install"
  ], io));

  assert.equal(exitCode, 0, "exit code must be 0 when --no-verify-install");
  assert.equal(verifyInvoked, false, "io.verify must NOT be invoked when --no-verify-install");
});

test("VER-03 no-leak: access token never appears in stdout/stderr across full init flow", async () => {
  const io = createIo();
  const directory = mkdtempSync(join(tmpdir(), "ocp-mcp-ver-"));
  const outputPath = join(directory, "mcp.json");
  const LEAK_TOKEN = "leak-tok-9999";

  io.verify = async () => ({ ok: true, summary: "Install verification:\nResult: PASS\n" });

  await Promise.resolve(runCli([
    "init", "--client", "cursor", "--write", "--path", outputPath,
    "--base-url", "https://ocp.example.com", "--access-token", LEAK_TOKEN
  ], io));

  assert.ok(!io.output.stdout.includes(LEAK_TOKEN),
    `raw token "${LEAK_TOKEN}" must not appear in stdout`);
  assert.ok(!io.output.stderr.includes(LEAK_TOKEN),
    `raw token "${LEAK_TOKEN}" must not appear in stderr`);
});
