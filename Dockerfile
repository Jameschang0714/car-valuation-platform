# Stage 1: Build & Dependencies
FROM python:3.11-slim as builder

WORKDIR /app
COPY requirements.txt .

# Install build dependencies and python packages
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && pip3 install --user -r requirements.txt \
    && rm -rf /var/lib/apt/lists/*

# Stage 2: Final Runtime
FROM python:3.11-slim

WORKDIR /app

# Install only necessary runtime libraries for Playwright
RUN apt-get update && apt-get install -y \
    curl \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2 \
    && rm -rf /var/lib/apt/lists/*

# Copy python packages from builder
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# Copy application code
COPY . .

# Install Playwright browsers (chromium) and then CLEAN UP
RUN playwright install chromium \
    && playwright install-deps chromium \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

EXPOSE 8501

HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health

ENTRYPOINT ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
