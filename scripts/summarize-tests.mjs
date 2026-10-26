import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const evidence = path.join(root, "docs/evidence");
fs.mkdirSync(evidence, { recursive: true });
const read = (name) => JSON.parse(fs.readFileSync(path.join(root, name), "utf8").replace(/^\uFEFF/, ""));
const mode = process.argv[2] || "latest";
const browser = read("frontend/test-results/results.json");
const cases = [];
function visit(suites) {
  for (const suite of suites) {
    for (const spec of suite.specs || []) {
      for (const test of spec.tests) {
        cases.push({ title: spec.title, file: spec.file, line: spec.line,
          status: test.results.at(-1)?.status, expectedStatus: test.expectedStatus,
          error: test.results.at(-1)?.error?.message?.replace(/\u001b\[[0-9;]*m/g, "") });
      }
    }
    visit(suite.suites || []);
  }
}
visit(browser.suites);
const summary = { capturedAt: new Date().toISOString(), sourceStart: browser.stats.startTime,
  stats: browser.stats, cases };
fs.writeFileSync(path.join(evidence, `e2e-${mode}.json`), JSON.stringify(summary, null, 2) + "\n");
if (mode === "latest") {
  const unit = read("frontend/test-results/unit-latest.json");
  fs.writeFileSync(path.join(evidence, "unit-latest.json"), JSON.stringify({
    capturedAt: new Date().toISOString(), total: unit.numTotalTests, passed: unit.numPassedTests,
    failed: unit.numFailedTests, cases: unit.testResults.flatMap(suite => suite.assertionResults.map(test => ({
      name: test.fullName, status: test.status, errors: test.failureMessages,
    }))),
  }, null, 2) + "\n");
}
console.log(`Saved ${cases.length} browser cases to docs/evidence/e2e-${mode}.json`);
