import { spawn, spawnSync } from "node:child_process";
import { mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import net from "node:net";
import path from "node:path";
import { fileURLToPath } from "node:url";

const frontend = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const backend = path.resolve(frontend, "../backend");
const python = process.env.E2E_PYTHON_BIN || "python";
const env = { ...process.env, DJANGO_SETTINGS_MODULE: "config.e2e_settings",
  E2E_DB_PATH: path.join(mkdtempSync(path.join(tmpdir(), "romusic-e2e-")), "db.sqlite3"),
  VITE_API_BASE_URL: "http://127.0.0.1:8001", VITE_API_PROXY_TARGET: "http://127.0.0.1:8001",
  PYTHONUNBUFFERED: "1", SENTRY_DSN: "", AZURE_KEY_VAULT_URL: "" };
const children = [];
let stopping = false;
function stop(code = 0) {
  if (stopping) return;
  stopping = true;
  for (const child of children) child.kill();
  process.exit(code);
}
process.on("SIGINT", () => stop());
process.on("SIGTERM", () => stop());
process.on("exit", () => { for (const child of children) child.kill(); });
async function assertFree(port) {
  await new Promise((resolve, reject) => {
    const server = net.createServer();
    server.once("error", reject);
    server.listen(port, "127.0.0.1", () => server.close(resolve));
  });
}
function start(command, args, cwd) {
  const child = spawn(command, args, { cwd, env, stdio: "inherit", shell: false });
  children.push(child);
  child.on("error", (error) => { console.error(error); stop(1); });
  child.on("exit", () => { if (!stopping) stop(1); });
  return child;
}
async function waitForBackend() {
  for (let attempt = 0; attempt < 100; attempt++) {
    try { const res = await fetch("http://127.0.0.1:8001/health/"); if (res.ok) return; } catch {}
    await new Promise((resolve) => setTimeout(resolve, 200));
  }
  throw new Error("E2E backend did not become healthy");
}
try {
  await assertFree(8001);
  await assertFree(5174);
  for (const args of [["migrate", "--noinput", "--verbosity", "0"], ["seed_e2e_flow"]]) {
    const result = spawnSync(python, ["manage.py", ...args], { cwd: backend, env, stdio: "inherit" });
    if (result.error) throw result.error;
    if (result.status !== 0) throw new Error(`E2E setup failed: ${args[0]}`);
  }
  start(python, ["manage.py", "runserver", "127.0.0.1:8001", "--noreload"], backend);
  await waitForBackend();
  start(process.execPath, ["node_modules/vite/bin/vite.js", "--host", "127.0.0.1", "--port", "5174", "--strictPort"], frontend);
} catch (error) { console.error(error); stop(1); }
