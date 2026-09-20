FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN mkdir -p data
EXPOSE ${API_PORT:-8002}
CMD uvicorn app.main:app --host 0.0.0.0 --port ${API_PORT:-8002}
