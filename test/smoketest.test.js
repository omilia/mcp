import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import test from "node:test";

import { smokeTest } from "../lib/smoketest.js";

// ─── Fake transport factory ───────────────────────────────────────────────────

/**
 * makeFakeTransport(script) — builds an injectable transport adapter.
 *
 * script: Map<id, resultObject>
 *   - key 1 => initialize result payload
 *   - key 2 => tools/list result payload
 *   - omit a key to make the transport silent (timeout simulation)
 *
 * Exposes:
 *   transport.send(jsonRpcObject)  — called by smoketest handshake
 *   transport.kill()               — called by smoketest teardown
 *   transport.killCount            — number of kill() invocations
 *
 * The transport emits responses via an EventEmitter-style 'line' event on
 * transport.stdout — smoketest reads lines via createInterface({ input: transport.stdout }).
 */
function makeFakeTransport(script = {}) {
  let lineListener = null;
  let killCount = 0;

  // Fake stdout: readline createInterface reads from this via 'line' event or async iteration.
  // We implement a minimal EventEmitter interface.
  const fakeStdout = {
    _listeners: {},
    on(event, fn) {
      this._listeners[event] = this._listeners[event] || [];
      this._listeners[event].push(fn);
      return this;
    },
    emit(event, data) {
      const fns = this._listeners[event] || [];
      for (const fn of fns) fn(data);
    },
    // readline also reads from the 'data' event or pipe — we support both via 'line' injection.
    // For node:readline createInterface we need a proper readable stream or we inject lines directly.
    // We use a passthrough: smoketest calls createInterface({input: child.stdout}); our
    // fake stdout must be a readable stream. Simplest approach: store the listener and fire lines
    // when send() triggers a scripted response.
    removeListener() { return this; },
    removeAllListeners() { return this; }
  };

  const fakeStdin = {
    write(data) {
      // Parse the request and trigger the scripted response (if any).
      let req;
      try { req = JSON.parse(data); } catch { return; }

      if (req.id !== undefined && script[req.id] !== undefined) {
        // Emit the scripted response after a microtask to simulate async.
        const response = JSON.stringify({
          jsonrpc: "2.0",
          id: req.id,
          result: script[req.id]
        }) + "\n";
        setImmediate(() => {
          if (lineListener) lineListener(response.trimEnd());
        });
      }
      // If no id (notification), do nothing.
    },
    end() {}
  };

  // Create a readable-stream-like object that readline can consume.
  // We intercept by wrapping the readline 'line' registration.
  const transport = {
    stdout: fakeStdout,
    stdin: fakeStdin,
    stderr: {
      on() { return this; }
    },
    kill() {
      killCount++;
    },
    on(event, fn) {
      // Child process 'error' and 'close' events.
      return this;
    },
    get killCount() { return killCount; },
    // Hook so smoketest's createInterface can register the line listener.
    _setLineListener(fn) { lineListener = fn; }
  };

  return transport;
}

/**
 * makeTransportDeps(script, extra) — builds deps object for smokeTest injection.
 *
 * Instead of injecting a child-process-like transport directly (which would
 * require duplicating the readline setup), we inject a custom spawn function
 * that returns the fake transport as the child object, AND inject a custom
 * readline createInterface that wires up the fake stdout's line listener.
 *
 * This keeps the smoketest's internal structure (spawn + createInterface) while
 * avoiding any real process launch.
 */
function makeTransportDeps(script = {}, extra = {}) {
  const transport = makeFakeTransport(script);

  const fakeSpawn = (_cmd, _args, _opts) => transport;

  const fakeCreateInterface = ({ input }) => {
    // Wire our line listener.
    const iface = {
      _handlers: {},
      on(event, fn) {
        if (event === "line") {
          transport._setLineListener(fn);
        }
        this._handlers[event] = fn;
        return this;
      },
      close() {}
    };
    return iface;
  };

  const fakeBuildRunCommand = () => ({
    command: "fake-uv",
    args: ["run", "--project", "/fake", "fastmcp", "run", "/fake/src/server.py:mcp"],
    env: { ...process.env, ...extra.extraEnv }
  });

  return { transport, fakeSpawn, fakeCreateInterface, fakeBuildRunCommand };
}

// ─── Happy path ───────────────────────────────────────────────────────────────

