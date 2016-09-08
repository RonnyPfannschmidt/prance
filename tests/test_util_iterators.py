# -*- coding: utf-8 -*-
"""Test suite for prance.util.iterators ."""

__author__ = 'Jens Finkhaeuser'
__copyright__ = 'Copyright (c) 2016 Jens Finkhaeuser'
__license__ = 'MIT +no-false-attribs'
__all__ = ()


from prance.util import iterators


def test_empty_dict():
  tester = {}
  frozen = tuple(iterators.reference_iterator(tester))
  assert len(frozen) == 0, 'Found items when it should not have!'


def test_dict_without_references():
  tester = {
    'foo': 42,
    'bar': 'baz',
    'baz': {
      'quux': {
        'fnord': False,
      },
    },
  }
  frozen = tuple(iterators.reference_iterator(tester))
  assert len(frozen) == 0, 'Found items when it should not have!'


def test_dict_with_references():
  tester = {
    'foo': 42,
    'bar': 'baz',
    '$ref': 'root',
    'baz': {
      '$ref': 'branch',
      'quux': {
        'fnord': False,
        '$ref': 'leaf',
      },
    },
  }
  frozen = tuple(iterators.reference_iterator(tester))
  assert len(frozen) == 3, 'Found a different item count than expected!'

  # We have three references with their paths here, but we don't know which
  # order the tuple has them in. Let's go through them all:
  expectations = {
    0: 'root',
    1: 'branch',
    2: 'leaf',
  }
  for key, value, path in iterators.reference_iterator(tester):
    assert value == expectations[len(path)]
