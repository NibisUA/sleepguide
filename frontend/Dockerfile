# Build context is the repository root (see docker-compose.prod.yml).
FROM node:22-alpine AS build
WORKDIR /app
COPY frontend/package.json ./
RUN npm install
COPY frontend/ ./
# VITE_API_URL is intentionally unset: the API is served from the same origin under /api
RUN npm run build

FROM caddy:2-alpine
COPY deploy/Caddyfile /etc/caddy/Caddyfile
COPY --from=build /app/dist /srv
