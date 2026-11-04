FROM python:3.8-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --progress-bar off -r requirements.txt

COPY app/ app/
COPY data/ data/

RUN useradd --create-home --uid 1000 appuser \
    && mkdir -p /app/reports \
    && chown -R appuser:appuser /app

USER appuser

ENTRYPOINT ["python", "-m", "app.main"]
CMD ["--source", "demo"]
