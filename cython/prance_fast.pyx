# cython: language_level=3, boundscheck=False, wraparound=False
"""Fast Cython helpers and RefResolver for prance reference resolution."""

from urllib import parse

import cython
import os.path

# Resolve-type flags (mirrors prance.util.resolver)
RESOLVE_INTERNAL = 2**1
RESOLVE_HTTP = 2**2
RESOLVE_FILES = 2**3
RESOLVE_ALL = RESOLVE_INTERNAL | RESOLVE_HTTP | RESOLVE_FILES

TRANSLATE_EXTERNAL = 0
TRANSLATE_DEFAULT = 1


cdef bint _is_mapping(object obj):
    return isinstance(obj, dict)


cdef bint _is_sequence_not_str(object obj):
    return isinstance(obj, (list, tuple))


cdef object _json_ref_escape(object part):
    if not isinstance(part, str):
        part = str(part)
    return part.replace("~", "~0").replace("/", "~1")


cdef str _str_path(tuple path_of_obj):
    if not path_of_obj:
        return "/"
    return "/" + "/".join(_json_ref_escape(p) for p in path_of_obj)


cdef object _path_append(tuple path, object part):
    return path + (part,)


# --- fast_deepcopy_json ---------------------------------------------------

cdef object _deepcopy(object obj):
    if obj is None or isinstance(obj, (bool, int, float, str)):
        return obj
    if isinstance(obj, dict):
        return {k: _deepcopy(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_deepcopy(v) for v in obj]
    raise TypeError(
        f"fast_deepcopy_json does not support type {type(obj).__name__}"
    )


def fast_deepcopy_json(obj):
    """Deep-copy JSON-compatible Python objects."""
    return _deepcopy(obj)


cdef object _deepcopy_specs(object value):
    try:
        return _deepcopy(value)
    except TypeError:
        import copy
        return copy.deepcopy(value)


# --- path_get -------------------------------------------------------------

cdef object _path_get_impl(object obj, object path, object defaultvalue, tuple path_of_obj):
    cdef object key, idx_obj
    cdef int idx

    if path is not None and not isinstance(path, (list, tuple)):
        raise TypeError(
            f"Path is a {type(path)}, but must be None or a Collection!"
        )

    if path is None:
        path = ()

    if isinstance(obj, dict):
        if len(path) < 1:
            return obj if obj is not None else defaultvalue
        key = path[0]
        if key not in obj:
            raise KeyError(
                'Object at "{}" does not contain key: {}'.format(
                    _str_path(path_of_obj), key
                )
            )
        return _path_get_impl(
            obj[key], path[1:], defaultvalue, _path_append(path_of_obj, key)
        )

    if isinstance(obj, (list, tuple)):
        if len(path) < 1:
            return obj if obj is not None else defaultvalue
        idx_obj = path[0]
        try:
            idx = int(idx_obj)
        except ValueError:
            raise KeyError(
                'Sequence at "%s" needs integer indices only, but got: %s'
                % (_str_path(path_of_obj), idx_obj)
            )
        if idx < 0 or idx >= len(obj):
            raise IndexError(
                'Index out of bounds for sequence at "%s": %d'
                % (_str_path(path_of_obj), idx)
            )
        return _path_get_impl(
            obj[idx], path[1:], defaultvalue, _path_append(path_of_obj, idx_obj)
        )

    if len(path) > 0:
        raise TypeError(f"Cannot get anything from type {type(obj)}!")
    return obj if obj is not None else defaultvalue


def path_get(obj, path, defaultvalue=None, path_of_obj=()):
    """Get a nested value by path tuple."""
    if path_of_obj is None:
        path_of_obj = ()
    return _path_get_impl(obj, path, defaultvalue, path_of_obj)


# --- path_set -------------------------------------------------------------

_EXIT_PATH = object()


@cython.boundscheck(True)
@cython.wraparound(True)
cdef void _fill_sequence(object seq, int index, object value_index_type):
    if len(seq) > index:
        return
    while len(seq) < index:
        seq.append(None)
    if value_index_type == int:
        seq.append([])
    elif value_index_type is None:
        seq.append(None)
    else:
        seq.append({})


@cython.boundscheck(True)
@cython.wraparound(True)
cdef object _safe_path_component_type(object path, int index):
    try:
        return type(path[index])
    except IndexError:
        return None


@cython.boundscheck(True)
@cython.wraparound(True)
cdef object _path_set_impl(object obj, object path, object value, bint create):
    cdef object idx_obj
    cdef int idx

    if path is not None and not isinstance(path, (list, tuple)):
        raise TypeError(
            f"Path is a {type(path)}, but must be None or a Collection!"
        )

    if len(path) < 1:
        raise KeyError("Cannot set with an empty path!")

    if isinstance(obj, dict):
        if len(path) == 1:
            if not create and path[0] not in obj:
                raise KeyError(f'Key "{path[0]}" not in Mapping!')
            obj[path[0]] = value
        else:
            if create and path[0] not in obj:
                if type(path[1]) == int:
                    obj[path[0]] = []
                else:
                    obj[path[0]] = {}
            _path_set_impl(obj[path[0]], path[1:], value, create)
        return obj

    if isinstance(obj, list):
        idx_obj = path[0]
        try:
            idx = int(idx_obj)
        except ValueError:
            raise KeyError("Sequences need integer indices only.")

        if create:
            _fill_sequence(obj, idx, _safe_path_component_type(path, 1))

        if len(path) == 1:
            obj[idx] = value
        else:
            _path_set_impl(obj[idx], path[1:], value, create)
        return obj

    if isinstance(obj, tuple):
        raise TypeError(f"Sequence is not mutable: {type(obj)}")

    raise TypeError(f"Cannot set anything on type {type(obj)}!")


def path_set(obj, path, value, create=False):
    """Set a nested value by path tuple."""
    return _path_set_impl(obj, path, value, create)


# --- reference_iterator ---------------------------------------------------

def reference_iterator(specs, path=()):
    """Iterate $ref entries in a spec."""
    cdef list path_stack
    cdef list stack
    cdef object container, item, key, value
    cdef int idx, length

    if path is None:
        path_stack = []
    else:
        path_stack = list(path)

    stack = []
    if isinstance(specs, (dict, list, tuple)):
        stack.append(specs)

    while stack:
        item = stack.pop()
        if item is _EXIT_PATH:
            path_stack.pop()
            continue
        if isinstance(item, (str, int)):
            path_stack.append(item)
            continue

        container = item
        if isinstance(container, dict):
            for key in reversed(container):
                value = container[key]
                if key == "$ref":
                    yield "$ref", value, tuple(path_stack)
                elif isinstance(value, (dict, list, tuple)):
                    stack.append(_EXIT_PATH)
                    stack.append(value)
                    stack.append(key)
        elif isinstance(container, (list, tuple)):
            length = len(container)
            for idx in range(length - 1, -1, -1):
                value = container[idx]
                if isinstance(value, (dict, list, tuple)):
                    stack.append(_EXIT_PATH)
                    stack.append(value)
                    stack.append(idx)


# --- URL helpers ----------------------------------------------------------

_urlresource_cache = {}


def _resolution_error():
    from prance.util.url import ResolutionError
    return ResolutionError


def urlresource(url):
    """Return the resource part of a parsed URL."""
    if not isinstance(url, tuple):
        res_list = list(url)[0:3] + [None, None, None]
        return parse.ParseResult(*res_list).geturl()
    key = (url.scheme, url.netloc, url.path)
    cached = _urlresource_cache.get(key)
    if cached is not None:
        return cached
    res_list = list(url)[0:3] + [None, None, None]
    result = parse.ParseResult(*res_list).geturl()
    _urlresource_cache[key] = result
    return result


def _normalize_fragment_path(obj_path):
    def _normalize(path):
        path = path.replace("~1", "/")
        path = path.replace("~0", "~")
        return path

    return [_normalize(p) for p in obj_path]


def absurl(url, relative_to=None):
    """Turn relative file URLs into absolute file URLs."""
    from prance.util.fs import is_pathname_valid, from_posix, abspath
    from prance.util import fs
    from prance.util.exceptions import raise_from

    ResolutionError = _resolution_error()
    parsed = url
    if not isinstance(parsed, tuple):
        if is_pathname_valid(url):
            url = fs.to_posix(url)
        try:
            parsed = parse.urlparse(url)
        except Exception as ex:
            raise_from(_resolution_error(), ex, f"Unable to parse url: {url}")

    if parsed.scheme not in (None, "", "file"):
        return parsed

    reference = relative_to
    if reference and not isinstance(reference, tuple):
        if is_pathname_valid(reference):
            reference = fs.to_posix(reference)
        reference = parse.urlparse(reference)

    result_list = None
    if not parsed.path:
        if not reference or not reference.path:
            raise ResolutionError(
                "Cannot build an absolute file URL from a fragment"
                " without a reference with path!"
            )
        result_list = list(reference)
        result_list[5] = parsed.fragment
    elif os.path.isabs(from_posix(parsed.path)):
        result_list = list(parsed)
        result_list[0] = "file"
    else:
        if not reference:
            raise ResolutionError(
                "Cannot build an absolute file URL from a relative"
                " path without a reference!"
            )
        if reference.scheme not in (None, "", "file"):
            raise ResolutionError(
                "Cannot build an absolute file URL with a non-file reference!"
            )
        result_list = list(parsed)
        result_list[0] = "file"
        result_list[2] = abspath(from_posix(parsed.path), from_posix(reference.path))

    return parse.ParseResult(*result_list)


def split_fragment_reference(base_url, reference):
    """Fast path for fragment-only JSON references."""
    if not reference.startswith("#"):
        return None
    if base_url is None:
        return None

    fragment = reference[1:]
    obj_path = fragment.split("/")
    while len(obj_path) and not obj_path[0]:
        obj_path = obj_path[1:]
    obj_path = _normalize_fragment_path(obj_path)

    return base_url, obj_path


def split_url_reference(base_url, reference):
    """Return a normalized, parsed URL and object path."""
    parsed_url = absurl(reference, base_url)
    obj_path = parsed_url.fragment.split("/")
    while len(obj_path) and not obj_path[0]:
        obj_path = obj_path[1:]
    obj_path = _normalize_fragment_path(obj_path)
    return parsed_url, obj_path


def fetch_url_text(url, cache=None, encoding=None):
    """Fetch URL text content."""
    ResolutionError = _resolution_error()
    if cache is None:
        cache = {}

    url_key = "text_" + urlresource(url)
    entry = cache.get(url_key)
    if entry is not None:
        return entry

    content = None
    content_type = None
    if url.scheme in (None, "", "file"):
        from prance.util.fs import read_file, from_posix
        from prance.util.exceptions import raise_from

        try:
            content = read_file(from_posix(url.path), encoding)
        except FileNotFoundError as ex:
            raise_from(ResolutionError, ex, f"File not found: {url.path}")
    elif url.scheme == "python":
        package = url.netloc
        path = url.path
        if path and path[0] == "/":
            path = path[1:]

        from importlib.resources import files
        from prance.util.fs import read_file, from_posix

        path = files(package).joinpath(path)
        content = read_file(from_posix(path), encoding)
    else:
        import requests

        response = requests.get(url.geturl())
        if not response.ok:
            raise ResolutionError(
                'Cannot fetch URL "%s": %d %s'
                % (url.geturl(), response.status_code, response.reason)
            )
        content_type = response.headers.get("content-type", "text/plain")
        content = response.text

    cache[url_key] = (content, content_type)
    return content, content_type


def fetch_url(url, cache=None, encoding=None, strict=True, copy=True):
    """Fetch the URL and parse the contents."""
    if cache is None:
        cache = {}

    url_key = (urlresource(url), strict)
    entry = cache.get(url_key)
    if entry is not None:
        if copy:
            return entry.copy()
        return entry

    content, content_type = fetch_url_text(url, cache, encoding=encoding)

    from prance.util.formats import parse_spec

    result = parse_spec(content, url.path, content_type=content_type)

    if not strict:
        from prance.util import stringify_keys

        result = stringify_keys(result)

    cache[url_key] = result
    if copy:
        return result.copy()
    return result


# --- RefResolver ----------------------------------------------------------

class RefResolver:
    """Resolve JSON pointers/references in a spec by inlining."""

    def __init__(self, specs, url=None, **options):
        self.__copy_input = options.get("copy_input", True)
        if self.__copy_input:
            self.specs = _deepcopy_specs(specs)
        else:
            self.specs = specs
        self.url = url

        self.__reclimit = options.get("recursion_limit", 1)
        self.__reclimit_handler = options.get("recursion_limit_handler", None)
        if self.__reclimit_handler is None:
            from prance.util.resolver import default_reclimit_handler
            self.__reclimit_handler = default_reclimit_handler

        self.__reference_cache = options.get("reference_cache", {})
        self.__resolve_types = options.get("resolve_types", RESOLVE_ALL)
        self.__resolve_method = options.get("resolve_method", TRANSLATE_DEFAULT)
        self.__encoding = options.get("encoding", None)
        self.__strict = options.get("strict", True)
        self.__fragment_copy = options.get("fragment_copy", True)

        if self.url:
            self.parsed_url = absurl(self.url)
            self._url_key = (urlresource(self.parsed_url), self.__strict)
            if self.specs:
                self.__reference_cache[self._url_key] = self.specs
        else:
            self.parsed_url = self._url_key = None

        self.__soft_dereference_objs = {}
        self.__fragment_cache = {}

    def resolve_references(self):
        """Resolve JSON pointers/references in the spec."""
        self.__fragment_cache.clear()
        self.specs = self._resolve_partial(self.parsed_url, self.specs, (), {})

        if self.__soft_dereference_objs:
            if "components" not in self.specs:
                self.specs["components"] = {}
            if "schemas" not in self.specs["components"]:
                self.specs["components"].update({"schemas": {}})
            self.specs["components"]["schemas"].update(self.__soft_dereference_objs)

    def _split_reference(self, base_url, refstring):
        fragment_ref = split_fragment_reference(base_url, refstring)
        if fragment_ref is not None:
            return fragment_ref
        return split_url_reference(base_url, refstring)

    def _dereferencing_iterator(
        self, base_url, partial, parent_path, recursions, recursion_counts
    ):
        results = []
        for _, refstring, item_path in reference_iterator(partial):
            ref_url, obj_path = self._split_reference(base_url, refstring)

            translate = (self.__resolve_method == TRANSLATE_EXTERNAL) and (
                self.parsed_url.path != ref_url.path
            )

            if self._skip_reference(base_url, ref_url):
                continue

            ref_path = (urlresource(ref_url), tuple(obj_path))
            depth = recursion_counts.get(ref_path, 0)
            next_recursions = recursions + (ref_path,)
            next_counts = dict(recursion_counts)
            next_counts[ref_path] = depth + 1

            if depth >= self.__reclimit:
                ref_value = self.__reclimit_handler(
                    self.__reclimit, ref_url, next_recursions
                )
            else:
                ref_value = self._dereference(
                    ref_url,
                    obj_path,
                    next_recursions,
                    ref_path,
                    depth,
                    next_counts,
                )

            full_path = parent_path + item_path

            if translate:
                schema_url = self._collect_soft_refs(ref_url, obj_path, ref_value)
                results.append(
                    (full_path, {"$ref": "#/components/schemas/" + schema_url})
                )
            else:
                results.append((full_path, ref_value))

        return results

    def _collect_soft_refs(self, ref_url, item_path, value):
        path_parts = ref_url.path.split("/")
        dref_url = path_parts[len(path_parts) - 1] + "_" + "_".join(item_path[1:])
        self.__soft_dereference_objs[dref_url] = value
        return dref_url

    def _skip_reference(self, base_url, ref_url):
        if ref_url.scheme.startswith("http"):
            return (self.__resolve_types & RESOLVE_HTTP) == 0
        elif ref_url.scheme == "file" or ref_url.scheme == "python":
            if base_url.path == ref_url.path:
                return (self.__resolve_types & RESOLVE_INTERNAL) == 0
            return (self.__resolve_types & RESOLVE_FILES) == 0
        else:
            from urllib.parse import urlunparse

            raise ValueError(
                "Scheme {!r} is not recognized in reference URL: {}".format(
                    ref_url.scheme, urlunparse(ref_url)
                )
            )

    def _fetch_cached_contents(self, ref_url):
        url_key = (urlresource(ref_url), self.__strict)
        entry = self.__reference_cache.get(url_key)
        if entry is not None:
            return entry
        return fetch_url(
            ref_url,
            self.__reference_cache,
            self.__encoding,
            self.__strict,
            False,
        )

    def _dereference(
        self, ref_url, obj_path, recursions, ref_path, depth, recursion_counts
    ):
        cache_key = (ref_path, depth)
        cached = self.__fragment_cache.get(cache_key)
        if cached is not None:
            if not self.__fragment_copy and not self.__copy_input:
                return cached
            return _deepcopy_specs(cached)

        contents = self._fetch_cached_contents(ref_url)
        value = contents
        if len(obj_path) != 0:
            ResolutionError = _resolution_error()
            try:
                value = _path_get_impl(value, obj_path, None, ())
            except (KeyError, IndexError, TypeError) as ex:
                raise ResolutionError(
                    f'Cannot resolve reference "{ref_url.geturl()}": {str(ex)}'
                )

        value = _deepcopy_specs(value)
        value = self._resolve_partial(ref_url, value, recursions, recursion_counts)

        self.__fragment_cache[cache_key] = value
        return value

    def _resolve_partial(self, base_url, partial, recursions, recursion_counts):
        changes = dict(
            self._dereferencing_iterator(
                base_url, partial, (), recursions, recursion_counts
            )
        )
        paths = sorted(changes.keys(), key=len)

        for path in paths:
            value = changes[path]
            if len(path) == 0:
                partial = value
            else:
                _path_set_impl(partial, path, value, True)

        return partial
