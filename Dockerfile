FROM python:3.11-slim

WORKDIR /app

RUN groupadd -g 1000 dashcam && \
    useradd --create-home --uid 1000 --gid 1000 --shell /bin/bash dashcam

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/

RUN mkdir -p /app/config /downloads && \
    chown -R dashcam:dashcam /app /downloads

USER dashcam

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

CMD ["python", "-m", "src.main"]

