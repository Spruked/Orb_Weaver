FROM node:18-alpine AS frontend-build

WORKDIR /app/frontend

COPY frontend/package*.json ./
RUN npm ci

COPY frontend/ ./
ARG REACT_APP_API_URL=
ENV REACT_APP_API_URL=${REACT_APP_API_URL}
RUN npm run build


FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DATABASE_URL=sqlite:///./data/orb_weaver.db
ENV ORB_WEAVER_SUBSTRATE_ROOT=/app/substrate
ENV PUBLIC_BASE_URL=http://127.0.0.1:16510

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        chromium \
        curl \
        ffmpeg \
        libxml2-dev \
        libxslt1-dev \
        nginx \
        nodejs \
        npm \
        tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

RUN npm install -g chrome-devtools-mcp@1.3.0

COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

COPY backend /app/backend
COPY Orb_Assistant /app/Orb_Assistant
COPY ["Preflight Scanner", "/app/Preflight Scanner"]
COPY --from=frontend-build /app/frontend/build /app/frontend/build
COPY deploy/nginx/orb-weaver.conf /etc/nginx/conf.d/default.conf
COPY deploy/docker/start-orb-weaver.sh /usr/local/bin/start-orb-weaver

RUN chmod +x /usr/local/bin/start-orb-weaver \
    && mkdir -p /app/backend/data /app/substrate /run/nginx

EXPOSE 16500 16510

ENV CHROME_PATH=/usr/bin/chromium
ENV CHROME_BIN=/usr/bin/chromium
ENV CHROME_DEVTOOLS_CLI=chrome-devtools
ENV CHROME_DEVTOOLS_ENABLED=true
ENV CHROME_DEVTOOLS_PUBLIC_ENABLED=false
ENV CHROME_DEVTOOLS_START_ARGS='["--no-sandbox","--disable-dev-shm-usage"]'
ENV TESSERACT_CMD=/usr/bin/tesseract
ENV ORB_ASSISTANT_ROOT=/app/Orb_Assistant
ENV FASTER_WHISPER_STT_URL=http://host.docker.internal:9000/stt
ENV ORB_TTS_CACHE_DIR=/app/backend/data/tts_cache
ENV ORB_TTS_TIMEOUT_SECONDS=120
ENV ORB_TTS_QWEN_URL=http://host.docker.internal:9880/speak
ENV ORB_TTS_QWEN_MODEL=qwen-tts
ENV ORB_TTS_QWEN_VOICE=Cherry
ENV ORB_TTS_QWEN_FORMAT=wav
ENV ORB_TTS_QWEN_PAYLOAD_MODE=generic
ENV ORB_TTS_KOKORO_URL=http://host.docker.internal:8880/v1/audio/speech
ENV ORB_TTS_KOKORO_MODEL=kokoro
ENV ORB_TTS_KOKORO_VOICE=af_heart
ENV ORB_TTS_KOKORO_FORMAT=wav
ENV ORB_TTS_KOKORO_PAYLOAD_MODE=openai

WORKDIR /app/backend

CMD ["start-orb-weaver"]
