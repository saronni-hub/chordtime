# ChordTime - Deployment & Maintenance Guide

## Overview

ChordTime is a YouTube chord detection server that uses **Chord-CNN-LSTM** model (via ChordMiniApp backend) for high-quality chord recognition.

### Architecture

```
User → ChordTime Server (Synology:8193) → ChordMiniApp (Synology:8080)
                      ↓
              YouTube Download (yt-dlp)
                      ↓
              Audio Analysis (Chord-CNN-LSTM)
                      ↓
              Chord Response (JSON)
```

### Components

| Component | Location | Purpose |
|-----------|----------|---------|
| `chordtime_server.py` | Synology `/app/` | Main HTTP server |
| `chordtime.html` | Synology `/app/` | Web frontend |
| ChordMiniApp | `chordmini-backend:8080` | Chord detection (Chord-CNN-LSTM model) |
| Docker Network | `chordtime_default` | Container communication |

---

## Repository & Images

| Item | URL/Location |
|------|--------------|
| GitHub Repo | https://github.com/saronni-hub/chordtime |
| Docker Hub Image | `saronni/chordtime:main` |
| Synology Docker Path | `/volume2/docker/` |

---

## Updating ChordTime (Step by Step)

### When you make code changes:

**1. On your Mac (local development):**
```bash
cd /Volumes/DiscoExterno/ai-studio/chordtimev2

# Edit files (chordtime_server.py, Dockerfile, etc.)

# Commit and push
git add -A
git commit -m "Your change description"
git push
```

**2. GitHub Actions builds automatically:**
- Goes to: https://github.com/saronni-hub/chordtime/actions
- Builds `saronni/chordtime:main` and `saronni/chordtime:<commit-sha>`
- Takes ~5-10 minutes

**3. On Synology (update the running container):**
```bash
ssh saronni@saronni.myds.me

# Pull new image
docker pull saronni/chordtime:main

# Stop and remove old container
docker stop chordtime-server
docker rm chordtime-server

# Start new container
docker run -d \
  --name chordtime-server \
  --network chordtime_default \
  -p 8193:8193 \
  -e CHORDMINI_URL=http://chordmini-backend:8080 \
  -e DOWNLOAD_DIR=/downloads \
  saronni/chordtime:main
```

**Or use the update script:**
```bash
ssh saronni@saronni.myds.me "/volume2/docker/chordtime_update.sh"
```

---

## Creating a New Release (Versioned)

### On your Mac:

```bash
cd /Volumes/DiscoExterno/ai-studio/chordtimev2

# Create git tag
git tag -a v2.1.0 -m "Description of release"

# Push tag (triggers GitHub Actions)
git push origin v2.1.0
```

GitHub Actions will build and push:
- `saronni/chordtime:v2.1.0` (versioned)
- `saronni/chordtime:latest` (latest)

### On Synology to use versioned release:
```bash
docker pull saronni/chordtime:v2.1.0
# Then restart container with that tag
```

---

## Docker Compose (Synology)

Location: `/volume2/docker/chordtime/docker-compose.yml`

```yaml
version: '3.8'

services:
  chordtime:
    image: saronni/chordtime:main
    container_name: chordtime-server
    platform: linux/amd64
    ports:
      - "8193:8193"
    environment:
      - CHORDMINI_URL=http://chordmini-backend:8080
      - DOWNLOAD_DIR=/downloads
    volumes:
      - ./downloads:/downloads
    networks:
      - chordtime_network
    restart: unless-stopped

networks:
  chordtime_network:
    name: chordtime_default
    external: true
```

To update using docker-compose:
```bash
cd /volume2/docker/chordtime
docker-compose pull
docker-compose up -d
```

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `CHORDMINI_URL` | `http://chordmini-backend:8080` | ChordMiniApp backend URL |
| `DOWNLOAD_DIR` | `/downloads` | Where to store downloaded audio |

---

## API Endpoints

### Preview YouTube
```
POST /api/yt/preview
{
  "url": "https://www.youtube.com/watch?v=...",
  "transpose": 0,
  "detect": true
}
```

### Status
```
GET /api/status
```

### Access
- Local: http://localhost:8193/chordtime.html
- External: http://saronni.myds.me:8193/chordtime.html

---

## Synology Containers

| Container | Purpose | Port |
|-----------|---------|------|
| `chordtime-server` | ChordTime HTTP server | 8193 |
| `chordmini-backend` | Chord detection (Chord-CNN-LSTM) | 8080 |

Both must be on the same Docker network (`chordtime_default`).

### Check container status:
```bash
ssh saronni@saronni.myds.me "docker ps --format 'table {{.Names}}\t{{.Status}}'"
```

### View logs:
```bash
ssh saronni@saronni.myds.me "docker logs chordtime-server --tail 20"
ssh saronni@saronni.myds.me "docker logs chordmini-backend --tail 20"
```

---

## Troubleshooting

### ChordTime returns "preview" instead of "chordmini_local"

**Cause:** chordtime-server can't reach chordmini-backend

**Fix:**
```bash
# Check both containers are running
docker ps | grep chord

# Check they're on the same network
docker network inspect chordtime_default

# If not, connect them:
docker network connect chordtime_default chordmini-backend
docker restart chordtime-server
```

### YouTube download fails

Check:
1. Network connectivity from Synology
2. `docker logs chordtime-server | grep -i download`

### Chord detection fails / no chords detected

1. Check ChordMiniApp is running: `curl http://localhost:8080/api/status`
2. If down, restart: `docker restart chordmini-backend`

---

## GitHub Secrets

To modify secrets (if Docker Hub credentials change):

1. Go to: https://github.com/saronni-hub/chordtime/settings/secrets/actions
2. Update:
   - `DOCKERHUB_USERNAME` = `saronni`
   - `DOCKERHUB_TOKEN` = Your Docker Hub access token

---

## File Structure (in repo)

```
chordtime/
├── chordtime_server.py    # Main server
├── chordtime.html         # Web interface
├── Dockerfile             # Multi-stage build (amd64)
├── docker-compose.yml     # Compose for production
├── requirements.txt       # Python dependencies
├── .env.example           # Environment template
├── .github/
│   └── workflows/
│       └── build-and-push.yml  # CI/CD to Docker Hub
├── README.md             # Project overview
└── LICENSE               # MIT
```

---

## Quick Reference

| Action | Command |
|--------|---------|
| Pull latest | `docker pull saronni/chordtime:main` |
| Restart container | `docker restart chordtime-server` |
| View logs | `docker logs -f chordtime-server` |
| Test API | `curl http://localhost:8193/api/status` |
| Test from Mac | `curl http://saronni.myds.me:8193/api/status` |

---

## Notes

- Image is built for **linux/amd64 only** (Synology DS216+II)
- Mac (arm64) can't run the container locally
- ChordMiniApp must be running before ChordTime for chord detection
- If ChordMiniApp is down, ChordTime falls back to local librosa detection