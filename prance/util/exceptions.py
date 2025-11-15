"""This submodule contains helpers for exception handling."""
from typing import Optional
from typing import Type

__author__ = "Jens Finkhaeuser"
__copyright__ = "Copyright (c) 2018,2019 Jens Finkhaeuser"
__license__ = "MIT"
__all__ = ()


# Raise the given exception class from the caught exception, preserving
# stack trace and message as much as possible.
def raise_from(
    klass: type[BaseException],
    from_value: BaseException | None,
    extra_message: str | None = None,
) -> None:
    try:
        if from_value is None:
            if extra_message is not None:
                raise klass(extra_message)
            raise klass()

        args = list(from_value.args)
        if extra_message is not None:
            if len(args) and isinstance(args[0], str):
                args[0] += " -- " + extra_message
            else:
                args.append(extra_message)
        raise klass(*args) from from_value
    finally:
        klass = None  # type: ignore[assignment]
