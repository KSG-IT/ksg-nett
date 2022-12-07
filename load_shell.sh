#!/bin/bash

export $(grep -v '^#' .env | xargs)
source .venv/bin/activate
python manage.py shell
