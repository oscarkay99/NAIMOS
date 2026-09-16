from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())


class Page(BaseModel, Generic[T]):
    """Standard pagination envelope for list endpoints with unbounded growth
    (e.g. audit logs) - `items` is just this page's slice, `total` is the
    full count matching the filters, so the client can build real page
    controls rather than only ever seeing however many rows fit in one
    fetch."""

    items: list[T]
    total: int
    limit: int
    offset: int
