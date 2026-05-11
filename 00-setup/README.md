# 00 — Setup

One-time environment check. Run before anything else.

## Prerequisites

- **Docker** with Compose v2 (`docker compose ...` not `docker-compose`)
- **8 GB RAM** free for the stack (7 containers, peak ~5 GB resident)
- **Python 3.11+** for lab scripts (host, not container)
- **Free Slack workspace** for receiving alerts (Track 02 requires this)

## Run

From the lab root:

```bash
make setup
```

This:

1. Copies `.env.example` → `.env` if missing
2. Pre-pulls all 7 Docker images (saves ~10 min on first `make up`)
3. Runs `verify-docker.py` (checks Docker version, RAM headroom, port availability)

## Per-platform notes

- **macOS:** `bash macos-setup.sh` — checks Docker Desktop is running, suggests increasing memory limit if < 4 GB allocated
- **Linux:** `bash linux-setup.sh` — checks `docker` group membership, suggests `sudo usermod -aG docker $USER` if needed
- **Windows:** `pwsh windows-setup.ps1` — verifies WSL2 + Docker Desktop integration

## Submission checkpoint (5 pts)

Run `python verify-docker.py` and commit its `setup-report.json` output to `submission/`.
