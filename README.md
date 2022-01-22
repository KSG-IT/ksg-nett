# KSG-nett backend
[![Build Status](https://travis-ci.org/KSG-IT/ksg-nett.svg?branch=develop)](https://travis-ci.org/KSG-IT/ksg-nett)

## Overview
This repository contains the source code for [KSG](https://www.samfundet.no/kafe-og-serveringsgjengen)'s web page. The project is written in Django exposing a graphQL API using graphene. KSG-nett is a two-part webapplication, this being the frontend and requires a fucntioning [frontend](https://www.github.com/KSG-IT/ksg-nett-frontend) instance to be running. Follow the link and the quickstart section over there in addition to here to get everything up and running.

## Quickstart
Dependencies are managed with `poetry`. To run the code do the following

1. Make sure you have python 3.8 available on the computer
2. [install](https://python-poetry.org/docs/#installation) poetry on your computer
3. [Install](https://doc.courtbouillon.org/weasyprint/stable/first_steps.html#installation) Weasyprint (make sure to follow instructions thoroughly before going on to the next step) 
4. Clone and Navigate to this folder
5. Install the dependencies by running `poetry install`
6. Migrate the database with `poetry run python manage.py migrate`
7. Run the projects by running `poetry run python manage.py runserver`

## Other dependencies
We use [black](https://black.readthedocs.io/en/stable/) as a code formatter. We enforce this with the use [pre-commit](https://pre-commit.com/). Make sure to have this installed locally otherwise code formatting will not be automaically applied. 

## Branch formatting guidelines
Usually tasks are assigned through [Shortcut](https://app.shortcut.io/ksg-it/stories/space) stories, with a story type which is either a feature, bug or chore, and a story id. This is used to track progress on the task throughout development. A given branch will automatically get tracked if the branch includes `sc-<story-id>` anywhere in its name.

- Our branches follows a convention of `story-type/sc-<story-id>/branch-name`

So a story which is a bug type, with an id of 666 and a title of "Dashboard renders wrong data" would be named `bug/sc-666/dashboard-renders-wrong-data` or similar.



