FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY backend /app/backend
COPY bot /app/bot

# Переменные окружения
ENV PYTHONUNBUFFERED=1
