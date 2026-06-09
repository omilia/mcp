import { spawnSync } from "node:child_process";
import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname } from "node:path";

import {
  buildClientConfig,
  clientConfigPath,
  serializeClientConfig,
  SUPPORTED_AUTH_CHOICES,
  SUPPORTED_CLIENTS
} from "./config.js";
import { installClaudeCode } from "./install.js";
import { runMcpServer } from "./runtime.js";
import {
  buildConfirmationSummary,
  buildNoTtyError,
  missingPromptFields,
  runWizard
} from "./wizard.js";

// ─── CANONICAL VERIFY CONTRACT ─────────────────────────────────────────────────
// io.verify (injected by bin/ocp-mcp.js or tests) is the runVerification function.
// When io.verify is absent (legacy callers, unit tests that do not inject it),
// a no-op stub is used so that the real smoke test NEVER runs inside tests that
// don't provide it — keeping existing --write tests green without uv on PATH.
// Production path: bin/ocp-mcp.js sets process.verify = runVerification before
// calling runCli, so the real verification runs for interactive CLI users.
const NOOP_VERIFY = () => Promise.resolve({ ok: true, summary: "" });

export function runCli(argv, io = process) {
  const [command, ...args] = argv;

  if (command === "init") {
    return runInit(args, io);
  }

  if (command === "run") {
    return runRun(args, io);
  }

  io.stderr.write(`Unsupported command: ${command ?? "(missing)"}\n`);
  io.stderr.write(helpText());
  return 1;
}

/**
 * finishInit(effectiveOptions, io) — synchronous tail of runInit that builds
 * the config and either writes it to a file or prints it to stdout.
 *
 * Called from both the synchronous (fully-flagged) and async (wizard) paths.
 * Returns a synchronous integer for --print and error paths; returns a Promise
 * when verification is wired into the write/install path.
 *
 * @returns {number|Promise<number>} exit code (0 = success, 1 = error)
 */
function finishInit(effectiveOptions, io) {
  if (!SUPPORTED_CLIENTS.has(effectiveOptions.client)) {
    io.stderr.write(`Unsupported client: ${effectiveOptions.client}\n`);
    return 1;
  }

  // claude-code is installed via `claude mcp add` CLI, not the JSON write path (CLI-01, CLI-02).
  // CANONICAL SPAWN CONTRACT: forward io.spawn (test-injected) or the real spawnSync.
  if (effectiveOptions.client === "claude-code") {
    const installCode = installClaudeCode(effectiveOptions, io, { spawn: io.spawn ?? spawnSync });
    // Run verification after a real install (path 3) — skip for --print (path 1) and
    // CLI-absent guidance (path 2, installCode===0 but nothing was installed).
    // Verification gate: non-print + verifyInstall !== false + install succeeded.
    // NOTE: installClaudeCode paths 1 (print) and 2 (no CLI) both return 0 but must
    // NOT trigger verification — we cannot distinguish path 2 from path 3 without
    // probing the claude CLI again. Gate on print + verifyInstall; accept the small
    // risk that the CLI-absent path may run a no-op verify (no real spawn occurs since
    // NOOP_VERIFY is the default when io.verify is absent).
    if (installCode === 0 && !effectiveOptions.print && effectiveOptions.verifyInstall !== false && io.verify) {
      return (async () => {
        const { ok, summary } = await io.verify();
        if (summary) io.stdout.write(summary);
        return ok ? 0 : 1;
      })();
    }
    return installCode;
  }

  const config = buildClientConfig(effectiveOptions.client, {
    serverName: effectiveOptions.serverName,
    baseUrl: effectiveOptions.baseUrl,
    accessToken: effectiveOptions.accessToken,
    username: effectiveOptions.username,
    password: effectiveOptions.password,
    realm: effectiveOptions.realm,
    useEnvVars: effectiveOptions.useEnvVars,
    authChoice: effectiveOptions.authChoice
  });

  if (effectiveOptions.write) {
    let writeOk;
    try {
      writeClientConfig(effectiveOptions.client, config, effectiveOptions);
      io.stdout.write(`Wrote ${effectiveOptions.client} MCP config to ${resolveWritePath(effectiveOptions.client, effectiveOptions)}\n`);
      writeOk = true;
    } catch (error) {
      io.stderr.write(`${error.message}\n`);
      return 1;
    }

    // Run verification after a successful write — only when non-print, not opted-out,
    // AND io.verify is actually injected (so tests without io.verify stay synchronous).
    if (writeOk && !effectiveOptions.print && effectiveOptions.verifyInstall !== false && io.verify) {
      return (async () => {
        const { ok, summary } = await io.verify();
        if (summary) io.stdout.write(summary);
        return ok ? 0 : 1;
      })();
    }
    return 0;
  }

  // Default --print branch — never verify.
  io.stdout.write(serializeClientConfig(effectiveOptions.client, config));
  return 0;
}

