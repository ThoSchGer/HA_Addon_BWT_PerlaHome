#!/usr/bin/with-contenv bash
set -euo pipefail

echo "[INFO] Starting BWT Perla Smartmeter Add-on..."
exec python3 -m app.main
