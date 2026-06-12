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
        curl \
        libxml2-dev \
        libxslt1-dev \
        nginx \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

COPY backend /app/backend
COPY ["Preflight Scanner", "/app/Preflight Scanner"]
COPY --from=frontend-build /app/frontend/build /app/frontend/build
COPY deploy/nginx/orb-weaver.conf /etc/nginx/conf.d/default.conf
COPY deploy/docker/start-orb-weaver.sh /usr/local/bin/start-orb-weaver

RUN chmod +x /usr/local/bin/start-orb-weaver \
    && mkdir -p /app/backend/data /app/substrate /run/nginx

EXPOSE 16500 16510

WORKDIR /app/backend

CMD ["start-orb-weaver"]
