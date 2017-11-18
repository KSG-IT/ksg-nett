MODULES="api,economy,internal,login,media,organization,schedules,users"
coverage run --source=$MODULES manage.py test
coverage report
