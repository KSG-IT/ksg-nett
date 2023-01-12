#!/bin/bash
if [ -z ${1+x} ]; then
        echo "Please supply the working directory of the ksg project."
        exit 1
fi

cd $1
source .venv/bin/activate
export $(grep -v '^#' .env | xargs)
.venv/bin/python3.9 manage.py closestalesession