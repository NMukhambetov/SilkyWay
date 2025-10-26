FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend /app/backend
COPY bot /app/bot
COPY alembic /app/alembic
COPY alembic.ini /app/alembic.ini
COPY check_db_connection.py /app/check_db_connection.py

ENV PYTHONUNBUFFERED=1
