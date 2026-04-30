#!/usr/bin/env bash
set -euo pipefail

SERVICE_NAME="lingxing-middleware.service"
SERVICE_SRC="/opt/lingxing-middleware/app/deploy/systemd/${SERVICE_NAME}"
SERVICE_DST="/etc/systemd/system/${SERVICE_NAME}"

echo "[1/6] Check source file..."
if [[ ! -f "${SERVICE_SRC}" ]]; then
  echo "ERROR: ${SERVICE_SRC} not found"
  exit 1
fi

echo "[2/6] Install service file..."
cp "${SERVICE_SRC}" "${SERVICE_DST}"
chmod 644 "${SERVICE_DST}"

echo "[3/6] Reload systemd..."
systemctl daemon-reload

echo "[4/6] Enable on boot..."
systemctl enable "${SERVICE_NAME}"

echo "[5/6] Restart service..."
systemctl restart "${SERVICE_NAME}"

echo "[6/6] Service status..."
systemctl --no-pager --full status "${SERVICE_NAME}" || true
echo
echo "Recent logs:"
journalctl -u "${SERVICE_NAME}" -n 80 --no-pager || true
