# Single stateless image: the game is Python + a handful of static files,
# so there is nothing to compile. The `tools` stage below is the authoring
# toolchain (question generator) and is never what gets deployed.
FROM python:3.13-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

WORKDIR /srv

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

# Least privilege: the app never writes to disk, so it runs as a
# non-root user and the filesystem can be mounted read-only.
RUN useradd --system --uid 10001 --no-create-home pasapalabra

# Authoring toolchain: carries the Anthropic SDK, needs an API key and
# network access, writes into app/data. Built and run only by
# `make rosco` / `make unit` on a developer's machine — the deployed
# image is the `runtime` stage, which has none of this.
FROM base AS tools
COPY requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements-dev.txt
COPY scripts ./scripts
USER 10001
CMD ["python", "-m", "scripts.generate_rosco", "--help"]

# The deployed image. Last on purpose: a plain `docker build .` builds it.
FROM base AS runtime
USER 10001

EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=3s --start-period=10s --retries=5 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=3)"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
