# Architecture

## Components

One process, one container image, no database:

- `app/game.py` — the rules: turns, clocks, scoring, and the two modes
  (`teclado` / `juez`). Pure Python, no I/O and no wall clock (every call
  takes an explicit monotonic `now`), so the rules are testable without
  sleeping.
- `app/content.py` — loads the question banks, normalises answers (case,
  accents, punctuation, `ñ` → `n`), and owns `validate_rosco()`: the
  single statement of what makes a rosco playable. The unit tests hold
  the shipped banks to it and the generator holds its drafts to it, so
  generated content cannot enter under a laxer standard.
- `app/main.py` — the HTTP layer: FastAPI serves the JSON API under
  `/api/`, `/healthz`, the board at `/` and the judge panel at `/juez`.
- `app/static/` — the two browser views: plain HTML/CSS/JS, no build
  step, no bundler, no framework.
- `scripts/generate_rosco.py` — **not part of the running system.** An
  authoring tool that drafts a category's roscos with the Claude API and
  writes them into `app/data/roscos/` for a human to review. It lives in
  its own Dockerfile stage (`tools`) with the Anthropic SDK and an API
  key; the deployed `runtime` stage has neither (ADR-0008).

## Question banks

`app/data/roscos.json` is the built-in general bank. Every
`app/data/roscos/*.json` is a generated category bank, loaded and
appended at startup. A rosco carries a `category`; categories are
addressed over the wire by slug (`GET /api/categories`) and a match is
created with `mode` plus an optional `category`. The two axes are
deliberately separate: `mode` says who resolves a letter, `category` says
where the questions come from.

## The two views

`teclado` mode uses one view: the board is also the controller, and the
player types into it.

`juez` mode splits them, because the two audiences are different — one
screen is projected, the other must show the answers:

```
   PROJECTOR                              JUDGE'S PHONE
   GET /  (#<id>)                         GET /juez  (#<id>:<token>)
   ├─ polls /api/games/{id} every 1s      ├─ polls /api/games/{id}/judge?token=
   │  roscos, clocks, score, clue         │  same, plus both answer sheets
   └─ cannot play                         └─ POST .../judge {correct}
                                             POST .../pass, .../resign
```

The token is minted once, when the match is created, and returned only in
that response. In `juez` mode every mutating endpoint — and the endpoint
that carries the answers — requires it; the board's own endpoint never
includes an answer.

## Request flow

```
browser  ──POST /api/games──────────────▶  main.py  ──▶ Game.create()
         ◀──game state (no answers)─────

teclado  ──POST /api/games/{id}/answer─▶  main.py  ──▶ Game.answer(now)
juez     ──POST /api/games/{id}/judge──▶  main.py  ──▶ Game.judge(now)
         ◀──hit/miss + new state───────
```

Both plays land on the same `Game._resolve()`, so the rules cannot drift
apart between modes: only *who decides* whether the letter was right
differs. Every request that can consume time calls `Game.sync(now)`
first, so a player's clock is charged from the server's monotonic clock,
never from anything a browser reports. The browser only *interpolates*
the countdown between responses, and asks the server to settle it when it
reaches zero.

## Trust boundaries

- The browser is untrusted. It cannot add time, choose whose turn it is,
  or score a letter for itself — those live only in `Game`.
- In `teclado` mode no client ever receives a correct answer until the
  match is over. In `juez` mode the answers go only to the token-gated
  judge endpoint. The board view is identical in both.
- The judge token is a per-match shared secret for a room, not
  authentication: it identifies "the device holding the link", not a
  person. See `docs/security.md`.
- Request bodies are validated by Pydantic models with explicit bounds
  (name length, answer length, 30–600 s per player, mode from a fixed
  set). A game id that isn't in memory is a 404, not an error page.
- The container runs as a non-root user, read-only, with all
  capabilities dropped (`docker-compose.yml`, `deploy/k8s/`).

## State and lifecycle

Matches live in an in-memory `OrderedDict` in the app process, capped at
`MAX_GAMES` (oldest evicted first) so a public deployment can't be pushed
into unbounded memory growth. Nothing is persisted: a restart drops every
match in progress, and running more than one replica would serve half the
requests from an empty match list — including the judge's, which is why
judge mode makes the single-replica constraint load-bearing rather than
merely convenient. See `docs/known-limitations.md`,
`docs/decisions/0006-pasapalabra-web-game.md` and
`docs/decisions/0007-judge-mode.md`.

## Portability

The only deployment contract is: run the image, give it a port, hit
`/healthz`. No volume, no database, no environment variable is required
to start. `deploy/k8s/` is that same contract expressed as a Deployment
plus a ClusterIP Service; how (and whether) it gets exposed outside a
cluster is an environment decision, not a property of the app. Judge mode
only adds one requirement: the judge's device has to reach the same
origin as the board.
