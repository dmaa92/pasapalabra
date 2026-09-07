# Testing

Each layer is wired to exactly one `make` target — "how do I check this
works" has one answer, not a choice of scripts. All of them run inside
the container, so CI and a laptop run the same thing.

1. **`make validate`** — no containers running: `docker compose config`,
   `compileall` over `app/`, and a JSON parse of the question bank.
2. **`make unit`** — the rules (`tests/unit/test_game.py`) and the
   question bank (`tests/unit/test_content.py`). Time is injected, never
   slept on, so the whole suite is instant.
3. **`make smoke`** — against a running stack (`make up` first): health
   endpoint, create a keyboard game, play a *pasapalabra* and assert the
   turn actually changed; then create a refereed game and assert that the
   board endpoint carries no answers, that the judge endpoint is 403
   without a token, that it does carry the answers with one, and that a
   ruling scores; finally, that both client pages are served.

## What the unit tests cover

- Turn flow: a hit keeps the turn, a miss or a pass hands it over, a
  skipped letter comes back around.
- Clocks: only the active player's clock runs, a timeout takes that
  player out, the survivor plays on alone, and the match ends when both
  are done.
- Pause: pausing charges the time used so far and then stops both
  clocks, a long pause costs nobody a second, nothing can be answered or
  ruled on while paused, pausing twice is not an error, and a finished
  match cannot be paused.
- Scoring: most hits wins, ties break on fewer misses, an identical
  scoreline is a draw.
- Answer matching: case, accents and `ñ` are folded; declared variants
  are accepted; an empty answer never counts.
- Modes: keyboard is the default, an unknown mode is rejected, a typed
  answer in a refereed match and a ruling in a keyboard match are both
  refused, and a judge's hit/miss moves the turn exactly like a typed
  one.
- Content: `validate_rosco` is tested against its own rules — a missing
  letter, an answer that doesn't start with (or contain) its letter, a
  repeat, a clue that leaks its answer, a clue that's too short, an
  unknown kind — and then every shipped rosco is held to it. The
  generator calls the same function, so a generated bank cannot enter
  the repository under a laxer standard than the hand-written one.
- Categories: every rosco declares one, and every category has at least
  two roscos so both players can get a different one.

## Manual acceptance

Before a release, play one full match in the browser and confirm:

1. Both roscos render, and only the active player's panel is
   highlighted and counting down.
2. A hit advances to the next letter without changing player; a miss
   shows the right solution and switches player.
3. A pasapalabra leaves that letter grey and it reappears at the end of
   the lap.
4. When a clock hits zero the panel dims, and the other player carries
   on alone.
5. The final screen shows the winner and both full solution lists.

Then one refereed match:

6. The board shows the judge's link, and the board itself offers no way
   to answer.
7. On the judge panel, the correct answer for the current letter is
   shown, and *correcto* / *fallo* / *pasapalabra* each move the match on
   the board within about a second.
8. Opening `/juez` without a token (or with a wrong one) refuses to load
   the match.
9. Pausing stops both counters on the board, the answer box and the
   judge's ruling buttons stop accepting anything, and resuming picks up
   exactly where the clock stopped.
