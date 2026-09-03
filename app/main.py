"""HTTP layer: serves the two client views and the game API.

Correct answers never leave the server in `teclado` mode until the match
is over, so the client cannot be used to look them up. In `juez` mode the
judge does need them, so they are served on a separate endpoint gated by
a per-match token — the board view (the one you project) never receives
them. Game state lives in memory only (see docs/known-limitations.md).
"""
from __future__ import annotations

import secrets
import time
from collections import OrderedDict
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .content import load_roscos
from .game import (CORRECT, DEFAULT_TIME_SECONDS, MODE_JUDGE, MODE_KEYBOARD,
                   PENDING, WRONG, Game, GameOver, WrongMode)

STATIC_DIR = Path(__file__).resolve().parent / "static"

# Bounded so a public deployment can't be pushed into unbounded memory
# growth just by looping over "new game".
MAX_GAMES = 200

app = FastAPI(title="Pasapalabra", version="0.2.0")

ROSCOS = load_roscos()
GAMES: "OrderedDict[str, Game]" = OrderedDict()
_next_rosco = 0


class NewGameRequest(BaseModel):
    player_one: str = Field(default="Jugador 1", max_length=24)
    player_two: str = Field(default="Jugador 2", max_length=24)
    seconds: int = Field(default=int(DEFAULT_TIME_SECONDS), ge=30, le=600)
    mode: Literal["teclado", "juez"] = MODE_KEYBOARD


class AnswerRequest(BaseModel):
    text: str = Field(min_length=1, max_length=80)


class JudgeRequest(BaseModel):
    correct: bool


def _pick_roscos() -> tuple:
    """Hand each player a different rosco, rotating between matches."""
    global _next_rosco
    first = ROSCOS[_next_rosco % len(ROSCOS)]
    second = ROSCOS[(_next_rosco + 1) % len(ROSCOS)]
    _next_rosco = (_next_rosco + 1) % len(ROSCOS)
    return first, second


def _get_game(game_id: str) -> Game:
    game = GAMES.get(game_id)
    if game is None:
        raise HTTPException(status_code=404, detail="partida no encontrada")
    return game


def _controlled_by_judge(game: Game, token: str | None) -> Game:
    """In judge mode only the token holder may play or see the answers.

    This is a per-match secret for a room, not authentication — see
    docs/security.md.
    """
    if game.mode == MODE_JUDGE and not (
        token and game.judge_token and secrets.compare_digest(token, game.judge_token)
    ):
        raise HTTPException(status_code=403, detail="hace falta el token del juez")
    return game


def _play(action) -> dict:
    try:
        return action()
    except GameOver as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except WrongMode as exc:
        raise HTTPException(status_code=409, detail=str(exc))


def _state(game: Game, now: float) -> dict:
    game.sync(now)
    players = []
    for player in game.players:
        question = player.question
        players.append({
            "name": player.name,
            "rosco": player.rosco.name,
            "remaining_seconds": round(max(0.0, player.remaining), 1),
            "finished": player.finished,
            "finish_reason": player.finish_reason,
            "correct": player.count(CORRECT),
            "wrong": player.count(WRONG),
            "pending": player.count(PENDING),
            "letters": [
                {"letter": state.letter, "status": state.status}
                for state in player.letters
            ],
            "current": None if question is None else {
                "letter": question.letter,
                "kind": question.kind,
                "clue": question.clue,
            },
        })
    state = {
        "id": game.id,
        "mode": game.mode,
        "turn": game.turn,
        "over": game.over,
        "winner": game.winner,
        "players": players,
    }
    if game.over:
        # Only now is it safe to reveal what the answers were.
        state["solutions"] = [_answer_sheet(player) for player in game.players]
    return state


def _answer_sheet(player) -> list[dict]:
    return [
        {
            "letter": question.letter,
            "answer": question.answer,
            "status": letter.status,
            "answered_with": letter.answered_with,
        }
        for question, letter in zip(player.rosco.questions, player.letters)
    ]


@app.get("/healthz")
async def healthz() -> dict:
    return {"status": "ok", "roscos": len(ROSCOS), "games": len(GAMES)}


@app.get("/juez")
async def judge_view() -> FileResponse:
    return FileResponse(STATIC_DIR / "juez.html")


@app.post("/api/games", status_code=201)
async def create_game(request: NewGameRequest) -> dict:
    now = time.monotonic()
    while len(GAMES) >= MAX_GAMES:
        GAMES.popitem(last=False)
    token = secrets.token_urlsafe(9) if request.mode == MODE_JUDGE else None
    game = Game.create(
        names=(request.player_one.strip() or "Jugador 1",
               request.player_two.strip() or "Jugador 2"),
        roscos=_pick_roscos(),
        now=now,
        seconds=float(request.seconds),
        mode=request.mode,
        judge_token=token,
    )
    GAMES[game.id] = game
    state = _state(game, now)
    # The only time the token is ever sent: whoever creates the match
    # hands the link to the judge.
    state["judge_token"] = token
    return state


@app.get("/api/games/{game_id}")
async def read_game(game_id: str) -> dict:
    return _state(_get_game(game_id), time.monotonic())


@app.get("/api/games/{game_id}/judge")
async def read_judge_view(game_id: str, token: str | None = None) -> dict:
    """The judge's own view: the board plus both answer sheets."""
    game = _controlled_by_judge(_get_game(game_id), token)
    if game.mode != MODE_JUDGE:
        raise HTTPException(status_code=409, detail="esta partida es de teclado")
    state = _state(game, time.monotonic())
    state["answers"] = [_answer_sheet(player) for player in game.players]
    return state


@app.post("/api/games/{game_id}/judge")
async def judge(game_id: str, request: JudgeRequest, token: str | None = None) -> dict:
    game = _controlled_by_judge(_get_game(game_id), token)
    now = time.monotonic()
    result = _play(lambda: game.judge(request.correct, now))
    return {"result": result, "game": _state(game, now)}


@app.post("/api/games/{game_id}/answer")
async def answer(game_id: str, request: AnswerRequest, token: str | None = None) -> dict:
    game = _controlled_by_judge(_get_game(game_id), token)
    now = time.monotonic()
    result = _play(lambda: game.answer(request.text, now))
    return {"result": result, "game": _state(game, now)}


@app.post("/api/games/{game_id}/pass")
async def skip(game_id: str, token: str | None = None) -> dict:
    game = _controlled_by_judge(_get_game(game_id), token)
    now = time.monotonic()
    result = _play(lambda: game.skip(now))
    return {"result": result, "game": _state(game, now)}


@app.post("/api/games/{game_id}/resign")
async def resign(game_id: str, token: str | None = None) -> dict:
    game = _controlled_by_judge(_get_game(game_id), token)
    now = time.monotonic()
    _play(lambda: game.resign(now))
    return {"result": {"resigned": True}, "game": _state(game, now)}


# Mounted last: the API routes above take precedence over static files.
app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")
