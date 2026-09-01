"""Parser protocol shared by every sheet-type parser."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from src.etl.dto import ValidationIssue


@dataclass
class ParseResult:
    issues: list[ValidationIssue] = field(default_factory=list)


class SheetParser(Protocol):
    def parse(self, *args, **kwargs) -> ParseResult: ...
