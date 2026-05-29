import { spawnSync } from "node:child_process";
import { existsSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const PACKAGE_ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const ENTRYPOINT_CANDIDATES = ["server"];
const ENTRYPOINTS = new Set(ENTRYPOINT_CANDIDATES);

export function buildRunCommand({
  entrypoint,
  packageRoot = PACKAGE_ROOT
} = {}) {
  if (entrypoint !== undefined && !ENTRYPOINTS.has(entrypoint)) {
    throw new Error(`Unsupported entrypoint: ${entrypoint}`);
  }

  const resolved = resolvePythonProject(packageRoot, entrypoint);
  const entrypointPath = join(resolved.projectRoot, "src", `${resolved.entrypoint}.py`);

  return {
    command: "uv",
    args: ["run", "--project", resolved.projectRoot, "fastmcp", "run", `${entrypointPath}:mcp`],
    env: buildChildEnv(process.env)
  };
}

export function runMcpServer(options = {}) {
  const { dryRun = false, io = process, spawn = spawnSync, ...runOptions } = options;
  const command = buildRunCommand(runOptions);

  if (dryRun) {
    io.stdout.write(`${JSON.stringify({
      command: command.command,
      args: command.args,
      env: {
        OCP_BASE_URL: command.env.OCP_BASE_URL ? "${OCP_BASE_URL}" : undefined,
        OCP_ACCESS_TOKEN: command.env.OCP_ACCESS_TOKEN ? "${OCP_ACCESS_TOKEN}" : undefined
      }
    }, null, 2)}\n`);
    return 0;
  }

  const result = spawn(command.command, command.args, {
    env: command.env,
    stdio: "inherit"
  });

  if (result.error) {
    io.stderr.write(
      `Failed to start OCP MCP Server with uv. Install uv from https://github.com/astral-sh/uv and retry.\n${result.error.message}\n`
    );
    return 1;
  }

  return result.status ?? 1;
}

function resolvePythonProject(packageRoot, preferredEntrypoint) {
  const roots = [
    resolve(packageRoot, ".."),
    join(packageRoot, "vendor", "python")
  ];
  const order = preferredEntrypoint
    ? [preferredEntrypoint, ...ENTRYPOINT_CANDIDATES.filter((c) => c !== preferredEntrypoint)]
    : ENTRYPOINT_CANDIDATES;

  for (const root of roots) {
    if (!existsSync(join(root, "pyproject.toml"))) continue;
    for (const name of order) {
      if (existsSync(join(root, "src", `${name}.py`))) {
        return { projectRoot: root, entrypoint: name };
      }
    }
  }

  throw new Error("Python MCP server sources were not found in the repository checkout or npm package.");
}

function buildChildEnv(env) {
  return { ...env };
}
