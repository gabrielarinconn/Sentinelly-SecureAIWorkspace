FROM python:3.11-slim

WORKDIR /app

COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY backend/ backend/
COPY prompts/ prompts/

ENV PYTHONPATH=/app
EXPOSE 8000

# El modelo de fastembed (~220MB) se descarga en la primera request/ciclo del worker que lo
# necesite, no en el build de esta imagen — mantiene el build simple; el primer uso del
# copiloto tras un `docker compose up` limpio tarda unos segundos más mientras se cachea.
CMD ["uvicorn", "backend.presentation.api:app", "--host", "0.0.0.0", "--port", "8000"]
