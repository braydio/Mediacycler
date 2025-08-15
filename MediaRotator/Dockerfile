FROM python:3.11-slim

WORKDIR /app

# Install Python dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy MediaRotator source
COPY . ./
RUN chmod +x run_rotator.sh

# Run the rotator on a simple hourly schedule
CMD ["bash", "run_rotator.sh"]
