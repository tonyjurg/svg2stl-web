FROM python:3.14-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HOME=/tmp \
    TMPDIR=/tmp

# The gmsh wheel bundles Gmsh itself but dynamically links these small runtime
# libraries. No desktop session is used by the web application.
RUN apt-get update \
    && apt-get install --no-install-recommends -y libglu1-mesa libgomp1 \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system --gid 10001 svg2stl \
    && useradd --system --uid 10001 --gid svg2stl --home-dir /app svg2stl

WORKDIR /app
COPY pyproject.toml README.md LICENSE ./
COPY app ./app
RUN python -m pip install .

USER 10001:10001
EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/api/health', timeout=3)" || exit 1

# Keep one web worker. Conversion concurrency is controlled inside the app and
# each Gmsh job still runs in its own short-lived child process.
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "1", "--proxy-headers", "--forwarded-allow-ips", "127.0.0.1"]
