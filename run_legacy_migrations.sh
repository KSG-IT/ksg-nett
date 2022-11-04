#!/bin/bash

python manage.py migrateusers
python manage.py migratequotes
python manage.py migratesummaries
python manage.py migrateworkhistory
python manage.py migratedeposits
python manage.py migeratesessions
