from __future__ import annotations

from typing import Any


class BaseObject:
    """
    Universal base object.
    Anything in any program can be represented as a descendant of this class.
    """

    def __init__(self, name: str | None = None):
        self.name = name or self.__class__.__name__
        self.properties: dict[str, Any] = {}

    def set_property(self, key: str, value: Any) -> "BaseObject":
        self.properties[str(key)] = value
        return self

    def get_property(self, key: str, default: Any = None) -> Any:
        return self.properties.get(str(key), default)

    def has_property(self, key: str) -> bool:
        return str(key) in self.properties

    def remove_property(self, key: str) -> "BaseObject":
        self.properties.pop(str(key), None)
        return self
