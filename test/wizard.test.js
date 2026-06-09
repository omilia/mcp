import assert from "node:assert/strict";
import test from "node:test";

import {
  PROMPT_FIELDS,
  buildConfirmationSummary,
  buildNoTtyError,
  maskSecret,
  mergeFlagsAndAnswers,
  missingPromptFields,
  needsPrompting,
  requiredFieldsFor
} from "../lib/wizard.js";

// ─── PROMPT_FIELDS shape ──────────────────────────────────────────────────────

test("PROMPT_FIELDS is an ordered array of descriptors", () => {
  assert.ok(Array.isArray(PROMPT_FIELDS));
  const names = PROMPT_FIELDS.map((f) => f.name);
  assert.ok(names.includes("client"), "must include client");
  assert.ok(names.includes("authChoice"), "must include authChoice");
  assert.ok(names.includes("baseUrl"), "must include baseUrl");
  assert.ok(names.includes("accessToken"), "must include accessToken");
  // client appears before authChoice, authChoice before baseUrl
  assert.ok(names.indexOf("client") < names.indexOf("authChoice"));
  assert.ok(names.indexOf("authChoice") < names.indexOf("baseUrl"));
});

test("PROMPT_FIELDS descriptors have required shape (name, label, secret)", () => {
  for (const field of PROMPT_FIELDS) {
    assert.ok(typeof field.name === "string", `${field.name}: name must be string`);
    assert.ok(typeof field.label === "string", `${field.name}: label must be string`);
    assert.ok(typeof field.secret === "boolean", `${field.name}: secret must be boolean`);
  }
});

test("accessToken and password are flagged secret", () => {
  const atField = PROMPT_FIELDS.find((f) => f.name === "accessToken");
  const pwField = PROMPT_FIELDS.find((f) => f.name === "password");
  assert.ok(atField, "accessToken field must exist");
  assert.ok(pwField, "password field must exist");
  assert.equal(atField.secret, true);
  assert.equal(pwField.secret, true);
});

test("realm field has a default of 'master'", () => {
  const realmField = PROMPT_FIELDS.find((f) => f.name === "realm");
  assert.ok(realmField, "realm field must exist");
  assert.equal(realmField.default, "master");
});

// ─── needsPrompting ───────────────────────────────────────────────────────────

test("needsPrompting returns false for fully-flagged PAT options with isTty true", () => {
  const options = {
    client: "claude-code",
    authChoice: "pat",
    baseUrl: "https://ocp.example.com",
    accessToken: "pat-secret-token"
  };
  assert.equal(needsPrompting(options, { isTty: true }), false);
});

test("needsPrompting returns true when accessToken missing and isTty true", () => {
  const options = {
    client: "claude-code",
    authChoice: "pat",
    baseUrl: "https://ocp.example.com"
  };
  assert.equal(needsPrompting(options, { isTty: true }), true);
});

test("needsPrompting returns false when fields missing but isTty false", () => {
  const options = {
    client: "claude-code",
    authChoice: "pat",
    baseUrl: "https://ocp.example.com"
  };
  assert.equal(needsPrompting(options, { isTty: false }), false);
});

test("needsPrompting returns true when client missing and isTty true", () => {
  const options = {
    authChoice: "pat",
    baseUrl: "https://ocp.example.com",
    accessToken: "pat-token"
  };
  assert.equal(needsPrompting(options, { isTty: true }), true);
});

test("needsPrompting returns false for fully-flagged keycloak options with isTty true", () => {
  const options = {
    client: "claude",
    authChoice: "keycloak",
    baseUrl: "https://ocp.example.com",
    username: "alice",
    password: "s3cret"
    // realm omitted — defaults to "master", so not required
  };
  assert.equal(needsPrompting(options, { isTty: true }), false);
});

// ─── requiredFieldsFor ────────────────────────────────────────────────────────

test("requiredFieldsFor PAT includes client, authChoice, baseUrl, accessToken", () => {
  const fields = requiredFieldsFor({ authChoice: "pat" });
  assert.ok(fields.includes("client"));
  assert.ok(fields.includes("authChoice"));
  assert.ok(fields.includes("baseUrl"));
  assert.ok(fields.includes("accessToken"));
  assert.ok(!fields.includes("username"));
  assert.ok(!fields.includes("password"));
});

test("requiredFieldsFor keycloak includes username and password, not accessToken", () => {
  const fields = requiredFieldsFor({ authChoice: "keycloak" });
  assert.ok(fields.includes("username"));
  assert.ok(fields.includes("password"));
  assert.ok(!fields.includes("accessToken"));
});

