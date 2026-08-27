FROM node:20-alpine AS build
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
# Vite incrusta estas variables en el bundle en tiempo de BUILD, no de arranque del
# contenedor — deben apuntar a algo que el NAVEGADOR del usuario pueda resolver (localhost),
# nunca al nombre del servicio en la red interna de Docker (ej. "backend:8000" no existe
# fuera de la red de docker compose).
ARG VITE_API_BASE_URL=http://localhost:8000
ARG VITE_WS_BASE_URL=ws://localhost:8000
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
ENV VITE_WS_BASE_URL=$VITE_WS_BASE_URL
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
