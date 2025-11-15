"""
Defines Mixins for parsers.

The Mixins are here mostly for separation of concerns.
"""

from typing import Any, Optional, cast

__author__ = "Jens Finkhaeuser"
__copyright__ = "Copyright (c) 2016-2018 Jens Finkhaeuser"
__license__ = "MIT"
__all__ = ()


class CacheSpecsMixin:
    """
    CacheSpecsMixin helps determine if self.specification changed.

    It does so by caching a shallow copy on-demand.
    """

    # This attribute is expected to be provided by the class using this mixin
    specification: Any

    __CACHED_SPECS = "__cached_specs"

    def specs_updated(self) -> bool:
        """
        Test if self.specficiation changed.

        :return: Whether the specs changed.
        :rtype: bool
        """
        # Cache specs and return true if no specs have been cached
        if not getattr(self, self.__CACHED_SPECS, None):
            setattr(self, self.__CACHED_SPECS, self.specification.copy())
            return True

        # If specs have been cached, compare them to the current
        # specs.
        cached = getattr(self, self.__CACHED_SPECS)
        if cached != self.specification:
            setattr(self, self.__CACHED_SPECS, self.specification.copy())
            return True

        # Return false if they're the same
        return False


class YAMLMixin(CacheSpecsMixin):
    """
    YAMLMixin returns a YAML representation of the specification.

    It uses :py:class:`CacheSpecsMixin` for lazy evaluation.
    """

    __YAML = "__yaml"

    def yaml(self) -> str:
        """
        Return a YAML representation of the specifications.

        :return: YAML representation.
        :rtype: dict
        """
        # Query specs_updated first to start caching
        if self.specs_updated() or not getattr(self, self.__YAML, None):
            import yaml  # type: ignore[import-untyped]

            setattr(self, self.__YAML, yaml.dump(self.specification))
        return cast(str, getattr(self, self.__YAML))


class JSONMixin(CacheSpecsMixin):
    """
    JSONMixin returns a JSON representation of the specification.

    It uses :py:class:`CacheSpecsMixin` for lazy evaluation.
    """

    __JSON = "__json"

    def json(self) -> str:
        """
        Return a JSON representation of the specifications.

        :return: JSON representation.
        :rtype: dict
        """
        # Query specs_updated first to start caching
        if self.specs_updated() or not getattr(self, self.__JSON, None):
            import json

            setattr(self, self.__JSON, json.dumps(self.specification))
        return cast(str, getattr(self, self.__JSON))
