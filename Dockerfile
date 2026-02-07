FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip \
    && pip install -r /app/requirements.txt

COPY . /app

RUN addgroup --system app \
    && adduser --system --ingroup app app \
    && mkdir -p /app/artifacts /app/data \
    && chmod +x /app/docker/entrypoint.sh \
    && chown -R app:app /app

USER app

EXPOSE 8080

CMD ["/app/docker/entrypoint.sh"]
