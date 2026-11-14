"""Crisis resources shown on the public crisis sheet."""

from dataclasses import dataclass


@dataclass(frozen=True)
class CrisisResource:
    id: str
    name: str
    phone: str
    description: str
