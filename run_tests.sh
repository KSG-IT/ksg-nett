MODULES="api,economy,internal,login,media,organization,quotes,schedules,users"
poetry run coverage run --source=$MODULES manage.py test
if [ $? -eq 0 ]
then
    coverage report
else
    exit $?
fi
