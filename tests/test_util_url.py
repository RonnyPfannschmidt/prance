# -*- coding: utf-8 -*-
"""Test suite for prance.util.url ."""

__author__ = 'Jens Finkhaeuser'
__copyright__ = 'Copyright (c) 2016-2017 Jens Finkhaeuser'
__license__ = 'MIT +no-false-attribs'
__all__ = ()

import pytest

from prance.util import url


def test_absurl_http():
  test = 'http://foo.bar/asdf/#lala/quux'
  res = url.absurl(test)
  assert res.geturl() == test


def test_absurl_http_fragment():
  base = 'http://foo.bar/asdf/#lala/quux'
  test = '#another'
  res = url.absurl(test, base)
  assert res.scheme == 'http'
  assert res.netloc == 'foo.bar'
  assert res.path == '/asdf/'
  assert res.fragment == 'another'


def test_absurl_file():
  base = 'file:///etc/passwd'
  test = 'group'
  res = url.absurl(test, base)
  assert res.geturl() == 'file:///etc/group'


def test_absurl_absfile():
  test = 'file:///etc/passwd'
  res = url.absurl(test)
  assert res.geturl() == test


def test_absurl_fragment():
  base = 'file:///etc/passwd'
  test = '#frag'
  with pytest.raises(url.ResolutionError):
    url.absurl(test)

  res = url.absurl(test, base)
  assert res.geturl() == 'file:///etc/passwd#frag'


def test_absurl_relfile():
  base = 'http://foo.bar'
  test = 'relative.file'
  with pytest.raises(url.ResolutionError):
    url.absurl(test)
  with pytest.raises(url.ResolutionError):
    url.absurl(test, base)


def test_urlresource():
  parsed = url.absurl('http://foo.bar/asdf?some=query#myfrag')
  res = url.urlresource(parsed)
  assert res == 'http://foo.bar/asdf'


def test_fetch_url_file():
  from prance.util import fs
  content = url.fetch_url(url.absurl(fs.abspath('tests/with_externals.yaml')))
  assert content['swagger'] == '2.0'


def test_fetch_url_http():
  exturl = 'http://finkhaeuser.de/projects/prance/petstore.yaml'\
    '#/definitions/Pet'
  content = url.fetch_url(url.absurl(exturl))
  assert content['swagger'] == '2.0'