test("smokeTest happy path: tools include read_guide => ok:true, correct toolCount, hasReadGuide", async () => {
  const { fakeSpawn, fakeCreateInterface, fakeBuildRunCommand } = makeTransportDeps({
    1: { // initialize result
      protocolVersion: "2024-11-05",
      capabilities: {},
      serverInfo: { name: "ocp-server", version: "1.0.0" }
    },
    2: { // tools/list result
      tools: [
        { name: "read_guide" },
        { name: "search_guide" }
      ]
    }
  });

  const result = await smokeTest({
    spawn: fakeSpawn,
    createInterface: fakeCreateInterface,
    buildRunCommand: fakeBuildRunCommand
  });

  assert.equal(result.ok, true, "result.ok must be true for non-empty tools");
  assert.equal(result.toolCount, 2, "toolCount must equal the number of tools returned");
  assert.equal(result.hasReadGuide, true, "hasReadGuide must be true when read_guide is present");
});

// ─── Empty tools ──────────────────────────────────────────────────────────────

test("smokeTest empty tools: ok:false, reason mentions 'no tools'", async () => {
  const { fakeSpawn, fakeCreateInterface, fakeBuildRunCommand } = makeTransportDeps({
    1: {
      protocolVersion: "2024-11-05",
      capabilities: {},
      serverInfo: { name: "ocp-server", version: "1.0.0" }
    },
    2: { tools: [] }
  });

  const result = await smokeTest({
    spawn: fakeSpawn,
    createInterface: fakeCreateInterface,
    buildRunCommand: fakeBuildRunCommand
  });

  assert.equal(result.ok, false, "result.ok must be false for empty tools");
  assert.ok(
    result.reason && result.reason.toLowerCase().includes("no tools"),
    `reason must mention 'no tools' — got: ${result.reason}`
  );
});

// ─── Timeout ──────────────────────────────────────────────────────────────────

test("smokeTest timeout: ok:false, reason mentions 'timed out', kill invoked once", async () => {
  // Script has no responses — transport never replies.
  const { fakeSpawn, fakeCreateInterface, fakeBuildRunCommand, transport } = makeTransportDeps({});

  const result = await smokeTest({
    spawn: fakeSpawn,
    createInterface: fakeCreateInterface,
    buildRunCommand: fakeBuildRunCommand,
    timeoutMs: 50
  });

  assert.equal(result.ok, false, "result.ok must be false on timeout");
  assert.ok(
    result.reason && result.reason.toLowerCase().includes("timed out"),
    `reason must mention 'timed out' — got: ${result.reason}`
  );
  assert.equal(transport.killCount, 1, "kill must be invoked exactly once on timeout");
});

// ─── Kill invoked on success ──────────────────────────────────────────────────

test("smokeTest: kill invoked on success (teardown)", async () => {
  const { fakeSpawn, fakeCreateInterface, fakeBuildRunCommand, transport } = makeTransportDeps({
    1: {
      protocolVersion: "2024-11-05",
      capabilities: {},
      serverInfo: { name: "ocp-server", version: "1.0.0" }
    },
    2: { tools: [{ name: "read_guide" }] }
  });

  await smokeTest({
    spawn: fakeSpawn,
    createInterface: fakeCreateInterface,
    buildRunCommand: fakeBuildRunCommand
  });

  assert.equal(transport.killCount, 1, "kill must be invoked exactly once on success");
});

// ─── Kill invoked on empty tools ─────────────────────────────────────────────

test("smokeTest: kill invoked on empty-tools failure (teardown)", async () => {
  const { fakeSpawn, fakeCreateInterface, fakeBuildRunCommand, transport } = makeTransportDeps({
    1: {
      protocolVersion: "2024-11-05",
      capabilities: {},
      serverInfo: { name: "ocp-server", version: "1.0.0" }
    },
    2: { tools: [] }
  });

  await smokeTest({
    spawn: fakeSpawn,
    createInterface: fakeCreateInterface,
    buildRunCommand: fakeBuildRunCommand
  });

  assert.equal(transport.killCount, 1, "kill must be invoked exactly once on empty-tools failure");
});

// ─── No-leak (VER-03) ─────────────────────────────────────────────────────────

test("VER-03 no-leak: planted OCP_ACCESS_TOKEN never appears in JSON.stringify(result)", async () => {
  const PLANTED_TOKEN = "leak-tok-9999";

  const fakeBuildRunCommandWithToken = () => ({
    command: "fake-uv",
    args: ["run"],
    env: { ...process.env, OCP_ACCESS_TOKEN: PLANTED_TOKEN }
  });

  const { fakeSpawn, fakeCreateInterface } = makeTransportDeps({
    1: {
      protocolVersion: "2024-11-05",
      capabilities: {},
      serverInfo: { name: "ocp-server", version: "1.0.0" }
    },
    2: { tools: [{ name: "read_guide" }] }
  });

  const result = await smokeTest({
    spawn: fakeSpawn,
    createInterface: fakeCreateInterface,
    buildRunCommand: fakeBuildRunCommandWithToken
  });

  const serialized = JSON.stringify(result);
  assert.ok(
    !serialized.includes(PLANTED_TOKEN),
    `planted token "${PLANTED_TOKEN}" must NOT appear in JSON.stringify(result) — got: ${serialized}`
  );
});

