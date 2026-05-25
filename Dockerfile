# ── Stage 1: builder — install dependencies ───────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /app

RUN pip install --no-cache-dir --upgrade pip

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ── Stage 2: runner — lean production image ───────────────────────────────────
FROM python:3.12-slim AS runner

WORKDIR /app

# Copy installed packages from builder stage
COPY --from=builder /install /usr/local

# Copy application source
COPY . .

# Cloud Run expects the container to listen on $PORT (default 8080)
ENV PORT=8080
EXPOSE 8080

COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

CMD ["./entrypoint.sh"]
