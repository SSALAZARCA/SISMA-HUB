# Usar una imagen más estable y explícita
FROM python:3.11-slim-bookworm

WORKDIR /app

# Optimizaciones para evitar errores de red y dependencias (exit code 100)
# Se añade --fix-missing y se usan paquetes más estándar para OpenCV en slim
RUN apt-get update --fix-missing && apt-get install -y --no-install-recommends \
    libpq-dev \
    gcc \
    libgl1 \
    libglib2.0-0 \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Variables de entorno por defecto
ENV DATABASE_URL=sqlite:///./data/licenses.db
ENV PORT=10000

EXPOSE 10000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "10000"]
