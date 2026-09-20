FROM python:3.11-slim

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Persistent data directory
RUN mkdir -p /app/data

EXPOSE ${API_PORT:-8001}

CMD uvicorn app.main:app --host 0.0.0.0 --port ${API_PORT:-8001}
