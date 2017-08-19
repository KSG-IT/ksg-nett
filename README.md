# ksg-nett

This repository contains the source code for [KSG](https://www.samfundet.no/kafe-og-serveringsgjengen)'s web page. The project is written in Django.

## Quickstart

Create a new virtualenv with python 3.6, install dependencies, **and read** See [Contribution.md](https://github.com/KSG-IT/ksg-nett/blob/master/CONTRIBUTING.md).

## Dependencies
* Django
* Python 3.6
* virtualenv

## Installation

```bash
virtualenv venv
source venv/bin/activate
pip install -r requirements.txt
```

To initialize the database, run:

```
python manage.py migrate
```

## Running

```
source venv/bin/activate
python manage.py runserver
```

## Contributing
See [Contribution.md](https://github.com/KSG-IT/ksg-nett/blob/master/CONTRIBUTING.md).