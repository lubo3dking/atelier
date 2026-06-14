# Atelier web app — production image.
# Pure-Python stack; the only system package is DejaVu fonts so Bulgarian
# (Cyrillic) PDFs render (see src/techpack/fonts.py — it finds them at
# /usr/share/fonts/truetype/dejavu/).
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# The host injects ANTHROPIC_API_KEY (and any optional STRIPE_/RESEND_ keys) as
# environment variables. Never bake secrets into the image.
EXPOSE 8000

# $PORT is provided by most hosts (Railway/Render); default to 8000 locally.
CMD ["sh", "-c", "uvicorn src.web:create_app --factory --host 0.0.0.0 --port ${PORT:-8000}"]
