# Minimal Dockerfile for headless boBnox
FROM python:3.11-slim

# set a working directory
WORKDIR /app

# install system deps for cairosvg if needed
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libffi-dev \
    libxml2 \
    libxslt1.1 \
    libjpeg-dev \
    libpng-dev \
    && rm -rf /var/lib/apt/lists/*

# copy application files
COPY bobnox.py organize_cli.py ./
COPY assets ./assets

# install python deps
RUN pip install --no-cache-dir cairosvg Pillow || pip install --no-cache-dir Pillow

# create a non-root user for safer container runs
RUN useradd -m bobnox || true
USER bobnox

VOLUME ["/data"]

ENTRYPOINT ["python", "organize_cli.py"]
