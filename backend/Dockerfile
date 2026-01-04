FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Use PORT env var from Railway
ENV PORT=8000
EXPOSE 8000

# Start command - Railway sets PORT env var
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT}
