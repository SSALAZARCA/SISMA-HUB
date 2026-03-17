FROM python:3.11-slim

WORKDIR /app

# Instalar dependencias del sistema para PostgreSQL y OpenCV
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Variables de entorno por defecto
ENV DATABASE_URL=sqlite:///./data/licenses.db
ENV PORT=10000

EXPOSE 10000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "10000"]
