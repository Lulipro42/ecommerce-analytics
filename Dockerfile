FROM python:3.11-slim

WORKDIR /app

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copiar e instalar dependencias Python
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copiar todo el código
COPY . .

# El working directory es /app
WORKDIR /app

EXPOSE 8000

CMD ["python", "src/manage.py", "runserver", "0.0.0.0:8000"]