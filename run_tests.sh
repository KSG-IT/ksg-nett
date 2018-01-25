MODULES="api,economy,internal,login,media,organization,quotes,schedules,users"
coverage run --source=$MODULES manage.py test
coverage report
