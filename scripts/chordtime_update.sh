#!/bin/bash
# ChordTime Update Script for Synology
# Usage: bash chordtime_update.sh

set -e

IMAGE="saronni/chordtime:main"
CONTAINER_NAME="chordtime-server"
NETWORK="chordtime_default"
CHORDMINI_URL="http://chordmini-backend:8080"
DOWNLOAD_DIR="/downloads"
PORT="8193"

echo "=========================================="
echo "  ChordTime Update Script"
echo "=========================================="

# Pull latest image
echo "[1/4] Pulling latest image: $IMAGE"
docker pull "$IMAGE"

# Stop and remove old container
echo "[2/4] Stopping old container..."
docker stop "$CONTAINER_NAME" 2>/dev/null || true
docker rm "$CONTAINER_NAME" 2>/dev/null || true

# Start new container
echo "[3/4] Starting new container..."
docker run -d \
  --name "$CONTAINER_NAME" \
  --network "$NETWORK" \
  -p "${PORT}:${PORT}" \
  -e "CHORDMINI_URL=$CHORDMINI_URL" \
  -e "DOWNLOAD_DIR=$DOWNLOAD_DIR" \
  "$IMAGE"

# Verify
echo "[4/4] Verifying..."
sleep 2
STATUS=$(curl -s http://localhost:${PORT}/api/status 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('status','unknown'))" 2>/dev/null || echo "unknown")

if [ "$STATUS" = "ok" ]; then
    echo "✅ ChordTime is running and healthy!"
    echo "   URL: http://localhost:${PORT}/chordtime.html"
    echo "   External: http://saronni.myds.me:${PORT}/chordtime.html"
else
    echo "⚠️  Container started but API not responding. Check logs:"
    echo "   docker logs $CONTAINER_NAME"
fi

echo ""
echo "Done!"