# ksg-nett
[![Build Status](https://travis-ci.org/KSG-IT/ksg-nett.svg?branch=develop)](https://travis-ci.org/KSG-IT/ksg-nett)
[![Coverage Status](https://coveralls.io/repos/github/KSG-IT/ksg-nett/badge.svg?branch=develop)](https://coveralls.io/github/KSG-IT/ksg-nett?branch=develop)

This repository contains the source code for [KSG](https://www.samfundet.no/kafe-og-serveringsgjengen)'s web page. The project is written in Django.

## Quickstart

1. Create a new virtualenvironment with pipenv and python 3.6 (instructions below)
2. Install dependencies
3. **Carefully read** [Contribution.md](https://github.com/KSG-IT/ksg-nett/blob/develop/CONTRIBUTING.md) to aid both yourself and others!

## Dependencies
* Django 3.1
* Python 3.8
* Pipenv

## Installation

### Installing dependencies
First [install poetry](https://python-poetry.org/docs/#installation) our dependency and virtual environment manager.

    poetry install
    
### Setting up the database

```
poetry run python manage.py migrate
```

## Running 

```bash
poetry run python manage.py runserver
```

Alternatively one can initiate a pipenv shell session py running
```bash
poetry shell
```

Then commands can be run without the pipenv run command:
```bash
python manage.py runserver
```

## Contributing

First read [CONTRIBUTING.md](https://github.com/KSG-IT/ksg-nett/blob/develop/CONTRIBUTING.md) to understand the various project components. Then check out [SYSTEM.md](https://github.com/KSG-IT/ksg-nett/blob/develop/SYSTEM.md) to understand the various project components.

New to this project? Check out the [last section](https://github.com/KSG-IT/ksg-nett/blob/develop/CONTRIBUTING.md#guides-for-semi-noobs) in CONTRIBUTING.md for some handy guides to get you up to speed 💪