test("requiredFieldsFor with no authChoice treats it as a field to resolve", () => {
  const fields = requiredFieldsFor({});
  assert.ok(fields.includes("authChoice"));
});

// ─── missingPromptFields ──────────────────────────────────────────────────────

test("missingPromptFields excludes fields already supplied", () => {
  const options = { authChoice: "pat", baseUrl: "https://ocp.example.com" };
  const missing = missingPromptFields(options);
  assert.ok(missing.includes("client"), "client must be listed as missing");
  assert.ok(missing.includes("accessToken"), "accessToken must be listed as missing");
  assert.ok(!missing.includes("baseUrl"), "baseUrl must NOT be listed (supplied)");
  assert.ok(!missing.includes("authChoice"), "authChoice must NOT be listed (supplied)");
});

test("missingPromptFields returns empty array when all PAT fields supplied", () => {
  const options = {
    client: "claude-code",
    authChoice: "pat",
    baseUrl: "https://ocp.example.com",
    accessToken: "pat-token"
  };
  assert.deepEqual(missingPromptFields(options), []);
});

test("missingPromptFields deep-equals ['client','accessToken'] for given scenario", () => {
  // From acceptance criteria: missingPromptFields({authChoice:"pat",baseUrl:"x"})
  // deep-equals ["client","accessToken"] (order per PROMPT_FIELDS, baseUrl excluded)
  const missing = missingPromptFields({ authChoice: "pat", baseUrl: "x" });
  assert.deepEqual(missing, ["client", "accessToken"]);
});

test("missingPromptFields keycloak missing username and password lists them", () => {
  const options = {
    client: "claude",
    authChoice: "keycloak",
    baseUrl: "https://ocp.example.com"
    // username and password missing, realm omitted (has default)
  };
  const missing = missingPromptFields(options);
  assert.ok(missing.includes("username"));
  assert.ok(missing.includes("password"));
  assert.ok(!missing.includes("realm"), "realm must NOT be listed (has default 'master')");
});

test("missingPromptFields treats empty string as missing", () => {
  const options = { authChoice: "pat", baseUrl: "", client: "claude-code" };
  const missing = missingPromptFields(options);
  assert.ok(missing.includes("baseUrl"), "empty string baseUrl must be treated as missing");
});

// ─── mergeFlagsAndAnswers ─────────────────────────────────────────────────────

test("mergeFlagsAndAnswers fills only missing fields from answers", () => {
  const options = { client: "claude-code", authChoice: "pat", baseUrl: "https://ocp.example.com" };
  const answers = { baseUrl: "https://other.com", accessToken: "pat-new-token", client: "claude" };
  const merged = mergeFlagsAndAnswers(options, answers);
  // existing flag wins
  assert.equal(merged.baseUrl, "https://ocp.example.com");
  assert.equal(merged.client, "claude-code");
  // answer fills missing field
  assert.equal(merged.accessToken, "pat-new-token");
});

test("mergeFlagsAndAnswers does not mutate the input options object", () => {
  const options = { client: "claude-code", authChoice: "pat" };
  const answers = { accessToken: "pat-token" };
  const merged = mergeFlagsAndAnswers(options, answers);
  assert.equal(options.accessToken, undefined, "original options must not be mutated");
  assert.equal(merged.accessToken, "pat-token");
});

test("mergeFlagsAndAnswers returns a new object", () => {
  const options = { client: "claude-code" };
  const answers = {};
  const merged = mergeFlagsAndAnswers(options, answers);
  assert.notEqual(merged, options);
});

test("mergeFlagsAndAnswers: flag value beats answer even if answer differs", () => {
  const options = { client: "claude-code", authChoice: "pat", accessToken: "existing-token" };
  const answers = { accessToken: "new-token" };
  const merged = mergeFlagsAndAnswers(options, answers);
  assert.equal(merged.accessToken, "existing-token");
});

// ─── maskSecret ───────────────────────────────────────────────────────────────

test("maskSecret returns '(not set)' for undefined", () => {
  assert.equal(maskSecret(undefined), "(not set)");
});

test("maskSecret returns '(not set)' for empty string", () => {
  assert.equal(maskSecret(""), "(not set)");
});

test("maskSecret reveals at most last 4 chars for longer secrets", () => {
  const result = maskSecret("pat-abcd1234");
  assert.ok(result.endsWith("1234"), `expected to end with '1234', got: ${result}`);
  assert.ok(!result.includes("pat-abcd"), "must not reveal the prefix");
});

