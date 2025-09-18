FROM python:3.10

# Use .dockerignore to exclude unnecessary files (e.g. .git, tests, docs, assets, etc.)

# Copy only requirements.txt and main files to root
COPY requirements.txt ./

# Copy only necessary source files to /src
COPY src/ /src/

WORKDIR /src

# RUN apt-get update && apt-get install -y ffmpeg libsm6 libxext6
RUN pip install --no-cache-dir -r /requirements.txt

RUN chmod 444 main.py
RUN chmod 444 /requirements.txt

ENV PORT 8081

CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 900 main:app