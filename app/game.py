"""Turn-based, two-player Pasapalabra rules.

No I/O and no wall clock: every call that can consume a player's time
takes an explicit monotonic `now`, so the rules are testable without
sleeping and the caller owns the only clock.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from .content import Question, Rosco

DEFAULT_TIME_SECONDS = 200.0

PENDING = "pending"
CORRECT = "correct"
WRONG = "wrong"

FINISH_ROSCO = "rosco"
FINISH_TIMEOUT = "timeout"

# How a letter gets resolved. In `teclado` the player types the answer and
# the server compares it; in `juez` the players say it out loud and a
# judge, looking at the answer sheet, rules on it.
MODE_KEYBOARD = "teclado"
MODE_JUDGE = "juez"
MODES = (MODE_KEYBOARD, MODE_JUDGE)


class GameOver(Exception):
    """Raised when a play is attempted on a game that has already ended."""


class WrongMode(Exception):
    """Raised when a play doesn't belong to the mode the match is in."""


@dataclass
class LetterState:
    letter: str
    status: str = PENDING
    answered_with: str | None = None


@dataclass
class Player:
    name: str
    rosco: Rosco
    remaining: float
    letters: list[LetterState] = field(default_factory=list)
    cursor: int = 0
    finished: bool = False
    finish_reason: str | None = None

    def __post_init__(self) -> None:
        if not self.letters:
            self.letters = [LetterState(q.letter) for q in self.rosco.questions]

    @property
    def question(self) -> Question | None:
        if self.finished:
            return None
        return self.rosco.questions[self.cursor]

    def count(self, status: str) -> int:
        return sum(1 for letter in self.letters if letter.status == status)

    def advance(self) -> None:
        """Move the cursor to the next still-pending letter, wrapping around."""
        total = len(self.letters)
        for offset in range(1, total + 1):
            index = (self.cursor + offset) % total
            if self.letters[index].status == PENDING:
                self.cursor = index
                return
        self.finish(FINISH_ROSCO)

    def finish(self, reason: str) -> None:
        if not self.finished:
            self.finished = True
            self.finish_reason = reason


class Game:
    """A single match between two players, each with their own rosco."""

    def __init__(
        self,
        players: tuple[Player, Player],
        now: float,
        game_id: str | None = None,
        mode: str = MODE_KEYBOARD,
        judge_token: str | None = None,
    ) -> None:
        if mode not in MODES:
            raise ValueError(f"unknown mode: {mode!r}")
        self.id = game_id or uuid.uuid4().hex
        self.players = players
        self.mode = mode
        # Only meaningful in judge mode: whoever holds it controls the
        # match and can see the answers (see docs/security.md).
        self.judge_token = judge_token
        self.turn = 0
        self.turn_started_at = now
        self.created_at = now

    @classmethod
    def create(
        cls,
        names: tuple[str, str],
        roscos: tuple[Rosco, Rosco],
        now: float,
        seconds: float = DEFAULT_TIME_SECONDS,
        game_id: str | None = None,
        mode: str = MODE_KEYBOARD,
        judge_token: str | None = None,
    ) -> "Game":
        players = (
            Player(name=names[0], rosco=roscos[0], remaining=seconds),
            Player(name=names[1], rosco=roscos[1], remaining=seconds),
        )
        return cls(players, now=now, game_id=game_id, mode=mode,
                   judge_token=judge_token)

    # -- state ---------------------------------------------------------

    @property
    def over(self) -> bool:
        return all(player.finished for player in self.players)

    @property
    def active(self) -> Player:
        return self.players[self.turn]

    @property
    def winner(self) -> int | None:
        """Index of the winner, or None for a draw / unfinished game."""
        if not self.over:
            return None
        first, second = self.players
        by_score = [
            (p.count(CORRECT), -p.count(WRONG), index)
            for index, p in enumerate(self.players)
        ]
        best, runner_up = sorted(by_score, reverse=True)
        if best[:2] == runner_up[:2]:
            return None
        return best[2]

    # -- clock ---------------------------------------------------------

    def sync(self, now: float) -> None:
        """Charge elapsed time to the active player and settle the turn."""
        if self.over:
            return
        elapsed = max(0.0, now - self.turn_started_at)
        self.turn_started_at = now
        player = self.active
        if player.finished:
            self._pass_turn(now)
            return
        player.remaining -= elapsed
        if player.remaining <= 0:
            player.remaining = 0.0
            player.finish(FINISH_TIMEOUT)
            self._pass_turn(now)

    def _pass_turn(self, now: float) -> None:
        """Hand over the turn, unless the opponent is already out.

        A finished opponent means the active player keeps going alone,
        against their own clock, until their rosco or time runs out.
        """
        self.turn_started_at = now
        other = 1 - self.turn
        if not self.players[other].finished:
            self.turn = other

    # -- plays ---------------------------------------------------------

    def answer(self, attempt: str, now: float) -> dict:
        """`teclado` mode: the player types it, the server compares it."""
        if self.mode != MODE_KEYBOARD:
            raise WrongMode("this match is refereed by a judge")
        self.sync(now)
        if self.over:
            raise GameOver("the game has already finished")
        question = self.active.question
        assert question is not None  # a non-finished player always has one
        return self._resolve(question.matches(attempt), attempt, now)

    def judge(self, correct: bool, now: float) -> dict:
        """`juez` mode: the player says it out loud, the judge rules."""
        if self.mode != MODE_JUDGE:
            raise WrongMode("this match is played from the keyboard")
        self.sync(now)
        if self.over:
            raise GameOver("the game has already finished")
        return self._resolve(correct, None, now)

    def _resolve(self, correct: bool, attempt: str | None, now: float) -> dict:
        player = self.active
        question = player.question
        assert question is not None
        state = player.letters[player.cursor]
        state.answered_with = attempt
        state.status = CORRECT if correct else WRONG
        player.advance()
        # A hit keeps the turn — unless it closed the rosco and there is
        # nothing left for this player to answer.
        if not correct or player.finished:
            self._pass_turn(now)
        return {
            "correct": correct,
            "letter": question.letter,
            "solution": None if correct else question.answer,
        }

    def skip(self, now: float) -> dict:
        """"Pasapalabra": keep the letter pending and hand over the turn."""
        self.sync(now)
        if self.over:
            raise GameOver("the game has already finished")
        player = self.active
        letter = player.letters[player.cursor].letter
        player.advance()
        self._pass_turn(now)
        return {"skipped": letter}

    def resign(self, now: float) -> None:
        """Stop the active player's rosco early ("me planto")."""
        self.sync(now)
        if self.over:
            raise GameOver("the game has already finished")
        self.active.finish(FINISH_ROSCO)
        self._pass_turn(now)
