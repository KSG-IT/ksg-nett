FROM python:3.8-alpine
ENV PYTHONUNBUFFERED 1

# Runtime dependencies
RUN apk --update --upgrade --no-cache add \
    cairo-dev pango-dev gdk-pixbuf py3-pillow nginx libc-dev binutils gcc curl


RUN apk add --virtual build-deps gcc python3-dev musl-dev \
  g++ make libffi-dev openssl-dev \
  jpeg-dev zlib-dev \
  && apk add postgresql-dev \
  && pip install --no-cache-dir psycopg2

RUN curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/get-poetry.py | python -

COPY poetry.lock pyproject.toml /opt/python/
WORKDIR /opt/python/

RUN $HOME/.poetry/bin/poetry config virtualenvs.create false
RUN $HOME/.poetry/bin/poetry install --no-interaction --no-dev
RUN apk del build-deps

ADD . /opt/python

# Config nginx
RUN rm /etc/nginx/conf.d/default.conf
ADD _build/nginx.conf /etc/nginx/conf.d/nginx.conf

RUN python manage.py collectstatic --noinput

EXPOSE 8000
CMD ["./_build/server_entrypoint.sh"]


