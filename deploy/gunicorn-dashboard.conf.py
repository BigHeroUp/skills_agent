import os

bind = "0.0.0.0:8050"
# DashboardRuntimeState is process-local; keep one web process and use threads.
workers = 1
threads = max(4, int(os.getenv("DASHBOARD_THREADS", "4")))
worker_class = "gthread"
timeout = int(os.getenv("GUNICORN_TIMEOUT_SECONDS", "120"))
graceful_timeout = 30
accesslog = "-"
errorlog = "-"
