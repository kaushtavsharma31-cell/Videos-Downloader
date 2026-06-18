# Use a lightweight official python image
FROM python:3.10-slim

# Install system dependencies, including ffmpeg for HD stream merging
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg curl && \
    rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements file
COPY requirements.txt .

# Install dependencies (adding gunicorn for production server)
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir gunicorn

# Copy all application files
COPY . .

# Ensure static and templates folders are copied
RUN mkdir -p static templates downloads

# Set environment variables
ENV FLASK_ENV=production
ENV PORT=5000

# Expose server port
EXPOSE 5000

# Start the Flask app using Gunicorn with a higher timeout for long video downloads
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app", "--timeout", "120", "--workers", "2"]
