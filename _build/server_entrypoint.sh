#!/usr/bin/env sh
echo "Starting server"
exec poetry run gunicorn ksg_nett.wsgi \
         --workers 3 \
         --error-logfile '-' \
         --log-level INFO \
         --bind=unix:/opt/python/wsgi.sock &
exec nginx -g "pid /tmp/nginx.pid; daemon off;"
