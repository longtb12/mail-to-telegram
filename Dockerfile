FROM python:3.13-slim

WORKDIR /app

RUN apt-get update && apt-get install -y curl unzip && rm -rf /var/lib/apt/lists/*

RUN curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip" && \
    unzip awscliv2.zip && \
    ./aws/install && \
    rm -rf awscliv2.zip aws

COPY requirements.txt ./
COPY . .

RUN pip install --no-cache-dir -r requirements.txt

CMD ["python", "main.py"]
