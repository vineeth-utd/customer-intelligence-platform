from collections.abc import Callable
from typing import TypeVar

from pydantic import BaseModel

_PayloadT = TypeVar("_PayloadT", bound=BaseModel)

_PAYLOAD_REGISTRY: dict[tuple[str, int], type[BaseModel]] = {}


def register_event_payload(event_type: str, event_version: int) -> Callable[[type[_PayloadT]], type[_PayloadT]]:
    """Register a payload schema for a given (event_type, event_version).

    Ships empty in Unit 3.1 - later generator units register their own
    payload schemas here without needing to modify this module.
    """

    def decorator(payload_cls: type[_PayloadT]) -> type[_PayloadT]:
        key = (event_type, event_version)
        if key in _PAYLOAD_REGISTRY:
            raise ValueError(f"A payload schema is already registered for {key}")
        _PAYLOAD_REGISTRY[key] = payload_cls
        return payload_cls

    return decorator


def get_payload_schema(event_type: str, event_version: int) -> type[BaseModel] | None:
    return _PAYLOAD_REGISTRY.get((event_type, event_version))
