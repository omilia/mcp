import assert from "node:assert/strict";
import test from "node:test";

import {
  checkNode,
  checkUv,
  checkPrerequisites
} from "../lib/preflight.js";

// ─── Fake spawn factory (mirrors test/install.test.js idiom) ─────────────────

/**
 * makeVersionSpawn(map) — returns a fake spawnSync-like function keyed by cmd.
 *
 * Each key in `map` is a command name (e.g. "node", "uv").
 * Each value is either:
 *   - An object { status, stdout } — returned directly
 *   - The string "ENOENT" — makes the fake throw an ENOENT-coded error
 *
 * Commands not in the map return { status: 1, stdout: "" }.
 */
function makeVersionSpawn(map) {
  return function fakeSpawn(cmd, _args, _opts) {
    const entry = map[cmd];
    if (entry === "ENOENT") {
      const err = new Error(`spawn ${cmd} ENOENT`);
      err.code = "ENOENT";
      throw err;
    }
    if (entry) return { status: entry.status, stdout: entry.stdout ?? "" };
    return { status: 1, stdout: "" };
  };
}

// ─── checkNode ────────────────────────────────────────────────────────────────

test("checkNode: node present and >= 20 returns ok:true", () => {
  const spawn = makeVersionSpawn({ node: { status: 0, stdout: "v20.11.1\n" } });
  const result = checkNode({ spawn });
  assert.equal(result.name, "node");
  assert.equal(result.ok, true);
});

test("checkNode: node present but < 20 returns ok:false with found and hint", () => {
  const spawn = makeVersionSpawn({ node: { status: 0, stdout: "v18.20.0\n" } });
  const result = checkNode({ spawn });
  assert.equal(result.name, "node");
  assert.equal(result.ok, false);
  assert.equal(result.found, "18");
  assert.ok(result.hint.includes("https://nodejs.org"), "hint must include nodejs.org URL");
});

test("checkNode: ENOENT returns ok:false with found:null and hint", () => {
  const spawn = makeVersionSpawn({ node: "ENOENT" });
  const result = checkNode({ spawn });
  assert.equal(result.name, "node");
  assert.equal(result.ok, false);
  assert.equal(result.found, null);
  assert.ok(result.hint.includes("https://nodejs.org"), "hint must include nodejs.org URL");
});

test("checkNode: non-zero spawn status returns ok:false", () => {
  const spawn = makeVersionSpawn({ node: { status: 1, stdout: "" } });
  const result = checkNode({ spawn });
  assert.equal(result.name, "node");
  assert.equal(result.ok, false);
});

test("checkNode: unparseable version stdout treated as ok:false with found:null", () => {
  const spawn = makeVersionSpawn({ node: { status: 0, stdout: "not-a-version\n" } });
  const result = checkNode({ spawn });
  assert.equal(result.name, "node");
  assert.equal(result.ok, false);
  assert.equal(result.found, null);
});

test("checkNode: node 21 returns ok:true", () => {
  const spawn = makeVersionSpawn({ node: { status: 0, stdout: "v21.0.0\n" } });
  const result = checkNode({ spawn });
  assert.equal(result.ok, true);
});

// ─── checkUv ──────────────────────────────────────────────────────────────────

test("checkUv: uv present returns ok:true", () => {
  const spawn = makeVersionSpawn({ uv: { status: 0, stdout: "uv 0.5.1\n" } });
  const result = checkUv({ spawn });
  assert.equal(result.name, "uv");
  assert.equal(result.ok, true);
});

test("checkUv: ENOENT returns ok:false with hint", () => {
  const spawn = makeVersionSpawn({ uv: "ENOENT" });
  const result = checkUv({ spawn });
  assert.equal(result.name, "uv");
  assert.equal(result.ok, false);
  assert.ok(result.hint.includes("https://github.com/astral-sh/uv"),
    "hint must include uv GitHub URL");
});

test("checkUv: non-zero status returns ok:false", () => {
  const spawn = makeVersionSpawn({ uv: { status: 1, stdout: "" } });
  const result = checkUv({ spawn });
  assert.equal(result.name, "uv");
  assert.equal(result.ok, false);
});

// ─── checkPrerequisites ───────────────────────────────────────────────────────

test("checkPrerequisites: both ok returns { ok: true, missing: [] }", () => {
  const spawn = makeVersionSpawn({
    node: { status: 0, stdout: "v20.11.1\n" },
    uv: { status: 0, stdout: "uv 0.5.1\n" }
  });
  const result = checkPrerequisites({ spawn });
  assert.equal(result.ok, true);
  assert.deepEqual(result.missing, []);
  assert.equal(result.checks.length, 2);
});

test("checkPrerequisites: node ok but uv missing returns ok:false with uv in missing", () => {
  const spawn = makeVersionSpawn({
    node: { status: 0, stdout: "v20.11.1\n" },
    uv: "ENOENT"
  });
  const result = checkPrerequisites({ spawn });
  assert.equal(result.ok, false);
  assert.equal(result.missing.length, 1);
  assert.equal(result.missing[0].name, "uv");
  assert.ok(result.missing[0].hint, "missing uv entry must carry a hint");
});

test("checkPrerequisites: both missing returns ok:false with missing length 2", () => {
  const spawn = makeVersionSpawn({
    node: "ENOENT",
    uv: "ENOENT"
  });
  const result = checkPrerequisites({ spawn });
  assert.equal(result.ok, false);
  assert.equal(result.missing.length, 2);
});

test("checkPrerequisites: missing entries carry name and hint", () => {
  const spawn = makeVersionSpawn({
    node: "ENOENT",
    uv: "ENOENT"
  });
  const result = checkPrerequisites({ spawn });
  for (const entry of result.missing) {
    assert.ok(entry.name, "each missing entry must have a name");
    assert.ok(entry.hint, "each missing entry must carry a hint");
  }
});

test("checkPrerequisites: checks array has node and uv results", () => {
  const spawn = makeVersionSpawn({
    node: { status: 0, stdout: "v20.11.1\n" },
    uv: { status: 0, stdout: "uv 0.5.1\n" }
  });
  const result = checkPrerequisites({ spawn });
  const names = result.checks.map((c) => c.name);
  assert.ok(names.includes("node"), "checks must include node");
  assert.ok(names.includes("uv"), "checks must include uv");
});

// ─── VER-03: no raw credentials in results ────────────────────────────────────

test("VER-03: planted secret in spawn stdout never surfaces in any returned field", () => {
  // The secret token is planted into spawn stdout. Version parsing must only extract
  // the version number — the raw stdout (including the secret) must not appear in
  // any returned field or hint.
  const SECRET = "secret-tok-9999";
  const spawn = makeVersionSpawn({
    node: { status: 0, stdout: `v20.0.0 ${SECRET}\n` },
    uv: { status: 0, stdout: `uv 0.5.1 ${SECRET}\n` }
  });

  const nodeResult = checkNode({ spawn: makeVersionSpawn({ node: { status: 0, stdout: `v20.0.0 ${SECRET}\n` } }) });
  const uvResult = checkUv({ spawn: makeVersionSpawn({ uv: { status: 0, stdout: `uv 0.5.1 ${SECRET}\n` } }) });
  const prereqResult = checkPrerequisites({ spawn });

  const allSerialized = JSON.stringify([nodeResult, uvResult, prereqResult]);
  assert.ok(!allSerialized.includes(SECRET),
    `planted secret "${SECRET}" must not appear in any returned result`);
});
