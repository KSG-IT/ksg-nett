#!/usr/bin/env sh
echo "Starting server"
exec /home/ubuntu/.poetry/bin/poetry run gunicorn ksg_nett.wsgi \
         --workers 3 \
	 --env "PROD=1" \
         --error-logfile '-' \
         --log-level INFO \
         --bind=unix:/opt/ksg/wsgi.sock;
