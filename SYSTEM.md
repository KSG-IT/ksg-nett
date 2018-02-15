# System overview, frameworks and libraries

## General overview

The project is structured as a typical django project, with multiple apps. Currently the directory tree looks as follows:

```
.
├── api/ - App where the public API live 
├── commissions - App for commissions, aka "Verv"
├── common - App for common functionality 
├── CONTRIBUTING.md - Documentation for how to contribute
├── economy - App for all economic functionality
├── internal - Main app for the internal part of the web page. Note that not all internal views live here, but in other apps.
├── ksg_nett - Project root folder.
├── LICENSE - License of project, currently GPL.
├── login - App handling login and authentication.
├── Makefile - Makefile with some handy targets.
├── manage.py - Django manage script.
├── organization - App for organizational structures.
├── quotes - App for quotes.
├── README.md - The primary README.
├── requirements.txt - Dependencies of the project.
├── run_tests.sh - Helper file which run tests and report coverage.
├── schedules - App for schedules and scheduling, i.e. "Vaktlister".
├── SYSTEM.md - StackOverflowException
└── users - App for user functionality, including our own custom AbstractUser implementation.

```

## Backend
We use the full-stack Django-experience. This means that we use Django views, Django routing, the Django ORM, and Django templates.

There are some guidelines, and general tips to be found in this document.

### Models
All models must be defined as a regular Django-ORM model. They are required to:

1. Contain a Meta class
2. With the table name of the class explicitly defined
3. Should follow [general normalization](https://en.wikipedia.org/wiki/Database_normalization) [best practices](http://agiledata.org/essays/dataNormalization.html).
4. Must implement the \_\_str\_\_ method.
5. Should implement the \_\_repr\_\_ method.
6. Should not override the auto-incrementing default primary key. Other unique constrains should be specified explicitly.
7. Must implement the get_absolute_url method.
8. Must be given a DRF ModelSerializer and ModelView, and then be registered on the API.
9. Should specify the following values under the Meta class: `default_related_name`, `verbose_name_plural`
10. Every field should explicitly specifiy some or all the following values: [blank](https://docs.djangoproject.com/en/1.11/ref/models/fields/#blank), [null](https://docs.djangoproject.com/en/1.11/ref/models/fields/#null), [default](https://docs.djangoproject.com/en/1.11/ref/models/fields/#default).


Example:

```python
class Image(models.Model):

    url = models.ImageField(blank=False, null=False)
    name = models.CharField(blank=False, null=False, default="", max_length=128)
    description = models.CharField(blank=True, null=False, default="", max_length=None)

    albums = models.ManyToManyField(Album)

    class Meta:
        db_table = 'image'
        default_related_name = 'images'
        verbose_name_plural = 'images'
```


### Views and urls
There are a few guidelines to writing views as well. There will in effect be three types of views:
1. Pure template-rendering views.
2. Model-updating views
3. Utility views like login, etc.

Examples of the first type:
```
/internal/dashboard
/internal/vaktlister/lyche/
/internal/users
/internal/users/25/
```

Examples of the second type
```
/internal/users/create
/internal/users/25/update
/internal/users/25/delete
/internal/innskudd/343/update
```

Template-rendering views should be as straight forward as possible. They should be named as follows:

1. The leading path of the view not related to the view itself can be ignored. I.e. it is not necessary to include `internal` in the view name for `/internal/dashboard`.
2. Is the view an overview type of view? Like `internal/dashboard`, then it should be declared `dashboard`
3. Is the view a detail type of view? Like `internal/vaktlister/lyche` or `internal/users/25`. Then it should be suffixed with `_detail`, e.g. `users_detail`.
4. Is the view a model-updating view? Then it should be suffixed with the operation it represents: `users_create`, `users_update`, `users_delete`.

Any other view should be named simply after what service it yield / resource it returns. For instance, a view that generates a [jwt-token](https://jwt.io/), situated at `/security/jwt-token` can be named either of `jwt_token`, `generate_jwt_token`, etc.

Views should generally speaking **not** be suffixed with `_view`.

Views that naturally have conflicting names with globals or other methods **can** get a `_view` prefix, or **may** find another prefix or suffix fitting. For example, a view for user login can not simply be named `login` as the Django-internal method for starting a user session is named `login`. Instead of renaming this method, we can call our view
`user_login`. `login_view` would also have been fine.

As is clear, the URLs of a view can easily be determined from what type of view it is.


### Templates

Not too much to say here. The only thing to mention is that there are two base-templates, of which one of them should always be the template you extend your new template with: `base_external.html` and `base_internal.html`.


## Frontend

As previously mentioned, we use Django templates for writing all frontend views.

We currently only target browsers with innate es6 support (for the most part), to help the death of dreaded browsers like Internet Explorer. The actual support may be different, but do not hesitate to use es6 features. Please see [this link](https://kangax.github.io/compat-table/es6/) for a list over which browsers support what. We'd like to support the following browsers:

1. Internet Explorer: None
2. Google Chrome: >= 52
3. Firefox: >= 48
4. Edge >= 14
5. Opera: >= 39
6. Safari: >= 10
7. IOS browser: >= 10
8. Chrome for android >= 52

### Scripting

There should not be a heavy demand for much scripting in the app. There will of course be some need for Javascript. To that effect, we use the following libraries:

1. [es7-shim](https://github.com/es-shims/es7-shim)
2. [moment](https://momentjs.com/docs/)

Apart from those, everything should be plain Javascript.

Scripts used in a template are allowed to be defined in two places:
1. A separate .js file named similarily to the template.
2. A script-tag within the template, as the last tag before `<body>` closes.

Are you used to a simplifying library like jQuery to do all the heavy lifting? Read http://youmightnotneedjquery.com/.

### Styling
All styling is performed using regular CSS3. You should generally speaking not be concerned with vendor-prefixing beyond what is practical for local testing, as this will be taken care of on release by automatic scripts.
