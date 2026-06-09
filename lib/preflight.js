import { spawnSync } from "node:child_process";

// ─── Node install hint ────────────────────────────────────────────────────────

const NODE_HINT =
  "Install Node.js 20+ from https://nodejs.org (or use nvm: nvm install 20).";

// ─── uv install hint ──────────────────────────────────────────────────────────

const UV_HINT =
  "Install uv from https://github.com/astral-sh/uv " +
  "(curl -LsSf https://astral.sh/uv/install.sh | sh).";

// ─── checkNode ────────────────────────────────────────────────────────────────

/**
 * checkNode(deps = {}) — checks that `node` is on PATH and is version 20+.
 *
 * CANONICAL SPAWN CONTRACT: resolves `const spawn = deps.spawn ?? spawnSync` ONCE.
 * Never throws — all spawn errors are caught and returned as a structured failure.
 *
 * Returns:
 *   { name: "node", ok: true, found: "<major>" }
 *   { name: "node", ok: false, found: "<major>"|null, hint: string }
 */
export function checkNode(deps = {}) {
  const spawn = deps.spawn ?? spawnSync;

  let stdout;
  try {
    const result = spawn("node", ["--version"], { encoding: "utf8" });
    if (result == null || result.status !== 0) {
      return { name: "node", ok: false, found: null, hint: NODE_HINT };
    }
    stdout = result.stdout ?? "";
  } catch {
    // ENOENT or any other spawn error — node not found.
    return { name: "node", ok: false, found: null, hint: NODE_HINT };
  }

  // Parse only the major version number — never copy raw stdout into any field.
  // Strip optional leading "v", split on ".", take first segment.
  const match = String(stdout).trim().replace(/^v/i, "").split(".")[0];
  const major = parseInt(match, 10);

  if (isNaN(major)) {
    // Unparseable version string — treat as not found.
    return { name: "node", ok: false, found: null, hint: NODE_HINT };
  }

  if (major >= 20) {
    return { name: "node", ok: true, found: String(major) };
  }

  return { name: "node", ok: false, found: String(major), hint: NODE_HINT };
}

// ─── checkUv ──────────────────────────────────────────────────────────────────

/**
 * checkUv(deps = {}) — checks that `uv` is on PATH.
 *
 * CANONICAL SPAWN CONTRACT: resolves `const spawn = deps.spawn ?? spawnSync` ONCE.
 * Never throws — all spawn errors are caught and returned as a structured failure.
 *
 * Returns:
 *   { name: "uv", ok: true }
 *   { name: "uv", ok: false, hint: string }
 */
export function checkUv(deps = {}) {
  const spawn = deps.spawn ?? spawnSync;

  try {
    const result = spawn("uv", ["--version"], { encoding: "utf8" });
    if (result == null || result.status !== 0) {
      return { name: "uv", ok: false, hint: UV_HINT };
    }
    // uv is present and responded with status 0 — that is sufficient.
    // Do NOT copy raw stdout into any returned field (VER-03).
    return { name: "uv", ok: true };
  } catch {
    // ENOENT or any other spawn error — uv not found.
    return { name: "uv", ok: false, hint: UV_HINT };
  }
}

// ─── checkPrerequisites ───────────────────────────────────────────────────────

/**
 * checkPrerequisites(deps = {}) — aggregates checkNode and checkUv.
 *
 * Passes the SAME deps to both checks so a single injected fake spawn drives
 * both. The fake must branch on the cmd argument ("node" vs "uv").
 *
 * Returns:
 *   { ok: boolean, missing: Array<{name, hint}>, checks: [nodeResult, uvResult] }
 *
 * Callers can iterate `missing` to render exactly what is missing and which
 * install hint to show. Never throws.
 */
export function checkPrerequisites(deps = {}) {
  const nodeResult = checkNode(deps);
  const uvResult = checkUv(deps);

  const checks = [nodeResult, uvResult];
  const missing = checks.filter((r) => !r.ok);

  return { ok: missing.length === 0, missing, checks };
}