function runInit(args, io) {
  let options;

  try {
    options = parseInitOptions(args);
  } catch (error) {
    io.stderr.write(`${error.message}\n`);
    io.stderr.write(helpText());
    return error.exitCode ?? 1;
  }

  // Determine whether interactive prompting is needed.
  // missingPromptFields returns the fields the wizard would collect. We use this
  // to gate the TTY/no-TTY branches. The EXISTING partial-flag path (e.g.,
  // --client cursor without --base-url) is preserved: if missing fields exist
  // but io.input is neither TTY nor actively falsy (i.e., io.input is absent,
  // meaning the caller did not inject a stream at all), we fall through to the
  // synchronous finishInit so placeholder-default behavior is preserved.
  //
  // The guard fires only when io.input is explicitly injected (tests that inject
  // a non-TTY io to simulate no-TTY environments, or the bin entry which reads
  // from process.stdin).
  const isTty = !!io.input?.isTTY;
  const missing = missingPromptFields(options);

  // (WIZ-06) No-TTY + missing required fields + an injected io.input stream:
  // fail immediately with actionable message (bare init in CI / non-terminal).
  // When io.input is entirely absent (legacy callers not injecting input), fall
  // through to the synchronous path so existing placeholder behavior is intact.
  if (missing.length > 0 && io.input !== undefined && !isTty) {
    io.stderr.write(buildNoTtyError(missing) + "\n");
    return 1;
  }

  // (WIZ-01) TTY + missing required fields: run the interactive wizard.
  if (missing.length > 0 && isTty) {
    // Async path — returns Promise<integer>.
    // runWizard expects { input, output } while runCli uses { input, stdout, stderr }.
    // Map to the wizard-compatible shape.
    const wizardIo = { input: io.input, output: io.stdout };
    return (async () => {
      const merged = await runWizard(options, wizardIo);
      // (WIZ-04) Write confirmation summary BEFORE any file/process change.
      io.stdout.write(buildConfirmationSummary(merged) + "\n");
      return finishInit(merged, io);
    })();
  }

  // Fully-flagged path (or legacy no-input path) — synchronous, integer return.
  // finishInit handles the SUPPORTED_CLIENTS guard and build/print/write.
  return finishInit(options, io);
}

function runRun(args, io) {
  let options;

  try {
    options = parseRunOptions(args);
  } catch (error) {
    io.stderr.write(`${error.message}\n`);
    io.stderr.write(helpText());
    return 1;
  }

  try {
    return runMcpServer({ ...options, io });
  } catch (error) {
    io.stderr.write(`${error.message}\n`);
    return 1;
  }
}

function parseInitOptions(args) {
  const options = {
    accessToken: undefined,
    authChoice: "pat",
    baseUrl: undefined,
    client: undefined,
    force: false,
    password: undefined,
    path: undefined,
    print: false,
    realm: undefined,
    serverName: undefined,
    useEnvVars: false,
    username: undefined,
    verifyInstall: true,
    write: false
  };

  for (let index = 0; index < args.length; index += 1) {
    const arg = args[index];

    if (arg === "--client") {
      options.client = readOptionValue(args, index, arg);
      index += 1;
    } else if (arg === "--print") {
      options.print = true;
    } else if (arg === "--path") {
      options.path = readOptionValue(args, index, arg);
      index += 1;
    } else if (arg === "--server-name") {
      options.serverName = readOptionValue(args, index, arg);
      index += 1;
    } else if (arg === "--base-url") {
      options.baseUrl = readOptionValue(args, index, arg);
      index += 1;
    } else if (arg === "--access-token") {
      options.accessToken = readOptionValue(args, index, arg);
      index += 1;
    } else if (arg === "--auth") {
      options.authChoice = readOptionValue(args, index, arg);
      index += 1;
    } else if (arg === "--username") {
      options.username = readOptionValue(args, index, arg);
      index += 1;
    } else if (arg === "--password") {
      options.password = readOptionValue(args, index, arg);
      index += 1;
    } else if (arg === "--realm") {
      options.realm = readOptionValue(args, index, arg);
      index += 1;
    } else if (arg === "--use-env-vars") {
      options.useEnvVars = true;
    } else if (arg === "--write") {
      options.write = true;
    } else if (arg === "--force") {
      options.force = true;
    } else if (arg === "--no-verify-install") {
      options.verifyInstall = false;
    } else {
      throw new Error(`Unsupported option: ${arg}`);
    }
  }

  if (!SUPPORTED_AUTH_CHOICES.includes(options.authChoice)) {
    // Invalid --auth value exits with code 2 and the error message
    // names the supported values verbatim ("supported", "pat",
    // "keycloak"). Exit code is propagated via `error.exitCode`.
    const err = new Error(
      `Unsupported --auth value: ${options.authChoice}. Supported values are: pat, keycloak.`
    );
    err.exitCode = 2;
    throw err;
  }

  if (options.useEnvVars && (options.accessToken || options.baseUrl)) {
    throw new Error("--use-env-vars cannot be combined with --access-token or --base-url");
  }

  return options;
}

