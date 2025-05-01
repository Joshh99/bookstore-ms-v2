FROM python:3.9-slim

# Install system dependencies for mysqlclient
RUN apt-get update && apt-get install -y \
    gcc \
    default-libmysqlclient-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/* 

WORKDIR /app
#install python dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

#copy main file
COPY main.py .

#run the program
CMD ["python", "main.py"]