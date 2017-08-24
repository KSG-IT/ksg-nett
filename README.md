# ksg-nett

This repository contains the source code for [KSG](https://www.samfundet.no/kafe-og-serveringsgjengen)'s web page. The project is written in Django.

## Quickstart

1. Create a new virtualenv with python 3.6 (instructions below)
2. Install dependencies
3. **Carefully read** [Contribution.md](https://github.com/KSG-IT/ksg-nett/blob/develop/CONTRIBUTING.md) to aid both yourself and others!

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
See [CONTRIBUTING.md](https://github.com/KSG-IT/ksg-nett/blob/develop/CONTRIBUTING.md), and then [SYSTEM.md](https://github.com/KSG-IT/ksg-nett/blob/develop/SYSTEM.md).