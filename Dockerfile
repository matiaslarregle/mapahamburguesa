# Backend MapaHamburguesa
FROM python:3.11-slim

# Evitar que Python escriba .pyc y buffer de stdout
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Dependencias del sistema (Pillow a veces requiere libjpeg)
RUN apt-get update && apt-get install -y --no-install-recommends \
        libjpeg62-turbo-dev \
        zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

# Primero requirements (mejor cache de Docker)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Código fuente
COPY backend ./backend

EXPOSE 8000

# Producción: usar gunicorn con workers uvicorn
# Dev: usar uvicorn con --reload
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
