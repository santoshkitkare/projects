FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
# CMD ["gunicorn", "app:app", "-k", "uvicorn.workers.UvicornWorker", "--workers", "6", "--threads", "4", "--timeout", "300", "--bind", "0.0.0.0:8000"]
CMD ["gunicorn", "app:app", "-k", "uvicorn.workers.UvicornWorker", "--workers", "2", "--timeout", "300", "--bind", "0.0.0.0:8000"]
