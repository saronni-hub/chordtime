# ChordTime

🎹 Servidor de detección de acordes de YouTube con IA (Chord-CNN-LSTM via ChordMiniApp).

## Quick Start

```bash
# Pull from Docker Hub
docker pull saronni/chordtime:main

# Run
docker run -d --name chordtime-server -p 8193:8193 \
  -e CHORDMINI_URL=http://chordmini-backend:8080 \
  -e DOWNLOAD_DIR=/downloads \
  saronni/chordtime:main

# Access
open http://localhost:8193/chordtime.html
```

## Documentation

- **[DEPLOY.md](DEPLOY.md)** - Complete deployment & maintenance guide
- **[LICENSE](LICENSE)** - MIT License

## Features

- **Descarga de audio** desde YouTube (yt-dlp + ffmpeg)
- **Detección de acordes** mediante Chord-CNN-LSTM (modelo de deep learning)
- **API REST** para integración con otras aplicaciones
- **Frontend web** para preview rápido

## Tech Stack

- Python 3.12
- Docker (linux/amd64)
- GitHub Actions → Docker Hub (CI/CD)

## Repository

- **GitHub:** https://github.com/saronni-hub/chordtime
- **Docker Hub:** `saronni/chordtime`
- **Workflow:** `.github/workflows/build-and-push.yml`

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `CHORDMINI_URL` | `http://chordmini-backend:8080` | ChordMiniApp backend |
| `DOWNLOAD_DIR` | `/downloads` | Download directory |

## API Endpoints

```bash
# Status
GET /api/status

# Preview YouTube
POST /api/yt/preview
{"url": "https://youtube.com/watch?v=...", "transpose": 0, "detect": true}
```

## Development

```bash
# Clone
git clone https://github.com/saronni-hub/chordtime.git
cd chordtime

# Build locally
docker build -t chordtime:local .

# Run locally
docker-compose up --build
```