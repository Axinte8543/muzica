// Run from any directory: node scripts/verify.mjs
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const frontend = path.join(root, "frontend");
const backend = path.join(root, "backend");
const evidence = path.join(root, "docs/evidence");
fs.mkdirSync(evidence, { recursive: true });
const env = { ...process.env, SENTRY_DSN: "", AZURE_KEY_VAULT_URL: "" };
const run = (command, args, cwd, log) => {
  console.log(`Running ${command} ${args.join(" ")}`);
  const result = spawnSync(command, args, { cwd, env, encoding: "utf8", maxBuffer: 20 * 1024 * 1024 });
  const output = (result.stdout || "") + (result.stderr || "") + (result.error ? String(result.error) : "");
  fs.writeFileSync(path.join(evidence, log), output);
  console.log(output.split("\n").slice(-12).join("\n"));
  return result.status === 0;
};
const browserOK = run(process.execPath, ["node_modules/@playwright/test/cli.js", "test"], frontend, "e2e-latest.log");
// Playwright clears test-results at startup, so unit results are written afterwards.
const unitOK = run(process.execPath, ["node_modules/vitest/vitest.mjs", "run", "--reporter=default", "--reporter=json", "--outputFile=test-results/unit-latest.json"], frontend, "unit-latest.log");
const backendOK = run(process.env.E2E_PYTHON_BIN || "python", ["manage.py", "test", "--settings=config.test_settings", "--noinput", "--verbosity=1"], backend, "backend-latest.log");
const summaryOK = run(process.execPath, ["scripts/summarize-tests.mjs"], root, "summary-latest.log");
process.exit(browserOK && unitOK && backendOK && summaryOK ? 0 : 1);
