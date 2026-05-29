#!/usr/bin/env bash
set -euo pipefail

# Build the Docker image (uses Node 18 image defined in Dockerfile)
docker build -t licenta-frontend-tests .

# Run unit tests (Vitest)
docker run --rm licenta-frontend-tests

# To run E2E tests (Playwright) in container, rebuild then run with explicit command:
# docker build -t licenta-frontend-tests .
# docker run --rm licenta-frontend-tests /bin/sh -c "npx playwright install --with-deps && npm run test:e2e"
