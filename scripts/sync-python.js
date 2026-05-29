// Sync the Python server into npm/vendor/python/ for packaging.
//
// IMPORTANT: this script applies the same PUBLIC-tag filter as
// scripts/build_public_mirror.py, so the packaged npm tarball ships ONLY
// PUBLIC-tagged tools + their transitive dependencies. Without this gate,
// `npx @omilia/mcp-server run` would expose the full internal surface,
// bypassing the GitHub mirror's filter.
//
// Strategy: invoke the canonical Python filter against the repo root,
// output to a temp dir, then copy the filtered `src/` + `pyproject.toml`
// into vendor/python/. Single source of filter truth.

import { cpSync, mkdirSync, mkdtempSync, rmSync, existsSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { spawnSync } from "node:child_process";

const npmRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const repoRoot = resolve(npmRoot, "..");
const vendorRoot = join(npmRoot, "vendor", "python");
const filterScript = join(repoRoot, "scripts", "build_public_mirror.py");

if (!existsSync(filterScript)) {
  console.error(`FATAL: filter script not found at ${filterScript}`);
  process.exit(1);
}

// Pick Python 3.11+ (the filter requires tomllib).
const python = process.env.PUBLIC_MIRROR_PYTHON || "python3.11";

const stagingDir = mkdtempSync(join(tmpdir(), "omilia-mcp-vendor-"));

try {
  console.log(`[sync-python] invoking ${filterScript} via ${python} → ${stagingDir}`);
  const result = spawnSync(
    python,
    [filterScript, "--source", repoRoot, "--out", stagingDir],
    { stdio: "inherit", cwd: repoRoot }
  );

  if (result.status !== 0) {
    console.error(
      `[sync-python] filter exited ${result.status}; ` +
      `the npm package CANNOT be built with non-PUBLIC content. ` +
      `Fix the failures and retry.`
    );
    process.exit(result.status ?? 1);
  }

  // Sanity: the filter must have produced at least src/ and pyproject.toml.
  for (const required of ["src", "pyproject.toml"]) {
    if (!existsSync(join(stagingDir, required))) {
      console.error(
        `[sync-python] FATAL: filter output is missing ${required}. ` +
        `Aborting to avoid shipping an incomplete vendor tree.`
      );
      process.exit(1);
    }
  }

  // Replace vendor with the filtered output.
  rmSync(vendorRoot, { force: true, recursive: true });
  mkdirSync(vendorRoot, { recursive: true });

  cpSync(join(stagingDir, "src"), join(vendorRoot, "src"), { recursive: true });
  cpSync(join(stagingDir, "pyproject.toml"), join(vendorRoot, "pyproject.toml"));

  // uv.lock is unfiltered (it's already in the repo root, deterministic) — copy from there.
  cpSync(join(repoRoot, "uv.lock"), join(vendorRoot, "uv.lock"));

  console.log(`[sync-python] vendor refreshed (PUBLIC-only): ${vendorRoot}`);
} finally {
  rmSync(stagingDir, { force: true, recursive: true });
}
