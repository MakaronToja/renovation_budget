# Dockerfile
FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
CMD ["uvicorn", "renovation_cost_tracker.main:create_app", "--host", "0.0.0.0", "--port", "8000"]

