# Use Python image
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Copy requirements
COPY requirements.txt .

RUN pip install --no-cache-dir --default-timeout=1000 \
    torch==2.4.1 \
    --index-url https://download.pytorch.org/whl/cpu

# Install dependencies
RUN pip install --no-cache-dir --default-timeout=1000 -r requirements.txt

# Copy project
COPY . .

# Expose port
EXPOSE 8000

# Run server
CMD ["sh", "-c", "sleep 5 && python wait_for_db.py && python manage.py runserver 0.0.0.0:8000"]
