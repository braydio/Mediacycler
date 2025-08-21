
FROM python:3.11-slim

WORKDIR /app

# Install ffmpeg, rsync, SSH
RUN apt-get update && apt-get install -y \
  ffmpeg \
  rsync \
  openssh-client \
  && apt-get clean && rm -rf /var/lib/apt/lists/*

# Copy app code and scripts
COPY app.py /app/app.py
COPY transcode.sh /app/transcode.sh

# Make script executable
RUN chmod +x /app/transcode.sh

# Install Python deps
RUN pip install flask

CMD ["python", "app.py"]

