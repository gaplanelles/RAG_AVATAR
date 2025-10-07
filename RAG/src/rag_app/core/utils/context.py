from contextvars import ContextVar
from typing import Optional
from uuid import UUID

request_id: ContextVar[Optional[str]] = ContextVar('request_id', default=None)

def get_request_id() -> Optional[str]:
    return request_id.get()

def set_request_id(id: Optional[str]) -> None:
    if id:
        request_id.set(id) 