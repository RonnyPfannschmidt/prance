"""This submodule contains a JSON reference translator."""

from collections.abc import MutableMapping
from typing import Dict, Iterator, List, Optional, Tuple, Union
from urllib.parse import ParseResult

import prance.util.url as _url
from prance.util.path import JsonValue, PathElement

__author__ = "Štěpán Tomsa"
__copyright__ = "Copyright © 2021 Štěpán Tomsa"
__license__ = "MIT"
__all__ = ()


def _reference_key(ref_url: ParseResult, item_path: List[PathElement]) -> str:
    """
    Return a portion of the dereferenced URL.

    format - ref-url_obj-path
    """
    return ref_url.path.split("/")[-1] + "_" + "_".join(str(p) for p in item_path[1:])


def _local_ref(path: List[str]) -> Dict[str, str]:
    url = "#/" + "/".join(path)
    return {"$ref": url}


# Underscored to allow some time for the public API to be stabilized.
class _RefTranslator:
    """
    Resolve JSON pointers/references in a spec by translation.

    References to objects in other files are copied to the /components/schemas
    object of the root document, while being translated to point to the the new
    object locations.
    """

    def __init__(self, specs: JsonValue, url: Optional[str]) -> None:
        """
        Construct a JSON reference translator.

        The translated specs are in the `specs` member after a call to
        `translate_references` has been made.

        If a URL is given, it is used as a base for calculating the absolute
        URL of relative file references.

        :param dict specs: The parsed specs in which to translate any references.
        :param str url: [optional] The URL to base relative references on.
        """
        import copy

        self.specs: JsonValue = copy.deepcopy(specs)

        self.__strict: bool = True
        self.__reference_cache: Dict[Tuple[str, bool], JsonValue] = {}
        self.__collected_references: Dict[str, Optional[JsonValue]] = {}

        self.url: Optional[ParseResult]
        if url:
            self.url = _url.absurl(url)
            url_key: Tuple[str, bool] = (_url.urlresource(self.url), self.__strict)

            # If we have a url, we want to add ourselves to the reference cache
            # - that creates a reference loop, but prevents child resolvers from
            # creating a new resolver for this url.
            self.__reference_cache[url_key] = self.specs
        else:
            self.url = None

    def translate_references(self) -> None:
        """
        Iterate over the specification document, performing the translation.

        Traverses over the whole document, adding the referenced object from
        external files to the /components/schemas object in the root document
        and translating the references to the new location.
        """
        # url must be a ParseResult for _translate_partial
        if self.url is None:
            return

        self.specs = self._translate_partial(self.url, self.specs)

        # Add collected references to the root document.
        if self.__collected_references:
            # Type narrow specs to MutableMapping for safe indexing
            if isinstance(self.specs, MutableMapping):
                if "components" not in self.specs:
                    self.specs["components"] = {}
                components = self.specs["components"]
                if isinstance(components, MutableMapping):
                    if "schemas" not in components:
                        components.update({"schemas": {}})
                    schemas = components["schemas"]
                    if isinstance(schemas, MutableMapping):
                        schemas.update(self.__collected_references)

    def _dereference(self, ref_url: ParseResult, obj_path: List[PathElement]) -> JsonValue:
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
        contents = _url.fetch_url(ref_url, self.__reference_cache, strict=self.__strict)  # type: ignore[arg-type]

        # In this inner parser's specification, we can now look for the referenced
        # object.
        value = contents
        if len(obj_path) != 0:
            from prance.util.path import path_get

            try:
                value = path_get(value, obj_path)
            except (KeyError, IndexError, TypeError) as ex:
                raise _url.ResolutionError(
                    f'Cannot resolve reference "{ref_url.geturl()}": {str(ex)}'
                )

        # Deep copy value; we don't want to create recursive structures
        import copy

        value = copy.deepcopy(value)

        # Now resolve partial specs
        value = self._translate_partial(ref_url, value)

        # That's it!
        return value

    def _translate_partial(self, base_url: ParseResult, partial: JsonValue) -> JsonValue:
        changes = dict(tuple(self._translating_iterator(base_url, partial, ())))

        paths = sorted(changes.keys(), key=len)

        from prance.util.path import path_set

        for path in paths:
            value = changes[path]
            if len(path) == 0:
                partial = value
            else:
                path_set(partial, list(path), value, create=True)

        return partial

    def _translating_iterator(self, base_url: ParseResult, partial: JsonValue, path: Tuple[PathElement, ...]) -> Iterator[Tuple[Tuple[PathElement, ...], Dict[str, str]]]:
        from prance.util.iterators import reference_iterator

        for _, ref_string, item_path in reference_iterator(partial):
            # Type narrow ref_string to str for split_url_reference
            if not isinstance(ref_string, str):
                continue

            ref_url, obj_path = _url.split_url_reference(base_url, ref_string)
            full_path = path + item_path

            if self.url is None or ref_url.path == self.url.path:
                # Reference to the root document.
                ref_path = obj_path
            else:
                # Reference to a non-root document.
                ref_key = _reference_key(ref_url, obj_path)
                if ref_key not in self.__collected_references:
                    self.__collected_references[ref_key] = None
                    ref_value = self._dereference(ref_url, obj_path)
                    self.__collected_references[ref_key] = ref_value
                ref_path = ["components", "schemas", ref_key]

            # Convert ref_path to List[str] for _local_ref
            ref_path_str: List[str] = [str(p) for p in ref_path]
            ref_obj = _local_ref(ref_path_str)
            yield full_path, ref_obj
