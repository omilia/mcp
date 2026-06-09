import {
  DEFAULT_REALM_PLACEHOLDER,
  SUPPORTED_AUTH_CHOICES,
  SUPPORTED_CLIENTS
} from "./config.js";

/**
 * PROMPT_FIELDS — ordered field descriptors for the interactive wizard.
 *
 * Each descriptor has:
 *   name    — key name matching parseInitOptions (lib/cli.js)
 *   label   — human-readable prompt text shown to the user
 *   secret  — true if the value must be masked in confirmations and logs
 *   default — (optional) default value accepted without user input
 *
 * Order matters: the wizard presents fields in this sequence.
 * Auth-conditional fields (accessToken / keycloak group) are filtered
 * by missingPromptFields based on the resolved authChoice.
 */
export const PROMPT_FIELDS = [
  { name: "client", label: "MCP client (claude-code, claude)", secret: false },
  { name: "authChoice", label: "Auth method (pat, keycloak)", secret: false },
  { name: "baseUrl", label: "Base URL", secret: false },
  // PAT credential
  { name: "accessToken", label: "Access token", secret: true },
  // Keycloak credentials
  { name: "username", label: "Username", secret: false },
  { name: "password", label: "Password", secret: true },
  { name: "realm", label: "Realm", secret: false, default: DEFAULT_REALM_PLACEHOLDER }
];

/**
 * Return the ordered list of field names required for the given options.
 *
 * Always required: client, authChoice, baseUrl.
 * PAT: + accessToken.
 * Keycloak: + username, password. (realm has a default; not listed as required.)
 *
 * When authChoice is absent we cannot resolve the conditional fields, so
 * authChoice itself is included as a field to resolve (the caller must prompt
 * for it before the credential fields can be determined).
 */
export function requiredFieldsFor(options) {
  const base = ["client", "authChoice", "baseUrl"];

  const auth = options.authChoice;

  if (auth === "pat") {
    return [...base, "accessToken"];
  }

  if (auth === "keycloak") {
    return [...base, "username", "password"];
  }

  // authChoice unknown/absent — return base so the caller knows it must be resolved
  return base;
}

/**
 * isMissing — treat undefined and empty string as "not supplied".
 */
function isMissing(value) {
  return value === undefined || value === null || value === "";
}

/**
 * missingPromptFields(options) — returns the ordered subset of required
 * field names whose value is absent in options (WIZ-05: flag-supplied fields
 * are never returned).
 *
 * realm is special: it has a default of "master" and is only considered
 * missing when authChoice is keycloak and no --realm was given.
 */
export function missingPromptFields(options) {
  const required = requiredFieldsFor(options);
  const missing = [];

  for (const fieldName of required) {
    if (isMissing(options[fieldName])) {
      missing.push(fieldName);
    }
  }

  // realm: keycloak-only, has default — only prompt when explicitly keycloak
  // and not already supplied. requiredFieldsFor does not include realm (default
  // satisfies it), so we do not add it here. The default value itself is
  // sufficient and is applied at buildConfirmationSummary / config-build time.

  return missing;
}

/**
 * needsPrompting(options, { isTty }) — returns true when the wizard should
 * enter interactive mode (WIZ-05).
 *
 * Returns false when:
 *   - isTty is false (non-interactive environment — caller must error instead)
 *   - every required field is already supplied (fully-flagged invocation)
 *
 * Returns true only when at least one required field is missing AND isTty is true.
 */
export function needsPrompting(options, { isTty }) {
  if (!isTty) {
    return false;
  }
  return missingPromptFields(options).length > 0;
}

/**
 * mergeFlagsAndAnswers(options, answers) — merges wizard answers into the
 * existing options object, where FLAG values win over ANSWERS (WIZ-05).
 *
 * Only fills fields that are missing in options. Never mutates the input.
 */
export function mergeFlagsAndAnswers(options, answers) {
  const merged = { ...options };

  for (const [key, value] of Object.entries(answers)) {
    if (isMissing(merged[key])) {
      merged[key] = value;
    }
  }

  return merged;
}

/**
 * maskSecret(value) — reveals at most the last 4 characters of a secret,
 * replacing the remainder with "*". Short secrets (<=4 chars) are fully masked.
 *
 * Returns "(not set)" for undefined/null/empty.
 * The full secret is NEVER concatenated into the return value (T-01-02).
 */
export function maskSecret(value) {
  if (isMissing(value)) {
    return "(not set)";
  }

  const str = String(value);
  const len = str.length;

  if (len <= 4) {
    return "*".repeat(len);
  }

  // Reveal only the last 4 characters; mask the rest by character count.
  // The raw secret prefix is never embedded in the return value — only the
  // final 4 chars are sliced from the original string.
  const maskCount = len - 4;
  const tail = str.slice(len - 4);
  return "*".repeat(maskCount) + tail;
}

// ─── Field → flag name map (WIZ-06) ──────────────────────────────────────────

const FIELD_TO_FLAG = {
  client: "--client",
  authChoice: "--auth",
  baseUrl: "--base-url",
  accessToken: "--access-token",
  username: "--username",
  password: "--password",
  realm: "--realm"
};

/**
 * buildConfirmationSummary(options) — returns a multi-line human-readable
 * string listing all wizard-collected fields. Secret fields are rendered via
 * maskSecret so raw credentials never appear in the summary (WIZ-04, T-01-01).
 */
export function buildConfirmationSummary(options) {
  const lines = ["Configuration summary:"];

  for (const field of PROMPT_FIELDS) {
    const value = options[field.name];

    // Skip keycloak-only fields when auth is PAT (and vice versa)
    if (field.name === "accessToken" && options.authChoice !== "pat") {
      continue;
    }
    if (
      (field.name === "username" || field.name === "password") &&
      options.authChoice !== "keycloak"
    ) {
      continue;
    }
    if (field.name === "realm" && options.authChoice !== "keycloak") {
      continue;
    }

    const displayValue = field.secret
      ? maskSecret(value)
      : isMissing(value)
        ? "(not set)"
        : String(value);

    lines.push(`  ${field.label}: ${displayValue}`);
  }

  return lines.join("\n");
}

/**
 * buildNoTtyError(missingFields) — returns a single actionable error string
 * naming the missing flags (WIZ-06). Does NOT throw; returns string so the
 * caller writes it to stderr and exits with code 1.
 */
export function buildNoTtyError(missingFields) {
  const flagList = missingFields
    .map((name) => FIELD_TO_FLAG[name] ?? `--${name}`)
    .join(", ");

  const exampleParts = [
    "npx github:omilia/mcp init",
    "--client claude-code",
    "--auth pat",
    "--base-url https://your-ocp-base-url",
    "--access-token YOUR_ACCESS_TOKEN"
  ];

  const lines = [
    "Error: missing required options for non-interactive mode.",
    flagList.length > 0 ? `  Missing flags: ${flagList}` : "  No flags missing.",
    "",
    "Supply all required flags to skip interactive prompts, for example:",
    `  ${exampleParts.join(" ")}`
  ];

  return lines.join("\n");
}