// ─── Does not throw ───────────────────────────────────────────────────────────

test("smokeTest does not throw on timeout", async () => {
  const { fakeSpawn, fakeCreateInterface, fakeBuildRunCommand } = makeTransportDeps({});

  await assert.doesNotReject(
    () => smokeTest({
      spawn: fakeSpawn,
      createInterface: fakeCreateInterface,
      buildRunCommand: fakeBuildRunCommand,
      timeoutMs: 50
    }),
    "smokeTest must resolve (not reject) on timeout"
  );
});

test("smokeTest does not throw on empty tools", async () => {
  const { fakeSpawn, fakeCreateInterface, fakeBuildRunCommand } = makeTransportDeps({
    1: {
      protocolVersion: "2024-11-05",
      capabilities: {},
      serverInfo: { name: "ocp-server", version: "1.0.0" }
    },
    2: { tools: [] }
  });

  await assert.doesNotReject(
    () => smokeTest({
      spawn: fakeSpawn,
      createInterface: fakeCreateInterface,
      buildRunCommand: fakeBuildRunCommand
    }),
    "smokeTest must resolve (not reject) on empty tools"
  );
});

// ─── hasReadGuide false when read_guide absent ────────────────────────────────

test("smokeTest: hasReadGuide false when read_guide not in tools", async () => {
  const { fakeSpawn, fakeCreateInterface, fakeBuildRunCommand } = makeTransportDeps({
    1: {
      protocolVersion: "2024-11-05",
      capabilities: {},
      serverInfo: { name: "ocp-server", version: "1.0.0" }
    },
    2: { tools: [{ name: "other_tool" }] }
  });

  const result = await smokeTest({
    spawn: fakeSpawn,
    createInterface: fakeCreateInterface,
    buildRunCommand: fakeBuildRunCommand
  });

  assert.equal(result.ok, true);
  assert.equal(result.hasReadGuide, false, "hasReadGuide must be false when read_guide absent");
});

// ─── Spawn error (ENOENT) ─────────────────────────────────────────────────────

test("smokeTest spawn error (ENOENT): ok:false, reason mentions failed to start, does not throw", async () => {
  const fakeSpawnEnoent = (_cmd, _args, _opts) => {
    // Return a child that immediately emits an error.
    const child = {
      stdout: {
        _listeners: {},
        on(event, fn) { this._listeners[event] = fn; return this; },
        removeListener() { return this; },
        removeAllListeners() { return this; }
      },
      stdin: { write() {}, end() {} },
      stderr: { on() { return this; } },
      kill() {},
      on(event, fn) {
        if (event === "error") {
          const err = new Error("spawn fake-uv ENOENT");
          err.code = "ENOENT";
          setImmediate(() => fn(err));
        }
        return this;
      }
    };
    return child;
  };

  const fakeBuildRunCommand = () => ({
    command: "fake-uv",
    args: [],
    env: {}
  });

  const fakeCreateInterface = () => ({
    on() { return this; },
    close() {}
  });

  const result = await smokeTest({
    spawn: fakeSpawnEnoent,
    createInterface: fakeCreateInterface,
    buildRunCommand: fakeBuildRunCommand
  });

  assert.equal(result.ok, false, "result.ok must be false on spawn error");
  assert.ok(
    result.reason && result.reason.toLowerCase().includes("failed to start"),
    `reason must mention 'failed to start' — got: ${result.reason}`
  );
});

// ─── Guarded integration test (real uv) ──────────────────────────────────────

{
  let uvAvailable = false;
  try {
    const r = spawnSync("uv", ["--version"]);
    uvAvailable = r.status === 0;
  } catch {
    uvAvailable = false;
  }

  test(
    "integration: real smokeTest with actual uv server returns ok:true and hasReadGuide",
    { skip: uvAvailable ? false : "uv not on PATH" },
    async () => {
      const result = await smokeTest({ timeoutMs: 60000 });
      assert.equal(result.ok, true, `expected ok:true from real server — got: ${JSON.stringify(result)}`);
      assert.equal(result.hasReadGuide, true, "expected hasReadGuide:true from real server");
    }
  );
}
