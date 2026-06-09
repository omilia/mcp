#!/usr/bin/env node

import { runCli } from "../lib/cli.js";
import { runVerification } from "../lib/verify.js";

// CANONICAL VERIFY CONTRACT: inject the real runVerification so that the genuine
// interactive CLI path runs prerequisite checks + smoke test after install.
// Unit tests that do not inject io.verify will fall through to the NOOP_VERIFY
// stub in lib/cli.js, keeping the full test suite green without spawning uv.
process.verify = runVerification;

process.exitCode = await Promise.resolve(runCli(process.argv.slice(2)));
