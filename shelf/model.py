from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

ShelfStatus = Literal["undecided", "keep", "delete", "defer", "deleted"]
ShelfKind = Literal["movie", "tv"]


@dataclass
class ShelfItem:
    item_id: str
    title: str
    path: str
    kind: ShelfKind
    size_bytes: int
    last_modified: float
    download_completed_at: float | None = None
    poster_url: str | None = None
    synopsis: str | None = None
    genres: list[str] = field(default_factory=list)
    status: ShelfStatus = "undecided"


@dataclass
class ShelfState:
    version: int = 1
    items: dict[str, ShelfItem] = field(default_factory=dict)
