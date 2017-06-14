# -*- coding: utf-8 -*-
"""This submodule contains a JSON reference resolver."""

__author__ = 'Jens Finkhaeuser'
__copyright__ = 'Copyright (c) 2016-2017 Jens Finkhaeuser'
__license__ = 'MIT +no-false-attribs'
__all__ = ()

import prance.util.url as _url


class RefResolver(object):
  """Resolve JSON pointers/references in a spec."""

  __RS_UNRESOLVED = 0
  __RS_PROCESSING = 1
  __RS_RESOLVED   = 2  # noqa: E221

  __reference_cache = {}

  def __init__(self, specs, url = None):
    """
    Construct a JSON reference resolver.

    The resolved specs are in the `specs` member after a call to
    `resolve_references` has been made.

    If a URL is given, it is used as a base for calculating the absolute
    URL of relative file references.

    :param dict specs: The parsed specs in which to resolve any references.
    :param str url: [optional] The URL to base relative references on.
    """
    import copy
    self.specs = copy.deepcopy(specs)
    self.url = url

    if self.url:
      self.parsed_url = _url.absurl(self.url)
      self._url_key = _url.urlresource(self.parsed_url)
    else:
      self.parsed_url = self._url_key = None

    self.__resolution_status = self.__RS_UNRESOLVED
    self.__recursion_protection = set()

  def _dereferencing_iterator(self, partial, parent_path = ()):
    """
    Iterate over a partial spec, dereferencing all references within.

    Yields the resolved path and value of all items that need substituting.

    :param dict partial: The partial specs to work on.
    :param tuple parent_path: The parent path of the partial specs.
    """
    from .iterators import reference_iterator
    for _, refstring, item_path in reference_iterator(partial):
      # Resolve the reference we're currently dealing with.
      _, ref_path, referenced = self._dereference(refstring)
      ref_path = tuple(ref_path)

      # If the combination of parent path and ref path already exists,
      # we're recursing and shouldn't call _dereferencing_iterator.
      recursion_key = (parent_path, ref_path)
      if recursion_key in self.__recursion_protection:
        raise _url.ResolutionError('Recursion detected trying to resolve "%s"!'
            % (refstring, ))
      self.__recursion_protection.add(recursion_key)

      # If the referenced object contains any reference, yield all the items
      # in it that need dereferencing.
      for inner in self._dereferencing_iterator(referenced, ref_path):
        yield inner

      # We can remove ourselves from the recursion protection again after
      # children are processed.
      self.__recursion_protection.remove(recursion_key)

      # Afterwards also yield the outer item. This makes the
      # _dereferencing_iterator work depth first.
      yield parent_path + item_path, referenced

  def resolve_references(self):
    """Resolve JSON pointers/references in the spec."""
    # If we're currently processing, exit to avoid recursion. If we're already
    # done, also exit. Otherwise start processing.
    if self.__resolution_status in (self.__RS_PROCESSING, self.__RS_RESOLVED):
      return
    self.__resolution_status = self.__RS_PROCESSING

    from dpath import util as dutil
    changes = tuple(self._dereferencing_iterator(self.specs))
    for path, value in changes:
      # Note that it's entirely possible for this set() to happen more than
      # once per path/value pair. If a definition is used twice, and references
      # another definition, then this second definition will be dereferenced
      # with both of the uses of the first. But the value will be identical, so
      # it makes no real changes.
      dutil.set(self.specs, list(path), value)

    self.__resolution_status = self.__RS_RESOLVED

  def _dereference(self, urlstring):
    """
    Dereference the URL string.

    Returns the parsed URL, the object path extraced from the URL, and the
    dereferenced object.
    """
    # Parse URL
    parsed_url = _url.absurl(urlstring, self.parsed_url)

    # In order to start dereferencing anything in the referenced URL, we have
    # to read and parse it, of course.
    parsed_url, referenced = self._fetch_url(parsed_url)
    obj_path = parsed_url.fragment.split('/')
    while len(obj_path) and not obj_path[0]:
      obj_path = obj_path[1:]

    # In this inner parser's specification, we can now look for the referenced
    # object.
    value = referenced
    if len(obj_path) != 0:
      from dpath import util as dutil
      try:
        value = dutil.get(referenced, obj_path)
      except KeyError:
        raise _url.ResolutionError('Cannot resolve reference "%s"!'
            % (urlstring, ))
    return parsed_url, obj_path, value

  def _fetch_url(self, url):
    """
    Fetch the parsed contents of the given URL.

    Uses a caching mechanism so that each URL is only fetched once.
    """
    url_key = _url.urlresource(url)

    # Same URL key means it's the current file
    if url_key == self._url_key:
      return url, self.specs

    # For all other URLs, we might have a cached parser around already.
    resolver = self.__reference_cache.get(url_key, None)

    # If we don't have a parser for the url yet, create and cache one.
    if not resolver:
      resolver = RefResolver(_url.fetch_url(url), url)
      self.__reference_cache[url_key] = resolver

    # Resolve references *after* (potentially) adding the resolver to the
    # cache. This together with the __recursion_protection allows us to detect
    # and report recursions and bad references.
    resolver.resolve_references()

    # That's it!
    return url, resolver.specs
