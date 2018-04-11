# -*- coding: utf-8 -*-
"""This submodule contains a JSON reference resolver."""

__author__ = 'Jens Finkhaeuser'
__copyright__ = 'Copyright (c) 2016-2018 Jens Finkhaeuser'
__license__ = 'MIT +no-false-attribs'
__all__ = ()

import prance.util.url as _url

class RefResolver(object):
  """Resolve JSON pointers/references in a spec."""

  __RS_UNRESOLVED = 0
  __RS_PROCESSING = 1
  __RS_RESOLVED   = 2  # noqa: E221

  # FIXME
  def _default_handler(self, refstring):
    raise _url.ResolutionError('Recursion reached limit of %d trying to '
          'resolve "%s"!' % (self.__reclimit, refstring))


  def __init__(self, specs, url = None, **options):
    """
    Construct a JSON reference resolver.

    The resolved specs are in the `specs` member after a call to
    `resolve_references` has been made.

    If a URL is given, it is used as a base for calculating the absolute
    URL of relative file references.

    :param dict specs: The parsed specs in which to resolve any references.
    :param str url: [optional] The URL to base relative references on.
    :param dict reference_cache: [optional] Reference cache to use. When
        encountering references, nested RefResolvers are created, and this
        parameter is used by the RefResolver hierarchy to create only one
        resolver per unique URL.
        If you wish to use this optimization across distinct RefResolver
        instances, pass a dict here for the RefResolvers you create
        yourself. It's safe to ignore this parameter in other cases.
    :param int recursion_limit: [optional] set the limit on recursive
        references. The default is 0. When the limit is reached, the
        recursion_limit_handler is invoked.
    :param callable recursion_limit_handler: [optional] A callable that
        gets invoked when the recursion_limit is reached. Defaults to
        raising ResolutionError.
    """
    import copy
    self.specs = copy.deepcopy(specs)
    self.url = url

    self.__reference_cache = options.get('reference_cache', {})

    self.__reclimit = options.get('recursion_limit', 1) # FIXME document value

    self.__reclimit_handler = options.get('recursion_limit_handler',
            self._default_handler)

    if self.url:
      self.parsed_url = _url.absurl(self.url)
      self._url_key = _url.urlresource(self.parsed_url)

      # If we have a url, we want to add ourselves to the reference cache
      # - that creates a reference loop, but prevents child resolvers from
      # creating a new resolver for this url.
      self.__reference_cache[self._url_key] = self
    else:
      self.parsed_url = self._url_key = None

    self.__resolution_status = self.__RS_UNRESOLVED

# FIXME tail call optimization
  def _dereferencing_iterator(self, partial, parent_path = (), recursions = ()):
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

      # Count how often the reference path has been recursed into.
      from collections import Counter
      rec_counter = Counter(recursions)

      ref_key = tuple(ref_path)
      if rec_counter[ref_key] >= self.__reclimit:
        # The referenced value may be produced by the handler, or the handler
        # may raise, etc.
        ref_value = self.__reclimit_handler(refstring)
      else:
        # The referenced value is to be used, but let's copy it to avoid
        # building recursive structures.
        from copy import deepcopy
        ref_value = deepcopy(referenced)

      # Full item path
      full_path = parent_path + item_path

      # First yield parent
      yield full_path, ref_value

      # If the referenced object contains any reference, yield all the items
      # in it that need dereferencing.
      for inner in self._dereferencing_iterator(ref_value, full_path, recursions + (ref_key,)):
        yield inner

  def resolve_references(self):
    """Resolve JSON pointers/references in the spec."""
    # If we're currently processing, exit to avoid recursion. If we're already
    # done, also exit. Otherwise start processing.
    if self.__resolution_status in (self.__RS_PROCESSING, self.__RS_RESOLVED):
      return
    self.__resolution_status = self.__RS_PROCESSING

    # Gather changes from the dereferencing iterator - we need to set new
    # values from the outside in, so we have to post-process this a little,
    # sorting paths by path length.
    changes = dict(tuple(self._dereferencing_iterator(self.specs)))
    paths = sorted(changes.keys(), key = len)

    # With the paths sorted, set them to the resolved values.
    from prance.util.path import path_set
    for path in paths:
      value = changes[path]
      path_set(self.specs, list(path), value, create = True)

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
      from prance.util.path import path_get
      try:
        value = path_get(referenced, obj_path)
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
      # FIXME propagate recursion limits *remaining*
      resolver = RefResolver(_url.fetch_url(url), url,
              reference_cache = self.__reference_cache)
      self.__reference_cache[url_key] = resolver

    # Resolve references *after* (potentially) adding the resolver to the
    # cache.
    resolver.resolve_references()

    # That's it!
    return url, resolver.specs
