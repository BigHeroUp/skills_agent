import os

bind = "0.0.0.0:8080"
workers = max(2, int(os.getenv("API_WORKERS", "2")))
threads = max(2, int(os.getenv("API_THREADS", "4")))
worker_class = "gthread"
timeout = int(os.getenv("GUNICORN_TIMEOUT_SECONDS", "120"))
graceful_timeout = 30
keepalive = 5
accesslog = "-"
errorlog = "-"
capture_output = True
