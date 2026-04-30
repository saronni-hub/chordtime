# ChordTime

🎹 Servidor de detección de acordes de YouTube con IA (Chord-CNN-LSTM via ChordMiniApp).

## Características

- **Descarga de audio** desde YouTube (yt-dlp + ffmpeg)
- **Detección de acordes** mediante Chord-CNN-LSTM (modelo de deep learning)
- **Transposición** matemática de acordes
- **API REST** para integración con otras aplicaciones
- **Frontend web** para preview rápido

## Requisitos

- Docker (linux/amd64)
- Docker Compose
- ChordMiniApp backend ejecutándose en `chordmini-backend:8080`

## Configuración Rápida

### 1. Variables de entorno

```bash
cp .env.example .env
# Editar .env según necesidad
```

### 2. Ejecutar con Docker Compose

```bash
# development (build local)
docker-compose up --build

# production (usar imagen de Docker Hub)
docker-compose up -d
```

### 3. Acceder

- Frontend: `http://localhost:8193/chordtime.html`
- API: `http://localhost:8193/api/status`

## API Endpoints

### Preview YouTube
```bash
POST /api/yt/preview
{
  "url": "https://www.youtube.com/watch?v=...",
  "transpose": 0,
  "detect": true
}
```

### Status
```bash
GET /api/status
```

## Estructura del Proyecto

```
chordtime/
├── chordtime_server.py    # Servidor principal (Python HTTP)
├── chordtime.html         # Frontend web
├── config.py              # Configuración
├── requirements.txt       # Dependencias Python
├── Dockerfile             # Imagen Docker
├── docker-compose.yml     # Orquestación
├── .env.example           # Variables de entorno (template)
└── .github/
    └── workflows/
        └── build-and-push.yml  # CI/CD (Docker Hub)
```

## Docker Hub

Imagen pública: [saronni-hub/chordtime](https://hub.docker.com/r/saronni-hub/chordtime)

```bash
docker pull saronni-hub/chordtime:latest
```

## Desarrollo

### Build local
```bash
docker build -t chordtime:local .
```

### Variables de entorno para desarrollo

| Variable | Descripción | Default |
|----------|-------------|---------|
| `CHORDMINI_URL` | URL del backend ChordMiniApp | `http://localhost:8080` |
| `DOWNLOAD_DIR` | Directorio para descargas | `/downloads` |

## Notas

- El servidor espera que **ChordMiniApp** esté disponible en la URL configurada via `CHORDMINI_URL`
- Si ChordMiniApp no está disponible, se usa detección local (librosa + madmom) como fallback
- Puerto 8193 mapeado al host para acceso externo

## Licencia

MIT