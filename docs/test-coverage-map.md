# Install-flow test coverage map

Traceability table from TST-01..04 requirements to concrete passing tests.
Every referenced test name was verified verbatim against the test files before
being recorded here.

## Coverage table

| Requirement | What it requires | Covering test(s) (file :: exact test name) | Status |
|-------------|------------------|--------------------------------------------|--------|
| **TST-01** | Interactive wizard prompt flow — client / auth method / credential collection | `test/wizard.test.js` :: `runWizard: bare PAT path — collects client, auth, base-url, token` | Covered |
| | | `test/wizard.test.js` :: `runWizard: keycloak path — collects username, password, realm uses default` | |
| | | `test/wizard.test.js` :: `runWizard: PAT path — accessToken not echoed in captured output` | |
| | | `test/cli.test.js` :: `interactive bare init reaches masked confirmation summary (WIZ-01, WIZ-04)` | |
| **TST-02** | `claude mcp add` invocation for Claude Code + CLI-absent fallback | `test/cli.test.js` :: `init --client claude-code invokes claude mcp add with correct argv (CLI-01)` | Covered |
| | | `test/cli.test.js` :: `claude-code --print emits the masked mcp add command, no spawn (CLI-01)` | |
| | | `test/install.test.js` :: `installClaudeCode with available claude: records argv and returns 0` | |
| | | `test/install.test.js` :: `installClaudeCode CLI-absent path: returns 0 (graceful)` | |
| | | `test/install.test.js` :: `installClaudeCode CLI-absent path: writes guidance to stdout` | |
| **TST-03** | Config written to the correct location for each supported client | `test/cli.test.js` :: `init --client claude --write writes valid mcpServers JSON with npx github:omilia/mcp run (CLI-04, CLI-05)` | Covered |
| | | `test/cli.test.js` :: `clientConfigPath('claude') resolves to macOS claude_desktop_config.json path (CLI-04 location)` | |
| | | `test/cli.test.js` :: `writes Cursor config to an explicit path` | |
| | | `test/cli.test.js` :: `clientConfigPath returns undefined for claude-code (CLI-02: no settings.json write path)` | |
| **TST-04** | Flag-driven (non-interactive) invocations stay backward-compatible | `test/cli.test.js` :: `fully-flagged --print returns config JSON only, no prompts (WIZ-05)` | Covered |
| | | `test/cli.test.js` :: `PAT init for claude produces byte-identical output to golden SHA` | |
| | | `test/wizard.test.js` :: `runWizard: fully-flagged — prompts for nothing, returns options unchanged` | |

## Audit verdict

**All four TST requirements are Covered. No gaps were found.**

The audit found no missing assertions. Every requirement maps to one or more named,
passing tests that exist verbatim in the test suite. No additions to `test/cli.test.js`
are needed (Task 2 is a no-op on the test files).

## Suite size

Captured from `node --test` run during this audit:

```
# tests 155
# pass  155
# fail  0
```

All 155 tests are green. All referenced tests above are part of this suite.

## File map

| Test file | Requirements covered |
|-----------|---------------------|
| `test/wizard.test.js` | TST-01 (wizard prompt flow), TST-04 (fully-flagged) |
| `test/cli.test.js` | TST-01 (integration), TST-02 (claude mcp add + print), TST-03 (per-client write paths), TST-04 (golden SHA + no-prompt) |
| `test/install.test.js` | TST-02 (installClaudeCode CLI-present and CLI-absent) |