test("maskSecret fully masks secrets of 4 chars or fewer", () => {
  assert.equal(maskSecret("abcd"), "****");
  assert.equal(maskSecret("ab"), "**");
  assert.equal(maskSecret("a"), "*");
});

test("maskSecret: 'pat-secret-12345' does not include 'pat-secret' and ends with '2345'", () => {
  // From acceptance criteria
  const result = maskSecret("pat-secret-12345");
  assert.ok(!result.includes("pat-secret"), `must not include 'pat-secret', got: ${result}`);
  assert.ok(result.endsWith("2345"), `must end with '2345', got: ${result}`);
});

test("maskSecret never returns the raw secret for a long value", () => {
  const secret = "supersecrettoken123";
  const result = maskSecret(secret);
  assert.notEqual(result, secret);
  assert.ok(result.includes("*"), "result must contain mask characters");
});

// ─── buildConfirmationSummary ─────────────────────────────────────────────────

test("buildConfirmationSummary returns a string", () => {
  const options = {
    client: "claude-code",
    authChoice: "pat",
    baseUrl: "https://ocp.example.com",
    accessToken: "supersecrettoken"
  };
  const summary = buildConfirmationSummary(options);
  assert.ok(typeof summary === "string");
});

test("buildConfirmationSummary does not contain raw accessToken", () => {
  const options = {
    client: "claude-code",
    authChoice: "pat",
    baseUrl: "https://ocp.example.com",
    accessToken: "supersecrettoken"
  };
  const summary = buildConfirmationSummary(options);
  assert.ok(!summary.includes("supersecrettoken"), `summary must not contain raw secret, got:\n${summary}`);
});

test("buildConfirmationSummary does not contain raw password", () => {
  const options = {
    client: "claude",
    authChoice: "keycloak",
    baseUrl: "https://ocp.example.com",
    username: "alice",
    password: "very-secret-password"
  };
  const summary = buildConfirmationSummary(options);
  assert.ok(!summary.includes("very-secret-password"), `summary must not contain raw password, got:\n${summary}`);
});

test("buildConfirmationSummary includes client and auth method", () => {
  const options = {
    client: "claude-code",
    authChoice: "pat",
    baseUrl: "https://ocp.example.com",
    accessToken: "supersecrettoken"
  };
  const summary = buildConfirmationSummary(options);
  assert.ok(summary.includes("claude-code"), "summary must include client");
  assert.ok(summary.toLowerCase().includes("pat"), "summary must mention auth method");
});

test("buildConfirmationSummary includes base URL without masking", () => {
  const options = {
    client: "claude-code",
    authChoice: "pat",
    baseUrl: "https://ocp.example.com",
    accessToken: "token"
  };
  const summary = buildConfirmationSummary(options);
  assert.ok(summary.includes("https://ocp.example.com"), "summary must include base URL");
});

// ─── buildNoTtyError ──────────────────────────────────────────────────────────

test("buildNoTtyError returns a string", () => {
  const result = buildNoTtyError(["client", "accessToken"]);
  assert.ok(typeof result === "string");
});

test("buildNoTtyError contains --client for 'client' field", () => {
  const result = buildNoTtyError(["client", "accessToken"]);
  assert.ok(result.includes("--client"), `must include '--client', got:\n${result}`);
});

test("buildNoTtyError contains --access-token for 'accessToken' field", () => {
  const result = buildNoTtyError(["client", "accessToken"]);
  assert.ok(result.includes("--access-token"), `must include '--access-token', got:\n${result}`);
});

test("buildNoTtyError maps all field names to their flags", () => {
  const allFields = ["client", "authChoice", "baseUrl", "accessToken", "username", "password", "realm"];
  const result = buildNoTtyError(allFields);
  assert.ok(result.includes("--client"));
  assert.ok(result.includes("--auth"));
  assert.ok(result.includes("--base-url"));
  assert.ok(result.includes("--access-token"));
  assert.ok(result.includes("--username"));
  assert.ok(result.includes("--password"));
  assert.ok(result.includes("--realm"));
});

test("buildNoTtyError includes an example command invocation", () => {
  const result = buildNoTtyError(["client"]);
  // Must include some reference to npx or the init command
  assert.ok(
    result.includes("npx") || result.includes("init"),
    `expected example invocation in:\n${result}`
  );
});

test("buildNoTtyError does not throw — returns string for caller to handle", () => {
  // Must be callable without throwing
  assert.doesNotThrow(() => buildNoTtyError([]));
  assert.doesNotThrow(() => buildNoTtyError(["client", "accessToken"]));
});
