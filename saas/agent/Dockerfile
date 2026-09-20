FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
# Host network needed for mDNS Chromecast discovery
CMD ["python", "-m", "agent.main"]
