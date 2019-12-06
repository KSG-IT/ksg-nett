FROM python:3.6-alpine
ENV PYTHONUNBUFFERED 1

# Runtime dependencies
RUN apk --update --upgrade --no-cache add \
    cairo-dev pango-dev gdk-pixbuf py3-pillow nginx libc-dev binutils gcc


RUN apk add --virtual build-deps gcc python3-dev musl-dev \
  g++ make libffi-dev openssl-dev \
  jpeg-dev zlib-dev \
  && apk add postgresql-dev \
  && pip install --no-cache-dir psycopg2

COPY Pipfile /opt/python/Pipfile
COPY Pipfile.lock /opt/python/Pipfile.lock

RUN pip install pipenv
RUN pip install psycopg2

WORKDIR /opt/python/

RUN pipenv sync
RUN apk del build-deps

ADD . /opt/python
# Config nginx
RUN rm /etc/nginx/conf.d/default.conf
ADD _build/nginx.conf /etc/nginx/conf.d/nginx.conf

RUN pipenv run python manage.py collectstatic --noinput

EXPOSE 8000
CMD ["./_build/server_entrypoint.sh"]
