"""Question bank loading and answer normalisation.

Deliberately free of any web-framework import: `make unit` runs this
module (and `game.py`) with nothing but the standard library.
"""
from __future__ import annotations

import json
import pathlib
import unicodedata
from dataclasses import dataclass

# The televised rosco skips K and W, which almost no Spanish word starts
# with. 25 letters, always in this order.
LETTERS = ("A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "L", "M", "N",
           "Ñ", "O", "P", "Q", "R", "S", "T", "U", "V", "X", "Y", "Z")

KIND_STARTS_WITH = "empieza"
KIND_CONTAINS = "contiene"

DATA_PATH = pathlib.Path(__file__).resolve().parent / "data" / "roscos.json"


def normalize(text: str) -> str:
    """Fold an answer down to what we actually compare.

    Case, accents and punctuation are ignored, whitespace is collapsed,
    and `ñ` folds to `n` so a player on a keyboard without it is not
    punished for it.
    """
    decomposed = unicodedata.normalize("NFD", text.strip().lower())
    stripped = "".join(c for c in decomposed if not unicodedata.combining(c))
    kept = "".join(c if c.isalnum() else " " for c in stripped)
    return " ".join(kept.split())


@dataclass(frozen=True)
class Question:
    letter: str
    kind: str
    clue: str
    answer: str
    accepted: tuple[str, ...] = ()

    def matches(self, attempt: str) -> bool:
        candidate = normalize(attempt)
        if not candidate:
            return False
        return candidate in self.accepted_forms()

    def accepted_forms(self) -> frozenset[str]:
        return frozenset(normalize(a) for a in (self.answer, *self.accepted))


@dataclass(frozen=True)
class Rosco:
    id: str
    name: str
    questions: tuple[Question, ...]


def load_roscos(path: pathlib.Path | None = None) -> tuple[Rosco, ...]:
    raw = json.loads((path or DATA_PATH).read_text(encoding="utf-8"))
    return tuple(
        Rosco(
            id=rosco["id"],
            name=rosco["name"],
            questions=tuple(
                Question(
                    letter=q["letter"],
                    kind=q["kind"],
                    clue=q["clue"],
                    answer=q["answer"],
                    accepted=tuple(q.get("accepted", ())),
                )
                for q in rosco["questions"]
            ),
        )
        for rosco in raw["roscos"]
    )
