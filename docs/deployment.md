# LEAKGUARD Deployment Guide

## 1. Current Deployment Status

> [!NOTE]
> **Deployment Status:** **Not yet deployed** (Planned for Phase 10: Streamlit Community Cloud and Container Packaging).
> 
> Currently, LEAKGUARD runs strictly as a **local-first** security intelligence console on the operator's machine or on an isolated private server.

---

## 2. Local Production / Intranet Execution

To run LEAKGUARD locally or within an internal network environment:

```bash
# 1. Activate your virtual environment
# Windows (PowerShell):
.venv\Scripts\Activate.ps1
# Linux / macOS:
# source .venv/bin/activate

# 2. Launch the Streamlit application
streamlit run app.py --server.port 8501 --server.headless true
```

### Production Flags for Local Security
- `--server.headless true`: Prevents automatic opening of browser windows on headless servers.
- `--server.enableCORS false`: Disables cross-origin resource sharing when operating on localhost.
- `--server.enableXsrfProtection true`: Enforces cross-site request forgery protection tokens.
- `--browser.gatherUsageStats false`: Completely disables third-party usage telemetry (configured by default in `.streamlit/config.toml`).

---

## 3. Containerized Deployment Strategy (Preview for Phase 10)

For production deployment across isolated Linux environments or container clusters (Docker, Kubernetes):

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Prevent Python from writing .pyc files and buffer stdout
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV LEAKGUARD_DISABLE_TELEMETRY=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install pinned Python dependencies
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY . .

# Run as non-root user
RUN useradd -m -u 1000 leakguard
USER leakguard

EXPOSE 8501

ENTRYPOINT ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

---

## 4. Environment Variables & Runtime Overrides

| Variable Name | Default Value | Description |
| :--- | :--- | :--- |
| `LEAKGUARD_MAX_INPUT_LENGTH` | `20000` | Maximum allowed character length for scanned input payloads. |
| `LEAKGUARD_ENTROPY_THRESHOLD` | `4.5` | Minimum Shannon entropy (bits/char) for generic secret detection. |
| `LEAKGUARD_DISABLE_CSS` | `0` | If set to `1`, disables custom CSS stylesheet injections for no-style mode. |
| `LEAKGUARD_LOG_LEVEL` | `INFO` | Console logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`). |
| `STREAMLIT_BROWSER_GATHER_USAGE_STATS` | `false` | Explicitly disables Streamlit cloud telemetry reporting. |
