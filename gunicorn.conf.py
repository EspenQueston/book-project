"""
Gunicorn configuration for DUNO 360 production deployment.
"""
import multiprocessing
import os

# Bind
bind = "0.0.0.0:8000"

# Workers — 2 * CPU cores + 1 is the standard recommendation
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "sync"
threads = 2
timeout = 120

# Logging
accesslog = "/var/log/duno360/gunicorn-access.log"
errorlog = "/var/log/duno360/gunicorn-error.log"
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'

# Process naming
proc_name = "duno360"

# Security
limit_request_line = 4096
limit_request_fields = 100
limit_request_field_size = 8190

# Restart workers gracefully after N requests to prevent memory leaks
max_requests = 1000
max_requests_jitter = 50
