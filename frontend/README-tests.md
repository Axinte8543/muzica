Frontend tests — how to run locally in Docker or via CI

Run tests in Docker (recommended when local Node version is incompatible):

Linux / macOS:

```bash
cd frontend
./run-tests-docker.sh
```

Windows PowerShell:

```powershell
cd frontend
.\run-tests-docker.ps1
```

Notes:

- The Docker image uses Node 18 and installs dev dependencies, then runs `npm run test:unit` by default.
- To run Playwright E2E inside the container, install browsers and run `npm run test:e2e` (see scripts in `run-tests-docker.sh`).
- The integrated E2E flow seeds deterministic backend data and exercises login -> messages -> recommendations via `npm run test:e2e:full`.

Run tests in GitHub Actions:

- Push your branch or open a PR touching files under `frontend/` — workflow `Frontend CI` will run automatically.
- You can also trigger the workflow manually from the Actions tab (workflow supports `workflow_dispatch`).

Run the full integrated E2E flow locally:

```bash
cd frontend
npm run test:e2e:full
```

If you prefer running tests locally without Docker, install Node LTS (v18 or v20) via `nvm` / `nvm-windows`, then:

```bash
cd frontend
rm -rf node_modules package-lock.json
npm ci
npm run test:unit
npm run test:e2e # after installing playwright browsers: npx playwright install --with-deps
```

Frontend test instructions

Run unit tests locally (recommended: Node LTS v18/v20):

```bash
cd frontend
rm -rf node_modules package-lock.json
npm cache clean --force
npm install
npm run test:unit
```

Run tests in Docker (no need to change host Node):

```bash
# build image
docker build -t licenta-frontend-tests frontend
# run tests (container will execute unit tests)
docker run --rm licenta-frontend-tests
```

Run tests in CI: the GitHub Actions workflow `.github/workflows/frontend-ci.yml` will run Vitest and Playwright on Node 18 for pushes/PRs affecting `frontend/`.
