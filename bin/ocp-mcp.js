#!/usr/bin/env node

import { runCli } from "../lib/cli.js";

process.exitCode = await Promise.resolve(runCli(process.argv.slice(2)));