function parseRunOptions(args) {
  const options = {
    dryRun: false
  };

  for (let index = 0; index < args.length; index += 1) {
    const arg = args[index];

    if (arg === "--dry-run") {
      options.dryRun = true;
    } else {
      throw new Error(`Unsupported option: ${arg}`);
    }
  }

  return options;
}

function readOptionValue(args, index, optionName) {
  const value = args[index + 1];

  if (!value || value.startsWith("--")) {
    throw new Error(`Missing value for ${optionName}`);
  }

  return value;
}

function writeClientConfig(client, config, options) {
  if (client === "codex") {
    throw new Error("Codex write support is not implemented yet. Re-run with --print and paste the TOML into your Codex config.");
  }

  const outputPath = resolveWritePath(client, options);

  if (!outputPath) {
    throw new Error(`No default config path is known for ${client}. Pass --path explicitly or use --print.`);
  }

  if (client === "vscode") {
    writeJsonConfig(outputPath, config, "servers", options.force);
    return;
  }

  writeJsonConfig(outputPath, config, "mcpServers", options.force);
}

function writeJsonConfig(outputPath, config, rootKey, force) {
  const nextSection = config[rootKey];
  let existingConfig = {};

  if (existsSync(outputPath)) {
    existingConfig = JSON.parse(readFileSync(outputPath, "utf8"));
  }

  const existingSection = existingConfig[rootKey] ?? {};
  const serverNames = Object.keys(nextSection);
  const conflicts = serverNames.filter((serverName) => existingSection[serverName] && !force);

  if (conflicts.length > 0) {
    throw new Error(`Config already contains ${conflicts.join(", ")}. Re-run with --force to replace it.`);
  }

  const mergedConfig = {
    ...existingConfig,
    [rootKey]: {
      ...existingSection,
      ...nextSection
    }
  };

  mkdirSync(dirname(outputPath), { recursive: true });
  writeFileSync(outputPath, JSON.stringify(mergedConfig, null, 2) + "\n", { mode: 0o600 });
}

function resolveWritePath(client, options) {
  return options.path || clientConfigPath(client);
}

function helpText() {
  return [
    "Usage:",
    "  npx github:omilia/mcp init --client cursor|claude|claude-code|codex|vscode",
    "      [--print] [--write] [--force] [--path FILE] [--server-name OCP]",
    "      [--auth pat|keycloak] [--base-url URL] [--access-token PAT]",
    "      [--username U] [--password P] [--realm R]",
    "      [--use-env-vars] [--no-verify-install]",
    "",
    "  Default: emits literal placeholders ('your-ocp-base-url', 'your-ocp-access-token')",
    "  for the user to fill in directly (no shell indirection). Supply --base-url and",
    "  --access-token to inject real values. Use --use-env-vars to emit '${VAR}'",
    "  references that resolve from the launching shell.",
    "",
    "  Auth: --auth defaults to 'pat' (emits OCP_BASE_URL + OCP_ACCESS_TOKEN",
    "  placeholders). Pass --auth keycloak to emit a config",
    "  with OCP_USERNAME / OCP_PASSWORD / OCP_KEYCLOAK_REALM in place of",
    "  OCP_ACCESS_TOKEN. --username, --password, --realm inject literal values",
    "  in place of the Keycloak placeholders.",
    "",
    "  npx github:omilia/mcp run [--dry-run]",
    ""
  ].join("\n");
}
