FROM python:3.12-slim-bookworm

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    HOST=0.0.0.0 \
    PORT=8080

RUN python -m pip install --no-cache-dir --upgrade pip \
    && python -m pip install --no-cache-dir uv

ENV VIRTUAL_ENV=/opt/venv
RUN python -m venv "$VIRTUAL_ENV"
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
ENV UV_CACHE_DIR=/tmp/uv-cache

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project --active \
    && rm -rf "$UV_CACHE_DIR"

COPY src ./src

EXPOSE 8080

CMD ["python", "-m", "src.server"]
