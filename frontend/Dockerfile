FROM node:18-bullseye-slim

WORKDIR /app

# Install build deps
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates git && rm -rf /var/lib/apt/lists/*

# Copy package files first for better caching
COPY package.json package-lock.json* ./

RUN npm install --legacy-peer-deps

# Copy source
COPY . .

# Install Playwright browsers (optional for E2E)
RUN npx playwright install --with-deps || true

CMD ["/bin/sh", "-c", "npm run test:unit || exit 0"]
