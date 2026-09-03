"""Question bank loading, answer normalisation, and the rules a rosco has
to satisfy to be playable.

Deliberately free of any web-framework import: `make unit` runs this
module (and `game.py`) with nothing but the standard library. The
validator lives here rather than in the tests so the generator in
`scripts/generate_rosco.py` can hold generated questions to exactly the
same bar the shipped ones are held to.
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
KINDS = (KIND_STARTS_WITH, KIND_CONTAINS)

MIN_CLUE_LENGTH = 20

DATA_DIR = pathlib.Path(__file__).resolve().parent / "data"
BUILTIN_PATH = DATA_DIR / "roscos.json"
# Generated banks, one file per category (scripts/generate_rosco.py).
GENERATED_DIR = DATA_DIR / "roscos"
DEFAULT_CATEGORY = "general"


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


def slugify(text: str) -> str:
    """Category name -> a safe file stem and URL value."""
    return "-".join(normalize(text).split())


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
    category: str = DEFAULT_CATEGORY


def validate_rosco(rosco: Rosco) -> list[str]:
    """Return every reason this rosco is not playable; empty means good.

    These are the mechanical rules — the ones a machine can settle. That
    an answer is *true* is not among them, and no amount of validation
    here replaces a human reading the questions.
    """
    problems: list[str] = []
    letters = tuple(question.letter for question in rosco.questions)
    if letters != LETTERS:
        problems.append(f"letters must be {'/'.join(LETTERS)}, in order; got {'/'.join(letters)}")

    seen: dict[str, str] = {}
    for question in rosco.questions:
        where = f"{rosco.id}:{question.letter}"
        answer = normalize(question.answer)

        if question.kind not in KINDS:
            problems.append(f"{where}: unknown kind {question.kind!r}")
        if not answer:
            problems.append(f"{where}: empty answer")
            continue

        letter = normalize(question.letter) or question.letter.lower()
        if question.kind == KIND_STARTS_WITH and not answer.startswith(letter):
            problems.append(f"{where}: {question.answer!r} does not start with {question.letter!r}")
        if question.kind == KIND_CONTAINS and question.letter.lower() not in question.answer.lower():
            problems.append(f"{where}: {question.answer!r} does not contain {question.letter!r}")

        clue = question.clue.strip()
        if len(clue) < MIN_CLUE_LENGTH:
            problems.append(f"{where}: clue is too short ({len(clue)} chars)")
        if answer in normalize(clue):
            problems.append(f"{where}: the clue gives {question.answer!r} away")

        if answer in seen:
            problems.append(f"{where}: {question.answer!r} repeats the answer for {seen[answer]!r}")
        seen[answer] = question.letter

    return problems


def _rosco_from(raw: dict, fallback_category: str) -> Rosco:
    return Rosco(
        id=raw["id"],
        name=raw["name"],
        category=raw.get("category", fallback_category),
        questions=tuple(
            Question(
                letter=q["letter"],
                kind=q["kind"],
                clue=q["clue"],
                answer=q["answer"],
                accepted=tuple(q.get("accepted", ())),
            )
            for q in raw["questions"]
        ),
    )


def load_file(path: pathlib.Path) -> tuple[Rosco, ...]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    fallback = raw.get("category", DEFAULT_CATEGORY)
    return tuple(_rosco_from(rosco, fallback) for rosco in raw["roscos"])


def load_roscos(path: pathlib.Path | None = None) -> tuple[Rosco, ...]:
    """The built-in bank plus every generated category bank."""
    if path is not None:
        return load_file(path)
    roscos = list(load_file(BUILTIN_PATH))
    if GENERATED_DIR.is_dir():
        for extra in sorted(GENERATED_DIR.glob("*.json")):
            roscos.extend(load_file(extra))
    return tuple(roscos)


def by_category(roscos: tuple[Rosco, ...]) -> dict[str, list[Rosco]]:
    grouped: dict[str, list[Rosco]] = {}
    for rosco in roscos:
        grouped.setdefault(rosco.category, []).append(rosco)
    return grouped
