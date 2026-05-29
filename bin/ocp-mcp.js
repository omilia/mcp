#!/usr/bin/env node

import { runCli } from "../lib/cli.js";

process.exitCode = runCli(process.argv.slice(2));
