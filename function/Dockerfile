# Use official Python base image
FROM python:3.13-slim

# Set working directory
WORKDIR /app

# Copy requirements and source code
COPY requirements.txt ./
COPY . .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Run the script
CMD ["python", "main.py"]
