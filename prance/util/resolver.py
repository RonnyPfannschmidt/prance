"""This submodule contains a JSON inlining reference resolver."""

__author__ = "Jens Finkhaeuser"
__copyright__ = "Copyright (c) 2016-2018 Jens Finkhaeuser"
__license__ = "MIT"
__all__ = ()

import os

import prance.util.url as _url
from prance.util.path import path_get, path_set
from .iterators import reference_iterator

try:
    from _prance_rs import fast_deepcopy_json as _rust_deepcopy_json
except ImportError:
    _rust_deepcopy_json = None

try:
    from _prance_rs import RefResolver as _RustRefResolver
    from _prance_rs import resolve_spec as rust_resolve_spec
    from _prance_rs import validate_openapi_spec as rust_validate_openapi_spec
    from _prance_rs import load_openapi_spec_py as rust_load_openapi_spec
    from _prance_rs import parse_and_validate_spec as rust_parse_and_validate_spec
except ImportError:
    _RustRefResolver = None
    rust_resolve_spec = None
    rust_validate_openapi_spec = None
    rust_load_openapi_spec = None
    rust_parse_and_validate_spec = None


def _deepcopy_specs(value):
    if _rust_deepcopy_json is not None:
        try:
            return _rust_deepcopy_json(value)
        except TypeError:
            pass
    import copy

    return copy.deepcopy(value)


#: Resolve internal references
RESOLVE_INTERNAL = 2**1
#: Resolve references to HTTP external files.
RESOLVE_HTTP = 2**2
#: Resolve references to local files.
RESOLVE_FILES = 2**3

#: Copy the schema changing the reference.
TRANSLATE_EXTERNAL = 0
#: Replace the reference with inlined schema.
TRANSLATE_DEFAULT = 1

#: Default, resole all references.
RESOLVE_ALL = RESOLVE_INTERNAL | RESOLVE_HTTP | RESOLVE_FILES


def default_reclimit_handler(limit, parsed_url, recursions=()):
    """Raise prance.util.url.ResolutionError."""
    path = []
    for rc in recursions:
        path.append("{}#/{}".format(rc[0], "/".join(rc[1])))
    path = "\n".join(path)

    raise _url.ResolutionError(
        "Recursion reached limit of %d trying to "
        'resolve "%s"!\n%s' % (limit, parsed_url.geturl(), path)
    )


class _PythonRefResolver:
    """Pure-Python reference resolver used when the Rust extension is absent."""

    def __init__(self, specs, url=None, **options):
        self.__copy_input = options.get("copy_input", True)
        if self.__copy_input:
            self.specs = _deepcopy_specs(specs)
        else:
            self.specs = specs
        self.url = url

        self.__reclimit = options.get("recursion_limit", 1)
        self.__reclimit_handler = options.get(
            "recursion_limit_handler", default_reclimit_handler
        )
        self.__reference_cache = options.get("reference_cache", {})
        self.__resolve_types = options.get("resolve_types", RESOLVE_ALL)
        self.__resolve_method = options.get("resolve_method", TRANSLATE_DEFAULT)
        self.__encoding = options.get("encoding", None)
        self.__strict = options.get("strict", True)
        self.__fragment_copy = options.get("fragment_copy", True)

        if self.url:
            self.parsed_url = _url.absurl(self.url)
            self._url_key = (_url.urlresource(self.parsed_url), self.__strict)

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
        fragment_ref = _url.split_fragment_reference(base_url, refstring)
        if fragment_ref is not None:
            return fragment_ref
        return _url.split_url_reference(base_url, refstring)

    def _dereferencing_iterator(
        self, base_url, partial, path, recursions, recursion_counts
    ):
        for _, refstring, item_path in reference_iterator(partial):
            ref_url, obj_path = self._split_reference(base_url, refstring)

            translate = (self.__resolve_method == TRANSLATE_EXTERNAL) and (
                self.parsed_url.path != ref_url.path
            )

            if self._skip_reference(base_url, ref_url):
                continue

            ref_path = (_url.urlresource(ref_url), tuple(obj_path))
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
                    ref_url, obj_path, next_recursions, ref_path, depth, next_counts
                )

            full_path = path + item_path

            if translate:
                url = self._collect_soft_refs(ref_url, obj_path, ref_value)
                yield full_path, {"$ref": "#/components/schemas/" + url}
            else:
                yield full_path, ref_value

    def _collect_soft_refs(self, ref_url, item_path, value):
        dref_url = ref_url.path.split("/")[-1] + "_" + "_".join(item_path[1:])
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
        url_key = (_url.urlresource(ref_url), self.__strict)
        entry = self.__reference_cache.get(url_key)
        if entry is not None:
            return entry
        return _url.fetch_url(
            ref_url,
            self.__reference_cache,
            self.__encoding,
            self.__strict,
            copy=False,
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
            try:
                value = path_get(value, obj_path)
            except (KeyError, IndexError, TypeError) as ex:
                raise _url.ResolutionError(
                    f'Cannot resolve reference "{ref_url.geturl()}": {str(ex)}'
                )

        value = _deepcopy_specs(value)
        value = self._resolve_partial(ref_url, value, recursions, recursion_counts)

        self.__fragment_cache[cache_key] = value
        return value

    def _resolve_partial(self, base_url, partial, recursions, recursion_counts):
        changes = dict(
            tuple(
                self._dereferencing_iterator(
                    base_url, partial, (), recursions, recursion_counts
                )
            )
        )

        paths = sorted(changes.keys(), key=len)

        for path in paths:
            value = changes[path]
            if len(path) == 0:
                partial = value
            else:
                path_set(partial, path, value, create=True)

        return partial


def recursions_count_from_stack(recursions):
    """Build a ref_path count dict from a recursion stack tuple."""
    counts = {}
    for ref_path in recursions:
        counts[ref_path] = counts.get(ref_path, 0) + 1
    return counts


def _backend_override():
    return os.environ.get("PRANCE_BACKEND", "").strip().lower()


def _select_ref_resolver():
    override = _backend_override()
    if override == "python":
        return _PythonRefResolver
    if override == "rust":
        return _RustRefResolver or _PythonRefResolver
    if _RustRefResolver is not None:
        return _RustRefResolver
    return _PythonRefResolver


def use_rust_pipeline():
    """Return True when the full Rust parse+resolve pipeline should be used."""
    override = _backend_override()
    if override == "python":
        return False
    if rust_resolve_spec is None:
        return False
    return True


def use_rust_validator():
    """Return True when the Rust OpenAPI validator should be preferred."""
    override = _backend_override()
    if override == "python":
        return False
    if rust_validate_openapi_spec is None:
        return False
    return True


RefResolver = _select_ref_resolver()
