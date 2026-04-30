#!/bin/bash
# ChordTime v2 - Deploy Script para Synology DS216+II

set -e

if [ $# -lt 2 ]; then
    echo "Usage: $0 <NAS-IP> <SSH-PASSWORD>"
    echo "Example: $0 192.168.1.100 MiPassword123"
    exit 1
fi

NAS_IP="$1"
SSH_PASS="$2"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TEMP_DIR="/tmp/chordtime_deploy_$$"

echo "=== ChordTime v2 - Deploy para Synology ==="
echo "NAS: $NAS_IP"

# Create temporary local copy
echo "[1/6] Preparando archivos..."
rm -rf "$TEMP_DIR"
mkdir -p "$TEMP_DIR"
rsync -av --exclude='.git' --exclude='downloads' --exclude='__pycache__' --exclude='*.pyc' \
    "$SCRIPT_DIR/" "$TEMP_DIR/"

# SSH and setup remote directory
echo "[2/6] Conectando al NAS..."
export SSHPASS="$SSH_PASS"
SSH_CMD="sshpass -e ssh -o StrictHostKeyChecking=no admin@$NAS_IP"

$SSH_CMD "mkdir -p /volume1/docker/chordtime/downloads 2>/dev/null || true"

# Transfer files
echo "[3/6] Transferiendo archivos al NAS..."
sshpass -e rsync -avz --delete \
    -e "ssh -o StrictHostKeyChecking=no" \
    "$TEMP_DIR/" "admin@$NAS_IP:/volume1/docker/chordtime/"

# Build Docker image
echo "[4/6] Construyendo imagen Docker (puede tardar varios minutos)..."
$SSH_CMD "cd /volume1/docker/chordtime && docker build -t chordtime:latest . 2>&1 | tail -20"

# Verify image
echo "[5/6] Verificando imagen..."
IMAGE_OK=$($SSH_CMD "docker images chordtime:latest --format '{{.ID}}'" 2>/dev/null || echo "")
if [ -z "$IMAGE_OK" ]; then
    echo "ERROR: La imagen Docker no se construyó correctamente"
    exit 1
fi
echo "Imagen creada: $IMAGE_OK"

# Deploy with docker-compose
echo "[6/6] Desplegando stack..."
# Create updated docker-compose with image instead of build
$SSH_CMD "cat > /volume1/docker/chordtime/docker-compose.yml << 'EOF'
version: '3.8'
services:
  chordtime:
    image: chordtime:latest
    container_name: chordtime-server
    ports:
      - '8193:8193'
    volumes:
      - ./downloads:/downloads
    environment:
      - DOWNLOAD_DIR=/downloads
    restart: unless-stopped
EOF"

$SSH_CMD "cd /volume1/docker/chordtime && docker-compose up -d 2>&1"

# Wait and verify
sleep 5
echo ""
echo "=== Verificando ==="
$SSH_CMD "curl -s http://localhost:8193/api/status || echo 'Server may need a moment...'"

# Cleanup
rm -rf "$TEMP_DIR"

echo ""
echo "=== Deploy completado ==="
echo "Acceso: http://$NAS_IP:8193/chordtimev2.html"
echo ""
echo "Si el servicio no responde, verificá:"
echo "  docker ps"
echo "  docker logs chordtime-server"
echo "  curl http://localhost:8193/api/status"