#!/usr/bin/with-contenv bash
set -euo pipefail

export PATH="/opt/venv/bin:$PATH"

exec python3 -m app.main
