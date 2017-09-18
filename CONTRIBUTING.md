# Contributing

We love pull requests from everyone. By participating in this project, you
agree to abide by the project [code of conduct].

[code of conduct]: https://github.com/jfinkhaeuser/prance/blob/master/CODE_OF_CONDUCT.md

Fork, then clone the repo:

    git clone git@github.com:your-username/prance.git

## Setup

Use [virtualenv](http://docs.python-guide.org/en/latest/dev/virtualenvs/)
to create a virtual environment and change to it or not, as you see fit.

Then install the requirements:

```bash
$ pip install -r requirements.txt
```

## Documentation

After setup, run the following to generate documentation:

```bash
$ python setup.py build_sphinx
```

## Development

### Test Execution

Run the whole test suite:

```bash
$ python setup.py test
```

This runs all test cases, and also [flake8](http://flake8.pycqa.org/en/latest/)
with our project specific style guide configuration.

Run a single test scenario:

```bash
$ pytest tests/test_resolving_parser.py::test_basics
```

Run tests on multiple Python versions:

```bash
$ tox
```

Run tests on Python 2.7:

```bash
$ tox -e py27
```

A simple test coverage report is automatically generated.

## Pull Requests

Push to your fork and [submit a pull request][pr].

[pr]: https://github.com/jfinkhaeuser/prance/compare/

At this point you're waiting on us. We intend to respond to PRs within a few business days,
but nobody pays us to do so. Please be patient.

We may suggest some changes or improvements or alternatives.

Some things that will increase the chance that your pull request is accepted:

* Write tests.
* Follow our style guide. Running the tests runs flake8, our style guide checker.
* Write a [good commit message][commit].

[commit]: http://tbaggery.com/2008/04/19/a-note-about-git-commit-messages.html
