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
 * line WITHOUT echoing typed characters to the output stream.
 *
 * Security contract (T-01-04):
 *   - The label IS written to io.output (so the user knows what to enter).
 *   - The typed characters and the resolved value are NEVER written to io.output.
 *
 * Implementation: after writing the label, io.output.write is replaced with a
 * no-op for the duration of the readline question, then restored immediately.
 * This prevents readline from echoing the typed line back to the terminal.
 *
 * @param {string} label - The prompt label shown to the user (label is visible; value is not).
 * @param {{ input: NodeJS.ReadableStream, output: NodeJS.WritableStream }} [io]
 * @returns {Promise<string>} The entered secret value (never echoed).
 */
export async function askSecret(label, io = { input: process.stdin, output: process.stdout }) {
  // Write the label/prompt BEFORE suppressing output, so the user sees it.
  io.output.write(`${label}: `);

  // Mute the output writer for the duration of the readline read.
  // This prevents readline from echoing typed characters back to the terminal.
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
    // Move to next line after the hidden input (visible to user in real terminal).
    originalWrite("\n");
  }

  return secret;
}
