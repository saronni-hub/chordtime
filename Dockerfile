FROM python:3.12-slim-bookworm AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
        xz-utils \
        unzip \
        git \
        build-essential \
        libsndfile1-dev \
        libopenblas-dev \
        liblapack-dev \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir Cython

RUN curl -sL "https://github.com/yt-dlp/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-linux64-gpl.tar.xz" \
        -o /tmp/ffmpeg.tar.xz \
    && mkdir -p /tmp/ffmpeg_extracted \
    && tar -xJf /tmp/ffmpeg.tar.xz -C /tmp/ffmpeg_extracted \
    && cp /tmp/ffmpeg_extracted/ffmpeg-master-latest-linux64-gpl/bin/ffmpeg /usr/local/bin/ \
    && cp /tmp/ffmpeg_extracted/ffmpeg-master-latest-linux64-gpl/bin/ffprobe /usr/local/bin/ \
    && chmod +x /usr/local/bin/ffmpeg /usr/local/bin/ffprobe \
    && rm -rf /tmp/ffmpeg.tar.xz /tmp/ffmpeg_extracted

COPY requirements.txt .
RUN pip install --no-cache-dir librosa numpy soundfile pretty_midi mutagen requests
RUN pip install --no-cache-dir -U "yt-dlp[default]"

FROM python:3.12-slim-bookworm

ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
        git \
        libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /usr/local/bin/ffmpeg /usr/local/bin/ffprobe

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir librosa numpy soundfile pretty_midi mutagen requests
RUN pip install --no-cache-dir -U "yt-dlp[default]"

COPY . .

EXPOSE 8193

CMD ["python", "chordtime_server.py"]