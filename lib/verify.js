import { checkPrerequisites as defaultCheckPrerequisites } from "./preflight.js";
import { smokeTest as defaultSmokeTest } from "./smoketest.js";

// ─── buildVerifySummary ───────────────────────────────────────────────────────

/**
 * buildVerifySummary({ checks, prereqsOk, smoke }) — renders a multi-line PASS/FAIL
 * summary string from WHITELISTED fields only.
 *
 * Whitelisted fields consumed: name, ok, hint, found (from checks); ok, toolCount, reason (from smoke).
 * No credential, env value, or raw child output is ever rendered (VER-03).
 *
 * @param {object} parts
 * @param {Array<{name:string, ok:boolean, hint?:string, found?:string}>} parts.checks
 * @param {boolean} parts.prereqsOk
 * @param {{ok:boolean, toolCount?:number, reason?:string}|null} parts.smoke
 * @returns {string}
 */
export function buildVerifySummary({ checks, prereqsOk, smoke }) {
  const lines = [];
  lines.push("Install verification:");

  // Per-prereq check lines — only whitelisted fields (name, ok, found, hint).
  for (const check of checks) {
    if (check.ok) {
      // found may be a version string (e.g. "20") — safe, extracted from binary output.
      const versionSuffix = check.found ? ` ${check.found}` : "";
      lines.push(`  [✓] ${check.name}${versionSuffix}`);
    } else {
      // hint is a static install instruction string — never a credential.
      const hintSuffix = check.hint ? ` — ${check.hint}` : "";
      lines.push(`  [✗] ${check.name}${hintSuffix}`);
    }
  }

  // Smoke test line.
  if (!prereqsOk) {
    lines.push("  [-] server smoke test — skipped (prerequisites missing)");
  } else if (smoke && smoke.ok) {
    const toolSuffix = smoke.toolCount != null ? ` — ${smoke.toolCount} tools reachable` : "";
    lines.push(`  [✓] server smoke test${toolSuffix}`);
  } else if (smoke && !smoke.ok) {
    const reasonSuffix = smoke.reason ? ` — ${smoke.reason}` : "";
    lines.push(`  [✗] server smoke test${reasonSuffix}`);
  } else {
    // smoke is null/undefined — defensive fallback (should not normally occur).
    lines.push("  [-] server smoke test — skipped");
  }

  // Overall result line.
  const overallPass = prereqsOk && smoke && smoke.ok;
  lines.push(`Result: ${overallPass ? "PASS" : "FAIL"}`);

  return lines.join("\n") + "\n";
}

// ─── runVerification ──────────────────────────────────────────────────────────

/**
 * runVerification(deps) — orchestrates checkPrerequisites then (conditionally) smokeTest
 * and builds a masked PASS/FAIL summary.
 *
 * CANONICAL INJECTION CONTRACT: resolves injected deps via:
 *   const checkPrereqs = deps.checkPrerequisites ?? defaultCheckPrerequisites
 *   const smoke       = deps.smokeTest        ?? defaultSmokeTest
 *
 * Never throws — smokeTest already never throws; defensive try/catch wraps everything.
 *
 * @param {object} [deps]
 * @param {function} [deps.checkPrerequisites] — injectable for tests
 * @param {function} [deps.smokeTest]          — injectable for tests
 * @param {object}   [deps.smokeDeps]          — forwarded to real smokeTest when not injected
 * @returns {Promise<{ok: boolean, summary: string}>}
 */
export async function runVerification(deps = {}) {
  const checkPrereqs = deps.checkPrerequisites ?? defaultCheckPrerequisites;
  const smoke = deps.smokeTest ?? defaultSmokeTest;

  try {
    // Run prerequisites synchronously (checkPrerequisites is sync).
    const prereqs = checkPrereqs(deps.prereqDeps ?? {});

    if (!prereqs.ok) {
      // Skip smoke test when prerequisites are missing — cannot smoke-test without uv/node.
      const summary = buildVerifySummary({
        checks: prereqs.checks,
        prereqsOk: false,
        smoke: null
      });
      return { ok: false, summary };
    }

    // Prerequisites passed — run the smoke test.
    const smokeResult = await smoke(deps.smokeDeps ?? {});

    const summary = buildVerifySummary({
      checks: prereqs.checks,
      prereqsOk: true,
      smoke: smokeResult
    });

    return { ok: smokeResult.ok, summary };
  } catch (err) {
    // Defensive wrapper — should not normally throw.
    const summary = buildVerifySummary({
      checks: [],
      prereqsOk: false,
      smoke: null
    });
    return { ok: false, summary };
  }
}
