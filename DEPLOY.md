# ChordTime - Deployment & Maintenance Guide

## Overview

ChordTime is a YouTube chord detection server using **Chord-CNN-LSTM** (via ChordMiniApp backend) with librosa fallback.

### Architecture

```
Browser → saronni.myds.me:8193 → ChordTime Server (Docker)
                                      ├─ yt-dlp (YouTube download + ffmpeg)
                                      └─ ChordMiniApp (container:8080, Chord-CNN-LSTM)
                                             └─ fallback: librosa (local detection)
```

---

## Access

| URL | Purpose |
|-----|---------|
| `http://saronni.myds.me:8193/chordtime.html` | Web frontend |
| `http://localhost:8193/chordtime.html` | Local development (Mac) |
| `http://chordtime-edit.saronni.myds.me` | External chord editor (opens in new tab) |

**No reverse proxy.** Port 8193 is mapped directly from the Docker host. The old nginx proxy (port 80/443 → 8194) was removed (May 2026) because it pointed to the wrong port and caused 504 timeouts.

---

## Repository & Images

| Item | URL/Location |
|------|--------------|
| GitHub Repo | https://github.com/saronni-hub/chordtime (private) |
| Docker Hub Image | `saronni/chordtime:main` |
| CI/CD | `.github/workflows/build-and-push.yml` |
| Synology Docker Path | `/volume2/docker/` |

---

## Frontend Features

### Chord Detection Panel

| Feature | Description |
|---------|-------------|
| 🎤 Buscar Letras | Opens lyricsify.com in new tab |
| ✏️ Editar Acordes | Opens chordtime-edit.saronni.myds.me |
| 🔄 Re-detectar | Re-runs chord detection on preview |
| 🎚️ Transpose | Slider -12 to +12 semitones |
| 📝 Letra LRC | Upload/ paste .lrc lyrics |
| 🔗 Generar JSON | Builds JSON from chords + lyrics |
| ⬇️ Descargar JSON | Downloads merged JSON |
| ⬇️ Descargar MP3 | Full song download + chord detection |

### Stats Display

| Stat | Value | Source |
|------|-------|--------|
| Acordes | Count | API chords[] |
| Duración | mm:ss | API duration |
| BPM | float | ChordMiniApp or librosa |
| **Método** | **Chord-CNN-LSTM** / Librosa / Vista previa | API `source` field |

### Chord Palette

After detection, the section title shows unique chords:
```
🎸 Acordes detectados (63) — Am · F · G · C · Dm · Em
```

---

## Detection Flow

### Primary: Chord-CNN-LSTM (ChordMiniApp)
```
POST audio.mp3 → ChordMiniApp:8080/api/recognize-chords
Response: {"success": true, "chords": [{"start": t, "end": t, "chord": "Am"}]}
Source: "chordmini_local" → displayed as "Chord-CNN-LSTM"
```

### Fallback: librosa (Local)
```
1. Load audio (22kHz mono)
2. HPSS → harmonic component
3. BPM: madmom RNN → fallback librosa.beat_track
4. Chroma CQT → normalize L2 → median smoothing
5. Template matching vs chord patterns (dot product)
6. Threshold: score < 0.30 → "N" (no chord)
Source: "preview" → displayed as "Vista previa"
```

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `CHORDMINI_URL` | `http://chordmini-backend:8080` | ChordMiniApp backend URL |
| `DOWNLOAD_DIR` | `/downloads` | Where to store downloaded audio |
| `PYTHONUNBUFFERED` | `1` | Unbuffered Python output |

---

## Docker Image Details

### Dockerfile (`linux/amd64` only)

| Item | Status |
|------|--------|
| Base | `python:3.12-slim-bookworm` |
| ffmpeg/ffprobe | ✅ Built from yt-dlp FFmpeg-Builds |
| yt-dlp | ✅ `pip install -U yt-dlp` (latest, no [default] extra) |
| librosa | ✅ For fallback detection |
| madmom | ❌ Removed (build failures on PyPI/git) |
| deno | ❌ Removed (not needed for yt-dlp) |
| Cython | ✅ In builder stage only |

### Build Notes

- **Workflow uses `no-cache: true`** to ensure yt-dlp is always latest
- Multi-stage build: builder compiles, runtime is slim
- ffmpeg/ffprobe are copied as **separate binaries** (not one overwriting the other)

---

## yt-dlp Configuration

All yt-dlp commands use:
```
--user-agent "Mozilla/5.0 (Windows NT 10.0; Win64; x64)..."
--no-check-certificates
--no-playlist
--force-ipv4
```

**No** `--extractor-args` (was causing PO token errors with `web/android` clients)
**No** `--js-runtimes deno` (deno not installed)
**No** `-f best` (video downloads, was causing "format not available")

### Preview (90 sec)
```bash
yt-dlp -x --audio-format mp3 --download-sections '*0-90' -o /tmp/yt_preview_XXXXX.mp3 URL
```

### Full Download (audio)
```bash
yt-dlp -x --audio-format mp3 --audio-quality 0 -o /downloads/file.mp3 URL
```

---

## API Endpoints

```
POST /api/yt/preview    # 90s preview + chord detection
POST /api/yt/download   # Full download + chord detection
GET  /api/status        # Server health check
GET  /chordtime.html    # Web frontend
GET  /chordtimev2.html  # Alias (same as chordtime.html)
```

