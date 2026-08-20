FROM node:18-alpine AS frontend-build

WORKDIR /app/frontend

COPY frontend/package*.json ./
RUN npm ci

COPY frontend/ ./
ARG REACT_APP_API_URL=
ENV REACT_APP_API_URL=${REACT_APP_API_URL}
RUN npm run build


FROM python:3.12-slim

ARG APP_UID=1000
ARG APP_GID=1000

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

RUN groupadd --gid "${APP_GID}" orbweaver \
    && useradd \
        --uid "${APP_UID}" \
        --gid "${APP_GID}" \
        --create-home \
        --shell /usr/sbin/nologin \
        orbweaver

RUN sed -i 's|pid /run/nginx.pid;|pid /tmp/nginx.pid;|' /etc/nginx/nginx.conf \
    && sed -i '/^user /d' /etc/nginx/nginx.conf

RUN mkdir -p \
        /var/lib/nginx/body \
        /var/lib/nginx/proxy \
        /var/lib/nginx/fastcgi \
        /var/lib/nginx/uwsgi \
        /var/lib/nginx/scgi \
        /var/cache/nginx \
        /var/log/nginx \
        /run/nginx \
    && chown -R orbweaver:orbweaver \
        /var/lib/nginx \
        /var/cache/nginx \
        /var/log/nginx \
        /run/nginx

RUN npm install -g chrome-devtools-mcp@1.3.0

COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

COPY backend /app/backend
RUN chown -R orbweaver:orbweaver /app/backend

COPY Orb_Assistant /app/Orb_Assistant
COPY Orb_Vault_System /app/Orb_Vault_System
COPY manufacturing /app/manufacturing
COPY vault_system /app/vault_system
COPY ["Preflight Scanner", "/app/Preflight Scanner"]
COPY --from=frontend-build /app/frontend/build /app/frontend/build
COPY --from=frontend-build /app/frontend/node_modules/playwright /app/node_modules/playwright
COPY --from=frontend-build /app/frontend/node_modules/playwright-core /app/node_modules/playwright-core
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

CMD ["/usr/local/bin/start-orb-weaver"]
