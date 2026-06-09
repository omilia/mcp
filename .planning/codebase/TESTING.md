# Testing Patterns

**Analysis Date:** 2026-06-09

## Test Framework

**Runner:**
- Node.js built-in test runner (`node:test`) — no external test framework installed
- Config: none (invoked directly via `node --test`)
- Node >= 20 required (`"engines": {"node": ">=20"}` in `package.json`)

**Assertion Library:**
- `node:assert/strict` — strict equality mode enforced throughout

**Run Commands:**
```bash
node --test              # Run all tests (finds *.test.js by convention)
```

No watch mode, no coverage command configured in `package.json`.

**Python tests:** No Python test framework detected (no `pytest`, `conftest.py`, `test_*.py` files). The Python layer (`src/`, `vendor/python/src/`) has no automated tests.

---

## Test File Organization

**Location:** Co-located in `test/` directory at repo root (not alongside source files).

**Naming:**
- `<subject>.test.js` pattern — `test/cli.test.js`

**Current test files:**
- `test/cli.test.js` — covers `lib/cli.js`, `lib/config.js`, `lib/runtime.js`

---

## Test Structure

**Suite organization:** Flat — no nested `describe` blocks. Each `test()` call is a top-level, self-contained case:

```javascript
import test from "node:test";
import assert from "node:assert/strict";

test("builds Cursor config with inline literal placeholders by default", () => {
  const config = buildCursorConfig();
  assert.deepEqual(config, { mcpServers: { OCP: { ... } } });
});
```

**No beforeEach/afterEach hooks.** Each test creates its own fixtures inline.

**Async tests:** Not present in current test suite. The test runner supports `async` test callbacks natively when needed.

---

## Mocking

**Framework:** None — no `sinon`, `jest.mock`, or similar.

**Patterns:**

**IO injection (primary isolation technique):** The CLI is designed for testability via an `io` parameter. Tests pass a captured object instead of `process`:

```javascript
function createIo() {
  const output = { stderr: "", stdout: "" };
  return {
    output,
    stderr: { write(value) { output.stderr += value; } },
    stdout: { write(value) { output.stdout += value; } }
  };
}

test("prints Cursor config by default", () => {
  const io = createIo();
  const exitCode = runCli(["init", "--client", "cursor"], io);
  assert.equal(exitCode, 0);
  assert.deepEqual(JSON.parse(io.output.stdout), buildCursorConfig());
});
```

**Spawn injection:** `runMcpServer` accepts an optional `spawn` parameter, enabling test-time replacement of `spawnSync` without monkey-patching.

**What to mock:**
- Pass `createIo()` for any test that calls `runCli` or `runMcpServer`
- Pass explicit `spawn` override when testing `runMcpServer` behavior without executing child processes

**What NOT to mock:**
- The config builder functions (`buildClientConfig`, `buildCursorConfig`) — these are pure and test directly
- File system in most cases — tests use real `mkdtempSync` temp dirs for write tests

---

## Fixtures and Factories

**Test data — `createIo()` factory:**
```javascript
function createIo() {
  const output = { stderr: "", stdout: "" };
  return {
    output,
    stderr: { write(value) { output.stderr += value; } },
    stdout: { write(value) { output.stdout += value; } }
  };
}
```

**Temp directories for write tests:**
```javascript
const directory = mkdtempSync(join(tmpdir(), "ocp-mcp-"));
const outputPath = join(directory, "mcp.json");
```

**Golden hash for byte-stability regression:**
```javascript
const PAT_INIT_GOLDEN_SHA256 = "556844bc...";
// Used in one test to verify PAT-default output is byte-identical across releases.
```

**Location:** All fixtures are inlined in `test/cli.test.js` — no shared fixture files.

---

## Coverage

**Requirements:** None enforced. No coverage tooling configured.

**View Coverage:** Not configured. Can be added with:
```bash
node --test --experimental-test-coverage
```

---

## Test Types

**Unit Tests:**
- Scope: pure function behavior (`buildClientConfig`, `buildCursorConfig`, `clientConfigPath`, `buildRunCommand`)
- Approach: call the function directly, assert return value with `assert.deepEqual` or `assert.equal`

**Integration/CLI Tests:**
- Scope: end-to-end CLI argument parsing through output emission
- Approach: `runCli(args, createIo())` — tests the full parse → build → serialize chain

**File System Tests:**
- Scope: config write behavior, conflict detection, force-overwrite
- Approach: real `mkdtempSync` temp dir, `readFileSync` to verify written content

**E2E Tests:** Not present — no tests that spawn the actual MCP server process or call the OCP API.

**Python Tests:** Not present — no test framework or test files exist for the Python layer (`src/`, `vendor/python/src/`).

---

## Common Patterns

**Exit code assertion (always check before stdout/stderr):**
```javascript
assert.equal(exitCode, 0);
assert.deepEqual(JSON.parse(io.output.stdout), expectedConfig);
```

**Error path testing:**
```javascript
test("rejects unsupported clients", () => {
  const io = createIo();
  const exitCode = runCli(["init", "--client", "gemini"], io);

  assert.equal(exitCode, 1);
  assert.equal(io.output.stdout, "");
  assert.match(io.output.stderr, /Unsupported client: gemini/);
});
```

**Regex matching for error messages:**
```javascript
assert.match(io.output.stderr, /--use-env-vars cannot be combined/);
assert.match(io.output.stderr, /Re-run with --force/);
```

**Throws testing (for non-CLI code):**
```javascript
assert.throws(
  () => buildRunCommand({ entrypoint: "bogus" }),
  /Unsupported entrypoint/
);
```

**Security / non-leakage assertions:**
```javascript
assert.equal(io.output.stdout.includes("Bearer "), false);
assert.equal(io.output.stdout.includes("sk-"), false);
assert.equal(io.output.stdout.includes("your-ocp-access-token"), true);
```

**Golden SHA-256 regression gate:**
```javascript
const actualSha = crypto.createHash("sha256").update(io.output.stdout).digest("hex");
assert.equal(actualSha, PAT_INIT_GOLDEN_SHA256, "PAT-default output changed; ...");
```
Used for `test/cli.test.js` line 214 — guards byte-identical output contract for Claude PAT init.

---

## Gaps

- No Python tests — `src/` and `vendor/python/src/` have zero automated coverage
- No watch mode configured
- No coverage reporting configured
- No integration tests for actual MCP protocol messages
- `tool_decorators.py` (`ToolWrapper`) has no unit tests despite being a critical callback dispatch layer

---

*Testing analysis: 2026-06-09*
