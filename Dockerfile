# One container: the built demo, the edgekpi API, and the Malloy runtime.
# The Malloy DuckDB binding is native, so it is installed here for linux and never copied from a Mac.

FROM node:20-bookworm-slim AS web
WORKDIR /src
COPY demo/web/package.json demo/web/package-lock.json ./
ENV PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1
RUN npm ci --no-audit --no-fund
COPY demo/web/ ./
RUN npm run build

FROM node:20-bookworm-slim AS malloy
WORKDIR /runtime
COPY edgekpi/backends/malloy_runtime/package.json edgekpi/backends/malloy_runtime/package-lock.json ./
RUN npm ci --omit=dev --no-audit --no-fund
COPY edgekpi/backends/malloy_runtime/run.js ./run.js

FROM python:3.12-slim
# node:20-bookworm-slim is the same Debian family. The binary is enough; npm is not used at runtime.
COPY --from=node:20-bookworm-slim /usr/local/bin/node /usr/local/bin/node
RUN node --version

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PORT=8080 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    HOME=/tmp

COPY pyproject.toml README.md ./
COPY edgekpi/ ./edgekpi/
RUN pip install --no-cache-dir -e ".[duckdb]"

COPY --from=malloy /runtime/node_modules ./edgekpi/backends/malloy_runtime/node_modules
COPY --from=malloy /runtime/package.json ./edgekpi/backends/malloy_runtime/package.json
COPY --from=malloy /runtime/run.js ./edgekpi/backends/malloy_runtime/run.js
COPY examples/ ./examples/
COPY specs/library/evidence/ ./specs/library/evidence/
COPY --from=web /src/dist ./demo/web/dist
COPY demo/serve.py ./demo/serve.py

EXPOSE 8080
USER nobody
CMD ["python", "demo/serve.py"]
