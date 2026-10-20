#!/usr/bin/env pwsh
Set-StrictMode -Version Latest

Write-Host "Building Docker image for frontend tests..."
docker build -t licenta-frontend-tests .

Write-Host "Running unit tests inside container..."
docker run --rm licenta-frontend-tests

Write-Host "To run Playwright E2E inside container, run the following (after build):"
Write-Host 'docker run --rm licenta-frontend-tests /bin/sh -c "npx playwright install --with-deps && npm run test:e2e"'
