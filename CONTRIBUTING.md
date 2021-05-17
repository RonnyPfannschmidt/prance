# Contributing

We love pull requests from everyone. By participating in this project, you
agree to abide by the project [code of conduct].

[code of conduct]: https://github.com/RonnyPfannschmidt/prance/blob/master/CODE_OF_CONDUCT.md

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
$ pytest
```

This runs all test cases.

Run a single test scenario:

```bash
$ pytest tests/test_resolving_parser.py::test_basics
```

Note that tests come in two flavours: one set of tests exercises various package
functionalities. The other set of tests validates examples from OpenAPI's own
repositories; these latter tests can be fairly slow to execute.

To run all tests without these spec validation tests, use:

```bash
$ pytest -k 'not test_zzz_specs.py'
```

To run all tests requiring/not requiring a network connection, use:

```bash
$ pytest -m 'requires_network'
$ pytest -m 'not requires_network'
```

Run tests on multiple Python versions:

```bash
$ tox
```

Run tests on other Python versions:

```bash
$ tox -e py34  # e.g.
```

A simple test coverage report is automatically generated.

### Changelog

We're using [towncrier](https://pypi.org/project/towncrier/) to generate a
changelog. We don't use custom change types, so pick one of `feature`,
`bugfix`, `doc`, `removal`, `misc`.

Create a simple text file in `changelog.d/<issue-or-pr>.<type>`. Write a
concise summary of the change and how it affects users.

For very small changes, use `misc` - the descriptions from that type won't
even be added to the changelog, just a link ot the issue.

Prefer issue numbers over PR numbers, if you have both.

You can run `towncrier --draft` to see how your changes would appear in
the changelog. Running without draft would alter `CHANGES.rst`, so if you
do that, make sure *not* to commit the result. That'll be done on `master`
during release.

## Pull Requests

Push to your fork and submit a pull request.

At this point you're waiting on us. We intend to respond to PRs within a few business days,
but nobody pays us to do so. Please be patient.

We may suggest some changes or improvements or alternatives.

Some things that will increase the chance that your pull request is accepted:

* Write tests.
* Follow our style guide. Run the tests and pre-commit.
* Write a [good commit message][commit].

[commit]: http://tbaggery.com/2008/04/19/a-note-about-git-commit-messages.html
