FROM python:3.11-slim

WORKDIR /app

# Install dependencies first (layer cache)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source
COPY . .

# Runtime config
ENV PORT=5000
ENV FLASK_DEBUG=0
ENV TRAIN_WINDOW=300

EXPOSE 5000

CMD ["python", "app.py"]
