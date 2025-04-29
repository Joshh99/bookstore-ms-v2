FROM python:3.12-slim

# Install system dependencies for mysqlclient
RUN apt-get update && apt-get install -y \
    gcc \
    default-libmysqlclient-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*


WORKDIR /app

COPY . .
COPY requirements.txt .


RUN pip install --no-cache-dir -r requirements.txt




EXPOSE 80
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80"]