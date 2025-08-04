# Dockerfile specifically for Render deployment
FROM python:3.11-slim

# Update package lists
RUN apt-get update

# Install basic dependencies first
RUN apt-get install -y \
    wget \
    gnupg \
    unzip \
    curl \
    ca-certificates \
    apt-transport-https \
    software-properties-common

# Add Google Chrome repository and key
RUN wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google.list

# Update package lists again after adding Chrome repository
RUN apt-get update

# Install Chrome and its dependencies
RUN apt-get install -y google-chrome-stable

# Install additional Chrome dependencies that might be missing
RUN apt-get install -y \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libc6 \
    libcairo2 \
    libcups2 \
    libdbus-1-3 \
    libexpat1 \
    libfontconfig1 \
    libgcc1 \
    libgconf-2-4 \
    libgdk-pixbuf2.0-0 \
    libglib2.0-0 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libstdc++6 \
    libx11-6 \
    libx11-xcb1 \
    libxcb1 \
    libxcomposite1 \
    libxcursor1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxi6 \
    libxrandr2 \
    libxrender1 \
    libxss1 \
    libxtst6 \
    lsb-release \
    xdg-utils

# Clean up apt cache to reduce image size
RUN rm -rf /var/lib/apt/lists/*

# Set Chrome environment variables
ENV GOOGLE_CHROME_BIN=/usr/bin/google-chrome-stable
ENV CHROME_BIN=/usr/bin/google-chrome-stable

# Verify Chrome installation
RUN google-chrome-stable --version || echo "Chrome version check failed"
RUN ls -la /usr/bin/google-chrome* || echo "Chrome binaries not found"

# Create app directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user for security
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Verify Chrome is accessible as non-root user
RUN google-chrome-stable --version || echo "Chrome not accessible as appuser"

# Expose port
EXPOSE 8000

# Start command (adjust based on your main file)
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "app:app"]
