# Seraphim Trading System - Updated Dockerfile
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DJANGO_SETTINGS_MODULE=seraphim.settings

# Set the working directory to /app
WORKDIR /app

# Install system dependencies including netcat for healthchecks
RUN apt-get update && apt-get install -y \
    cron \
    netcat-traditional \
    build-essential \
    zlib1g-dev \
    libjpeg-dev \
    libpng-dev \
    libfreetype6-dev \
    liblcms2-dev \
    libopenjp2-7-dev \
    libtiff5-dev \
    tk-dev \
    tcl-dev \
    libharfbuzz-dev \
    libfribidi-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt /app/
RUN pip install --trusted-host pypi.python.org -r requirements.txt

# Copy the rest of the working directory contents into the container at /app
COPY . .

# Make entrypoint executable
RUN chmod +x entrypoint.sh

# Expose the port on which the application will run
EXPOSE 8082

# Run the application
CMD ["./entrypoint.sh"]
