import { createInterface } from "node:readline/promises";

/**
 * askChoice(label, choices, io) — presents the label and an enumerated list of
 * choices, reads a line, accepts either the 1-based index or the choice value
 * string, re-prompts on invalid input, and resolves to the selected choice value.
 *
 * @param {string} label - The prompt label shown to the user.
 * @param {Array<{value: string, label?: string}>} choices - Array of choice descriptors.
 * @param {{ input: NodeJS.ReadableStream, output: NodeJS.WritableStream }} [io]
 *   - Injected I/O streams; defaults to { input: process.stdin, output: process.stdout }.
 * @returns {Promise<string>} The selected choice value.
 */
export async function askChoice(label, choices, io = { input: process.stdin, output: process.stdout }) {
  const rl = createInterface({ input: io.input, output: io.output, terminal: false });

  // Build the prompt text with enumerated choices.
  const lines = [`${label}:`];
  for (let i = 0; i < choices.length; i++) {
    const c = choices[i];
    const displayLabel = c.label ?? c.value;
    lines.push(`  ${i + 1}. ${displayLabel} (${c.value})`);
  }
  lines.push("Enter number or value: ");
  const prompt = lines.join("\n");

  try {
    while (true) {
      io.output.write(prompt);
      const line = await rl.question("");
      const trimmed = line.trim();

      // Accept a 1-based index.
      const index = parseInt(trimmed, 10);
      if (!isNaN(index) && index >= 1 && index <= choices.length) {
        return choices[index - 1].value;
      }

      // Accept the value string directly.
      const match = choices.find((c) => c.value === trimmed);
      if (match) {
        return match.value;
      }

      // Invalid input — re-prompt.
      io.output.write(`Invalid choice: "${trimmed}". Please enter a number (1-${choices.length}) or a value.\n`);
    }
  } finally {
    rl.close();
  }
}

/**
 * askText(label, { defaultValue }, io) — reads a line, trims whitespace.
 * Empty input returns defaultValue when provided, otherwise re-prompts.
 *
 * @param {string} label - The prompt label shown to the user.
 * @param {{ defaultValue?: string }} [opts] - Options; defaultValue used on empty input.
 * @param {{ input: NodeJS.ReadableStream, output: NodeJS.WritableStream }} [io]
 * @returns {Promise<string>} The entered (or default) value.
 */
export async function askText(label, opts = {}, io = { input: process.stdin, output: process.stdout }) {
  const { defaultValue } = opts;
  const rl = createInterface({ input: io.input, output: io.output, terminal: false });

  const promptSuffix = defaultValue !== undefined ? ` [${defaultValue}]` : "";
  const prompt = `${label}${promptSuffix}: `;

  try {
    while (true) {
      io.output.write(prompt);
      const line = await rl.question("");
      const trimmed = line.trim();

      if (trimmed.length > 0) {
        return trimmed;
      }

      if (defaultValue !== undefined) {
        return defaultValue;
      }

      // Empty and no default — re-prompt.
      io.output.write(`${label} is required. Please enter a value.\n`);
    }
  } finally {
    rl.close();
  }
}

/**
 * askSecret(label, io) — writes the prompt label to io.output, then reads a
 * secret value WITHOUT echoing typed characters.
 *
 * Security contract (T-01-04):
 *   - The label IS written to io.output (so the user knows what to enter).
 *   - The typed characters and the resolved value are NEVER echoed.
 *
 * Two paths:
 *   - Real TTY (io.input.isTTY && setRawMode): raw-mode manual read. Required
 *     because in a terminal the kernel echoes stdin itself (cooked mode), so
 *     muting the program's writer does NOT hide the secret there.
 *   - Non-TTY (pipes / injected test streams): readline with the output writer
 *     muted for the duration of the read.
 *
 * @param {string} label - The prompt label shown to the user (label is visible; value is not).
 * @param {{ input: NodeJS.ReadableStream, output: NodeJS.WritableStream }} [io]
 * @returns {Promise<string>} The entered secret value (never echoed).
 */
export async function askSecret(label, io = { input: process.stdin, output: process.stdout }) {
  // Real terminal: read in raw mode so the TTY does not echo typed characters.
  if (io.input && io.input.isTTY && typeof io.input.setRawMode === "function") {
    return readSecretFromTty(label, io.input, io.output);
  }

  // Non-TTY: write the label, then mute the output writer for the readline read.
  io.output.write(`${label}: `);
  const originalWrite = io.output.write.bind(io.output);
  io.output.write = () => true; // no-op; discard all writes during secret read

  const rl = createInterface({ input: io.input, output: io.output, terminal: false });

  let secret;
  try {
    secret = await rl.question("");
  } finally {
    rl.close();
    // Restore the output writer immediately after the line is resolved.
    io.output.write = originalWrite;
    // Move to next line after the hidden input.
    originalWrite("\n");
  }

  return secret;
}

// Control byte code points handled during raw-mode secret entry.
const CTRL_C = 3;
const BACKSPACE = 8;
const ENTER_CR = 13;
const ENTER_LF = 10;
const DEL = 127;

/**
 * readSecretFromTty(label, input, output) — reads a secret from a raw-mode TTY
 * without echoing typed characters. Handles Enter (submit), Backspace/DEL
 * (erase), and Ctrl-C (abort). Restores the prior raw-mode state on completion.
 */
function readSecretFromTty(label, input, output) {
  return new Promise((resolve, reject) => {
    output.write(`${label}: `);
    const wasRaw = input.isRaw === true;
    input.setRawMode(true);
    input.resume();

    let buf = "";

    function cleanup() {
      input.removeListener("data", onData);
      input.setRawMode(wasRaw);
      input.pause();
    }

    function onData(chunk) {
      const s = chunk.toString("utf8");
      for (const ch of s) {
        const code = ch.charCodeAt(0);
        if (code === ENTER_CR || code === ENTER_LF) {
          cleanup();
          output.write("\n");
          resolve(buf);
          return;
        }
        if (code === CTRL_C) {
          cleanup();
          output.write("\n");
          reject(new Error("Aborted"));
          return;
        }
        if (code === BACKSPACE || code === DEL) {
          buf = buf.slice(0, -1);
          continue;
        }
        if (code >= 32) {
          buf += ch;
        }
      }
    }

    input.on("data", onData);
  });
}
