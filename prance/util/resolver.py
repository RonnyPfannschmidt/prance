# -*- coding: utf-8 -*-
"""This submodule contains a JSON reference resolver."""

__author__ = 'Jens Finkhaeuser'
__copyright__ = 'Copyright (c) 2016-2018 Jens Finkhaeuser'
__license__ = 'MIT +no-false-attribs'
__all__ = ()

import prance.util.url as _url


def default_reclimit_handler(limit, parsed_url):
  """Raise prance.util.url.ResolutionError."""
  raise _url.ResolutionError('Recursion reached limit of %d trying to '
        'resolve "%s"!' % (limit, parsed_url.geturl()))


class RefResolver(object):
  """Resolve JSON pointers/references in a spec."""

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
        references. The default is 1, indicating that an element may be
        refered to exactly once when resolving references. When the limit
        is reached, the recursion_limit_handler is invoked.
    :param callable recursion_limit_handler: [optional] A callable that
        gets invoked when the recursion_limit is reached. Defaults to
        raising ResolutionError. Receives the recursion_limit as the
        first parameter, and the parsed reference URL as the second.
    """
    import copy
    self.specs = copy.deepcopy(specs)
    self.url = url

    self.__reclimit = options.get('recursion_limit', 1)
    self.__reclimit_handler = options.get('recursion_limit_handler',
            default_reclimit_handler)
    self.__reference_cache = options.get('reference_cache', {})

    if self.url:
      self.parsed_url = _url.absurl(self.url)
      self._url_key = _url.urlresource(self.parsed_url)

      # If we have a url, we want to add ourselves to the reference cache
      # - that creates a reference loop, but prevents child resolvers from
      # creating a new resolver for this url.
      if self.specs:
        self.__reference_cache[self._url_key] = self.specs
    else:
      self.parsed_url = self._url_key = None

  def resolve_references(self):
    """Resolve JSON pointers/references in the spec."""
    self.specs = self._resolve_partial(self.parsed_url, self.specs, ())

  def _dereferencing_iterator(self, base_url, partial, path, recursions):
    """
    Iterate over a partial spec, dereferencing all references within.

    Yields the resolved path and value of all items that need substituting.

    :param mixed base_url: URL that the partial specs is located at.
    :param dict partial: The partial specs to work on.
    :param tuple path: The parent path of the partial specs.
    :param tuple recursions: A recursion stack for resolving references.
    """
    from .iterators import reference_iterator
    for _, refstring, item_path in reference_iterator(partial):
      # Split the reference string into parsed URL and object path
      ref_url, obj_path = _url.split_url_reference(base_url, refstring)

      # The reference path is the url resource and object path
      ref_path = (_url.urlresource(ref_url), tuple(obj_path))

      # Count how often the reference path has been recursed into.
      from collections import Counter
      rec_counter = Counter(recursions)
      next_recursions = recursions + (ref_path,)

      if rec_counter[ref_path] >= self.__reclimit:
        # The referenced value may be produced by the handler, or the handler
        # may raise, etc.
        ref_value = self.__reclimit_handler(self.__reclimit, ref_url)
      else:
        # The referenced value is to be used, but let's copy it to avoid
        # building recursive structures.
        ref_value = self._dereference(ref_url, obj_path, next_recursions)

      # Full item path
      full_path = path + item_path

      # First yield parent
      yield full_path, ref_value

  def _dereference(self, ref_url, obj_path, recursions):
    """
    Dereference the URL and object path.

    Returns the dereferenced object.

    :param mixed ref_url: The URL at which the reference is located.
    :param list obj_path: The object path within the URL resource.
    :param tuple recursions: A recursion stack for resolving references.
    :return: A copy of the dereferenced value, with all internal references
        resolved.
    """
    # In order to start dereferencing anything in the referenced URL, we have
    # to read and parse it, of course.
    contents = _url.fetch_url(ref_url, self.__reference_cache)

    # In this inner parser's specification, we can now look for the referenced
    # object.
    value = contents
    if len(obj_path) != 0:
      from prance.util.path import path_get
      try:
        value = path_get(value, obj_path)
      except KeyError:
        raise _url.ResolutionError('Cannot resolve reference "%s"!'
            % (ref_url.geturl(), ))

    # Deep copy value; we don't want to create recursive structures
    import copy
    value = copy.deepcopy(value)

    # Now resolve partial specs
    value = self._resolve_partial(ref_url, value, recursions)

    # That's it!
    return value

  def _resolve_partial(self, base_url, partial, recursions):
    """
    Resolve a (partial) spec's references.

    :param mixed base_url: URL that the partial specs is located at.
    :param dict partial: The partial specs to work on.
    :param tuple recursions: A recursion stack for resolving references.
    :return: The partial with all references resolved.
    """
    # Gather changes from the dereferencing iterator - we need to set new
    # values from the outside in, so we have to post-process this a little,
    # sorting paths by path length.
    changes = dict(tuple(self._dereferencing_iterator(base_url, partial, (),
        recursions)))
    paths = sorted(changes.keys(), key = len)

    # With the paths sorted, set them to the resolved values.
    from prance.util.path import path_set
    for path in paths:
      value = changes[path]
      path_set(partial, list(path), value, create = True)

    return partial
