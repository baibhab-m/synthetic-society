FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
RUN pip install --upgrade pip && pip install .[dev]

COPY src ./src
RUN pip install --no-deps -e .

EXPOSE 8765

CMD ["uvicorn", "synthetic_society.server:app", "--host", "0.0.0.0", "--port", "8765"]