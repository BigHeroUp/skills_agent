FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN groupadd --system skills && useradd --system --gid skills --create-home skills
WORKDIR /app

COPY requirements.txt ./
RUN python -m pip install --upgrade pip && python -m pip install -r requirements.txt

COPY . .
RUN mkdir -p /app/data/platform /app/data/knowledge_graph /app/data/experience /app/logs \
    && chown -R skills:skills /app

USER skills
EXPOSE 8050 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/health/ready', timeout=3)"

CMD ["gunicorn", "--config", "deploy/gunicorn.conf.py", "platform_api.app:app"]