---

## Synology Deploy

### Full Docker Path
```bash
/volume2/@appstore/ContainerManager/usr/bin/docker
```

### Container Run Command
```bash
docker run -d \
  --name chordtime-server \
  --network chordtime_default \
  -p 8193:8193 \
  -e CHORDMINI_URL=http://chordmini-backend:8080 \
  -e DOWNLOAD_DIR=/downloads \
  -v /volume2/docker/chordtime/downloads:/downloads \
  --restart unless-stopped \
  saronni/chordtime:main
```

### Using Docker Compose
```bash
cd /volume2/docker/chordtime
docker-compose pull
docker-compose up -d
```

### Update Script
```bash
bash /volume2/docker/chordtime/scripts/chordtime_update.sh
```

---

## Development (Local Mac)

### Start Server Locally
```bash
cd /Volumes/DiscoExterno/ai-studio/chordtimev2
DOWNLOAD_DIR=/tmp/chordtime_downloads python3 chordtime_server.py
# → http://localhost:8193/chordtime.html
```

### Server Path Resolution
The server checks paths in order:
1. `chordtime.html` (current working directory)
2. `os.path.join(os.path.dirname(__file__), 'chordtime.html')`
3. `/app/chordtime.html` (Docker container)

### Git Push + Deploy Flow
```bash
# 1. Local changes
cd /Volumes/DiscoExterno/ai-studio/chordtimev2
git add -A
git commit -m "Description"
git push

# 2. GitHub Actions builds saronni/chordtime:main

# 3. Deploy to Synology
sshpass -p 'PASSWORD' ssh -o StrictHostKeyChecking=no saronni@saronni.myds.me \
  "/volume2/@appstore/ContainerManager/usr/bin/docker pull saronni/chordtime:main && \
   /volume2/@appstore/ContainerManager/usr/bin/docker stop chordtime-server && \
   /volume2/@appstore/ContainerManager/usr/bin/docker rm chordtime-server && \
   /volume2/@appstore/ContainerManager/usr/bin/docker run -d --name chordtime-server \
     --network chordtime_default -p 8193:8193 \
     -e CHORDMINI_URL=http://chordmini-backend:8080 \
     -e DOWNLOAD_DIR=/downloads \
     saronni/chordtime:main"
```

---

## Troubleshooting

### 504 Gateway Timeout
If accessing through HTTP without port 8193, the request may hit Synology's default nginx (port 80), which doesn't serve ChordTime. **Always use port 8193.**

### ChordTime returns "Vista previa" (not Chord-CNN-LSTM)
ChordMiniApp is down or unreachable. Check:
```bash
docker ps | grep chordmini
docker network inspect chordtime_default | grep -A5 chordmini
curl http://localhost:8080/api/status
```

### YouTube "Requested format is not available"
Try a different video. Some YouTube videos are region-locked, age-restricted, or private.

### ffmpeg not found
The Dockerfile COPY command was fixed to copy ffmpeg and ffprobe as separate binaries:
```dockerfile
COPY --from=builder /usr/local/bin/ffmpeg /usr/local/bin/ffmpeg
COPY --from=builder /usr/local/bin/ffprobe /usr/local/bin/ffprobe
```

### Nginx proxy (legacy, removed May 2026)
The file `/etc/nginx/conf.d/chordtimev2.conf` was deleted because:
- It proxied `/api/yt` to port 8194 (wrong, chordtime runs on 8193)
- Synology's `default_server` on port 80 took precedence anyway
- It caused 504 timeouts during YouTube downloads

---

## File Structure (Repo)

```
chordtime/
├── chordtime_server.py       # Main HTTP server (self-contained)
├── chordtime.html            # Web frontend
├── Dockerfile                # Multi-stage linux/amd64 build
├── docker-compose.yml         # Synology compose config
├── requirements.txt           # Python dependencies
├── .env.example               # Environment template
├── .github/workflows/
│   └── build-and-push.yml     # CI/CD to Docker Hub
├── scripts/
│   └── chordtime_update.sh    # Synology update script
├── README.md                  # Project overview
├── DEPLOY.md                  # This file
└── LICENSE                    # MIT
```

---

## Quick Reference

| Action | Command |
|--------|---------|
| Build locally | `docker build -t chordtime:local .` |
| GitHub Actions | `gh workflow run build-and-push.yml --repo saronni-hub/chordtime` |
| Pull latest | `docker pull saronni/chordtime:main` |
| Restart container | `docker restart chordtime-server` |
| View logs | `docker logs -f chordtime-server` |
| Test API (Synology) | `curl http://saronni.myds.me:8193/api/status` |
| Check running containers | `docker ps --format 'table {{.Names}}\t{{.Status}}'` |
| Test YouTube download | `docker exec chordtime-server yt-dlp -x --audio-format mp3 -o /tmp/test.mp3 'URL'` |

---

## Notes

- Image: **linux/amd64 only** (Synology DS216+II, Intel Celeron N3060)
- Mac (arm64) cannot run the Docker image directly — use local server instead
- ChordMiniApp must be running for Chord-CNN-LSTM detection
- yt-dlp is installed via pip (gets latest on each build due to `no-cache: true`)
- Local chordtime_server.py reads `chordtime.html` from the repo directory
- SSH password: stored in DEPLOY.md locally (not committed to git)