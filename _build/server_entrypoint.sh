echo "Starting server"
exec pipenv run gunicorn ksg_nett.wsgi \
         --workers 3 \
         --error-logfile '-' \
         --log-level INFO \
         --bind=unix:/opt/python/wsgi.sock &
exec nginx -g "pid /tmp/nginx.pid; daemon off;"
