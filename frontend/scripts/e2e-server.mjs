import { spawn, spawnSync } from "node:child_process";
import net from "node:net";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const frontendRoot = path.resolve(__dirname, "..");
const repoRoot = path.resolve(frontendRoot, "..");
const backendRoot = path.resolve(repoRoot, "backend");
const isWindows = process.platform === "win32";

const pythonBin =
  process.env.E2E_PYTHON_BIN ||
  process.env.PYTHON_BIN ||
  process.env.PYTHON ||
  "python";

function waitForPort(port, host = "127.0.0.1", timeoutMs = 120_000) {
  const deadline = Date.now() + timeoutMs;

  return new Promise((resolve, reject) => {
    const tick = () => {
      const socket = net.connect({ port, host });
      const cleanup = () => {
        socket.removeAllListeners();
        socket.destroy();
      };

      socket.once("connect", () => {
        cleanup();
        resolve();
      });

      socket.once("error", () => {
        cleanup();
        if (Date.now() > deadline) {
          reject(new Error(`Timed out waiting for ${host}:${port}`));
          return;
        }
        setTimeout(tick, 1000);
      });
    };

    tick();
  });
}

function spawnProcess(command, args, cwd, label) {
  const child = spawn(command, args, {
    cwd,
    stdio: "inherit",
    shell: false,
    env: {
      ...process.env,
      PYTHONUNBUFFERED: "1",
      VITE_API_PROXY_TARGET: "http://127.0.0.1:8000",
    },
  });

  child.on("exit", (code) => {
    if (code && code !== 0) {
      console.error(`${label} exited with code ${code}`);
      process.exit(code);
    }
  });

  return child;
}

async function main() {
  const seedResult = spawnSync(
    pythonBin,
    ["manage.py", "seed_e2e_flow", "--reset"],
    {
      cwd: backendRoot,
      stdio: "inherit",
      shell: false,
      env: {
        ...process.env,
        PYTHONUNBUFFERED: "1",
      },
    },
  );

  if (seedResult.status !== 0) {
    process.exit(seedResult.status ?? 1);
  }

  const backend = spawnProcess(
    pythonBin,
    ["manage.py", "runserver", "127.0.0.1:8000"],
    backendRoot,
    "backend",
  );

  try {
    await waitForPort(8000);
  } catch (error) {
    console.error(error?.message || error);
    backend.kill();
    process.exit(1);
  }

  const frontend = spawnProcess(
    isWindows ? "cmd.exe" : "npm",
    isWindows
      ? [
          "/d",
          "/s",
          "/c",
          "npm run dev -- --host 127.0.0.1 --port 5173 --strictPort",
        ]
      : [
          "run",
          "dev",
          "--",
          "--host",
          "127.0.0.1",
          "--port",
          "5173",
          "--strictPort",
        ],
    frontendRoot,
    "frontend",
  );

  const shutdown = () => {
    frontend.kill();
    backend.kill();
  };

  process.on("SIGINT", shutdown);
  process.on("SIGTERM", shutdown);
  process.on("exit", shutdown);

  await waitForPort(5173);

  // Keep the process alive while Playwright runs.
  await new Promise(() => {});
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
