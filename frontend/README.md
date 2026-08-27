# Sentinelly — Frontend

React + TypeScript (Vite). Layout de 3 zonas: canales/perfil (sidebar), conversación (centro),
copiloto (derecha). i18n ES/EN con detección automática del idioma del navegador.

## Correr en desarrollo

```bash
cp .env.example .env   # ajustar VITE_API_BASE_URL / VITE_WS_BASE_URL si el backend no está en localhost:8000
npm install
npm run dev
```

Requiere el backend (`backend/`) corriendo y con `CORS_ALLOWED_ORIGINS` incluyendo el origen
de este dev server (por defecto `http://localhost:5173`).

## Build

```bash
npm run build
```
