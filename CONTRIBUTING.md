# Contributing guidelines

## Summary/Algorithm of how to contribute
Are you developing a hotfix?
 1. See [the hotfix branch](#the_hotfix_branch)

Are you developing a feature?
 1. Create a `feature/<domain>/<name>` branch
 2. Make awesome stuff
 3. Create a PR into develop

## Branching

We keep three separate notions of branches:

* The deployment branches master and develop
* The hotfix and release branch
* Feature branches

All commits should be pushed to either the hotfix branch, or a feature branch, and then pull requested into the develop branch.

The develop branch contains the latest deployed test version of the system, and will automatically re-deploy.

The master branch contains the production stable release of the system, and should not be touched by anything but final releases. The master branch will not automatically re-deploy.

The release branch should be used before merging into master. The features will be frozen, i.e. new featuers into develop will not be merged into the release branch for this release.

The hotfix branch should be used when pushing commits that fixes critical bugs. After pushing, a pull request into develop (and then master) should be made.

### Merging and rebasing

There are no ubiquitous rules here, but we follow the following patterns:

1. Has develop or the feature branch you're working on changed while you've made new commits which aren't yet pushed? **Rebase.**
2. Has develop or the feature branch you're working on changed, but you haven't done anything? **fast-forward merge** (`merge --ff-only`).
3. Most other cases: **merge without fast-forward** (`merge --no-ff`).


### Feature branch naming

All feature branches **must** be prefixed with `feature/`, e.g. `feature/upgrade-database`. Feature branches *should* contain at least two levels of nested information; the first signifying in which domain the change/addition is being made, and the second what the change/adition is. Examples:

```
feature/database/add-optimization-indices
feature/user/homepage
feature/economy/innskudd
feature/frontend/update-landingpage
```

Updates which are too broad to fall within one particular domain can avoid such nesting, e.g:

```
feature/security
feature/general-code-cleanup
```

Features that are **large** should have nested feature branches. Say we are developing a new large module called `cryptonite`, which will require tens if not hundred of commits to finish. A sensible way to structure the development of this module would be to have one branch `feature/cryptonite`, in which pull requests with incremental development are being made. For example:

```
feature/cryptonite
|-- feature/cryptonite/add-superman
|-- feature/cryptonite/remove-lex-luthor
|-- feature/cryptonite/optimize
```

When all sub-branches are merged into the main feature branch, a pull request can be made into develop.

Feature branches **may** be deleted after merging. Later updates/fixes/additions to the feature **may** be put in the same branch later on.

### The hotfix branch
Hotfixes should be pushed directly to the hotfix branch. Hotfixes should be tested **thoroughly locally** before being pushed.

After pushing a commit, do the following:
	1. Create a PR to develop.
	2. When the PR is accepted, test the deployed fixes on the test-system.
	3. Create a PR to master.

### The develop branch
The develop branch is automatically deployed to when a CI-passing commit is pushed to it. Thus one should refrain from pushing anything directly to this branch, but rather create a PR from a feature branch.

### Deploying to master
When a new deployment to master is to be made, the following **must** occur:

1. develop is merged into release
2. A pull request is created from release into master
3. Code should be reviewed, and bugs should be fixed.
4. Merge into master, and merge bug fixes back into develop


## Code style and requirements

There are some general requirements to the code.

1. For python we use [pep8](https://www.python.org/dev/peps/pep-0008/). With the exceptions listed [here](https://www.python.org/dev/peps/pep-0008/#a-foolish-consistency-is-the-hobgoblin-of-little-minds), it should be followed slavishly.
2. For javascript, follow the included eslintrc file in the repository.
3. We aim for having roughly 80% test coverage. This means that any new feature should be submitted with the appropriate amount of testing. **Even so-called trivial code should be tested**.
4. Everything should be documented. Specifically, every method and class should have a docstring associated with it. We use the [reST docstring format](#https://www.python.org/dev/peps/pep-0287/)(this is the one Pycharm uses by default). Also, every non-trivial line of code should contain a preceding comment clarifying what the line does.

### Commit contents
Commits should generally speaking be as atomic as possible. **We favor many commits over few**.
Some recommend squashing feature branches into a single commit before merging. We do not do this.

If your style of development is to program continuously without committing until your desired feature works, you are recommended to install a visual tool for staging partial files. Pycharm has this included, as well as Visual Studio Code (Recommended). [You can also use the CLI to do this](https://git-scm.com/book/en/v2/Git-Tools-Interactive-Staging). You can then break up your changes into single atomic commits. You may also in such a scenario considering squashing your commits.

A commit should generally speaking only touch the domain in which the feature branch is specified. If you come across a shortcoming in a feature you depend on, it **must** be adressed in a separate branch and merged before continuing.

### Commit messages
Commits messages **must** contain a subject title. The title **should** be structured as follows:

```
<verb in baseform> <file, files, or module affected> <short description>
```

The subject title should be no more than 75 characters.

The commit **should** contain a description of the commit. The description **should** give some clear indications as to what the commit does, and how it does it. If the commit fixes a bug, the description **must** contain information pointing either to a bug report on github, or a description of why the bug occured. It **should** also contain information regarding how the bug has been fixed. This is not required if the fix is obvious.


Examples:
```
Add economy/util.py

Added a utility file for the economy module. Populated the file with a single
method 'sendAllMyMoneyToTormod'.

```

```
Update frontend/login.py, fixes issue #24

The login_user method did previously not take into account authorization through
the HTTP_AUTHORIZATION header, making all secret-key logins not work.
```

```
Add groups module

Initialized the groups module.
```

```
Fix bug in economy.utils.sendTransaction

The bug occured due to a failure to take into account a potential change of currency.
```

Examples of (very) bad commit messages:

```
Fix stuff
```
```
Whops forgot to commit a file
```
```
A lot of different changes
```
```
More small changes
```

### Migrations and model changes
Every change in a model will generate a new migration file, when `python manage.py makemigrations` is run. The model-change *with* the migration should be commited together in a single atomic commit.

## CI

We use [Travis](https://travis-ci.org/) for continuous integration.

## Versioning

We use [semantic versioning](http://semver.org/) for versioning the system.
We use the following rules for incrementing the system version:

1. Everytime a new module is merged, we increase the MINOR version.
2. Everytime one or more modules receives an improvement in form of **more functionality**, we increase the MINOR version.
3. Everytime a module receives a minor change or bug fix, we increase the PATCH version.
4. (If we ever get this far) API-breaking changes or complete restructuring of the app will increase the MAJOR version.

The official release of the web page will be version 1.0.0.
