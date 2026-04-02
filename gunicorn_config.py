# Gunicorn configuration file for invsys
import multiprocessing

# Server socket
bind = "127.0.0.1:8007"
backlog = 2048

# Worker processes
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = 'sync'
worker_connections = 1000
timeout = 30
keepalive = 2

# Process naming
proc_name = 'invsys_gunicorn'

# Logging
errorlog = '/root/invsys/logs/gunicorn-error.log'
accesslog = '/root/invsys/logs/gunicorn-access.log'
loglevel = 'info'

# Daemon
daemon = False

# Server mechanics
preload_app = True
