from collections.abc import Mapping, Sequence
from typing import Any


class AttributeDict(dict):
    """
    A mapping that allows for attribute-style access of values.
    """
    def _is_valid_key_name(cls, key: str) -> bool:
        is_a_string = isinstance(key, str)
        is_an_identifier = str(key).isidentifier()
        builtin_dict_names = hasattr(cls, key)

        return (is_a_string and is_an_identifier and not builtin_dict_names)

    def _convert(self, obj):
        if isinstance(obj, Mapping):
            obj = AttributeDict(obj)

        if isinstance(obj, Sequence) and not isinstance(obj, (Mapping, str, bytes)):
            seq_cls = type(obj)
            obj = seq_cls(self._convert(element) for element in obj)

        return obj

    def __setattr__(self, key: str, value: Any) -> None:
        """
        Offer the a.b.c interface to dict.

        >>> a.b.c = "y"
        {"a": {"b": {"c": "y"}}
        """
        if not self._is_valid_key_name(key):
            raise ValueError(f"'{key}' is not a valid identifier for '{self.__class__}'")

        self[key] = value

    def __getattr__(self, key: str) -> Any:
        """
        Access an item as an attribute.
        """
        try:
            return self._convert(self[key])
        except KeyError:
            raise AttributeError(f"{self.__class__.__name__} instance has no attribute '{key}'") from None

    def __delattr__(self, key):
        """
        Delete an item as an attribute.
        """
        try:
            return self.pop(key)
        except KeyError:
            raise AttributeError(f"{self.__class__.__name__} instance has no attribute '{key}'") from None


class ArbitraryState:
    """
    An object that can be used to store arbitrary state.
    """

    _state: dict[str, Any]

    def __init__(self, state: dict[str, Any] = None):
        if state is None:
            state = {}

        super().__setattr__("_state", state)

    def __setattr__(self, key: Any, value: Any) -> None:
        self._state[key] = value

    def __getattr__(self, key: Any) -> Any:
        try:
            return self._state[key]
        except KeyError:
            cls_name = self.__class__.__name__
            raise AttributeError(f"'{cls_name}' object has no attribute '{key}'")

    def __delattr__(self, key: Any) -> None:
        del self._state[key]
