# Use the official Playwright Python image
FROM mcr.microsoft.com/playwright/python:v1.57.0-jammy

WORKDIR /app

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose Flask Port
EXPOSE 920

# Run with Gunicorn (4 workers)
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:920", "app:app"]
