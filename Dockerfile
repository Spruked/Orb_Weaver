FROM node:18-alpine AS frontend-build

WORKDIR /app/frontend

COPY frontend/package*.json ./
RUN npm ci

COPY frontend/ ./
ARG REACT_APP_API_URL=
ENV REACT_APP_API_URL=${REACT_APP_API_URL}
RUN npm run build


FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV ORB_WEAVER_VAULT_ROOT=/app/vault_system
ENV ORB_WEAVER_SUBSTRATE_ROOT=/app/vault_system
ENV DATABASE_URL=sqlite:////app/vault_system/databases/orb_weaver.db
ENV LOCAL_LLM_URL=http://host.docker.internal:11434/api/generate
ENV LOCAL_LLM_MODEL=qwen2.5:3b
ENV LOCAL_LLM_TIMEOUT_SECONDS=60
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
COPY vault_system /app/vault_system
COPY ["Preflight Scanner", "/app/Preflight Scanner"]
COPY --from=frontend-build /app/frontend/build /app/frontend/build
COPY deploy/nginx/orb-weaver.conf /etc/nginx/conf.d/default.conf
COPY deploy/docker/start-orb-weaver.sh /usr/local/bin/start-orb-weaver

RUN chmod +x /usr/local/bin/start-orb-weaver \
    && mkdir -p \
        /app/vault_system/clients \
        /app/vault_system/databases \
        /app/vault_system/posteriori \
        /app/vault_system/reports \
        /app/vault_system/indexes \
        /app/vault_system/manifests \
        /app/vault_system/schemas \
        /app/vault_system/runtime/tts_cache \
        /app/vault_system/runtime/browser_reviews \
        /app/vault_system/runtime/state \
        /app/vault_system/runtime/logs \
        /run/nginx

EXPOSE 16500 16510

ENV CHROME_PATH=/usr/bin/chromium
ENV CHROME_BIN=/usr/bin/chromium
ENV CHROME_DEVTOOLS_CLI=chrome-devtools
ENV CHROME_DEVTOOLS_ENABLED=true
ENV CHROME_DEVTOOLS_PUBLIC_ENABLED=false
ENV CHROME_DEVTOOLS_OUTPUT_ROOT=/app/vault_system/runtime/browser_reviews
ENV CHROME_DEVTOOLS_START_ARGS='["--no-sandbox","--disable-dev-shm-usage"]'
ENV ORB_DESKTOP_MCP_ENABLED=true
ENV ORB_DESKTOP_MCP_ROOT=/app/rdrive_mpc_server
ENV ORB_DESKTOP_MCP_PYTHON=python3.12
ENV ORB_DESKTOP_MCP_TIMEOUT_SECONDS=20
ENV TESSERACT_CMD=/usr/bin/tesseract
ENV ORB_ASSISTANT_ROOT=/app/Orb_Assistant
ENV FASTER_WHISPER_STT_URL=http://host.docker.internal:9000/stt
ENV ORB_TTS_CACHE_DIR=/app/vault_system/runtime/tts_cache
ENV ORB_TTS_TIMEOUT_SECONDS=45
ENV ORB_TTS_QWEN_URL=
ENV ORB_TTS_QWEN_MODEL=qwen-tts
ENV ORB_TTS_QWEN_VOICE=OrbWeaver
ENV ORB_TTS_QWEN_LANGUAGE=English
ENV ORB_TTS_QWEN_INSTRUCT="A warm, confident adult male assistant voice. Clear, calm, lightly theatrical, friendly, and concise."
ENV ORB_TTS_QWEN_FORMAT=wav
ENV ORB_TTS_QWEN_PAYLOAD_MODE=qwen-custom
ENV ORB_TTS_KOKORO_URL=http://host.docker.internal:8880/speak
ENV ORB_TTS_KOKORO_MODEL=kokoro
ENV ORB_TTS_KOKORO_VOICE=am_echo
ENV ORB_TTS_KOKORO_FORMAT=wav
ENV ORB_TTS_KOKORO_PAYLOAD_MODE=kokoro-direct

WORKDIR /app/backend

CMD ["start-orb-weaver"]
