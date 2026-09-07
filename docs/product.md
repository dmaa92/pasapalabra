# Product

## Current status

Prototype. A playable two-player Pasapalabra in two modes — typed
answers, and refereed by a judge for competitions — runnable locally with
`docker-compose` and deployable as a single container image anywhere
(`deploy/k8s/`). Not exposed publicly.

## Confirmed requirements

### The game

- Two players, alternating turns. Each has their own rosco and their own
  clock; a clock only runs during its player's turn.
- The rosco is the 25-letter Spanish alphabet without K and W, and each
  letter is either *empieza por* or *contiene la*.
- A hit keeps the turn. A miss or a *pasapalabra* hands it over. A
  skipped letter stays pending and comes back around.
- Default 200 seconds per player, configurable per match between 30 and
  600 seconds.
- Running out of time takes that player out; the other keeps playing
  alone until their own rosco or clock ends.
- A player may stop early ("me planto") and close their rosco.
- Either side can **pause** the match — for a recount, a protest, a
  break. Both clocks stop, no letter can be answered or ruled on while it
  lasts, and the time already spent is charged before stopping, so a
  pause never gives time back. In `juez` mode only the judge can pause.
- The winner is whoever has more hits; ties break on fewer misses, and
  an identical scoreline is a draw.

### Modes

- The mode is chosen when the match is created and cannot change
  mid-match.
- **`teclado`** — players type their answers and the server compares
  them. One screen, which is both board and controller.
- **`juez`** — for competitions: players answer out loud and a judge
  rules. The board (`/`) shows roscos, clocks, score and clue and is
  meant to be projected; it never receives an answer and cannot play.
  The judge panel (`/juez`) shows the answer for the current letter, both
  full answer sheets, and the buttons for hit, miss, pasapalabra and "se
  planta".
- The judge panel is reached with a per-match token, handed out once when
  the match is created, as part of the judge's link.
- The board reflects the judge's rulings within about a second, without
  anyone touching it.
- **`por categoría`** — the third option in the selector. The questions
  come from a themed bank instead of the general one, and the player then
  chooses whether that match is resolved from the keyboard or by a judge.
  It is a question-source choice, not a third rulebook: on the wire it is
  still `mode` (`teclado`/`juez`) plus a `category`.
- Only categories with at least two roscos are offered — one rosco would
  mean both players answering the same questions.
- The rules are identical in every mode; only who resolves a letter, and
  which bank it comes from, differ.

### Category banks

- A category is authored ahead of time with
  `make rosco CATEGORIA="cine español"`, which drafts it with the Claude
  API, validates it mechanically, and writes it into `app/data/roscos/`
  for a human to review and commit (ADR-0008).
- The application never generates questions: at match time it only reads
  files already in the repository, needs no API key, and makes no
  outbound request.

## Constraints

- No account system, no persistence, no payments, no personal data: the
  only user input is a display name and (in `teclado` mode) an answer,
  neither of which is stored beyond the life of the match.
- Ships as one container image with no database and no volume, so it can
  run on any container platform.
- The judge's device must reach the same origin as the board.

## Open questions

- Should matches survive a restart (and therefore support more than one
  replica)? That needs shared state — a decision nobody has made yet.
- How many roscos should a category ship? Two is the minimum that lets
  both players have a different one; a bigger bank means less repetition
  between matches, which matters more for competitions.
- Should a generated bank record who reviewed it, rather than a
  `"reviewed_by_a_human": false` field nothing ever flips?
- Does a judged match need an "undo last ruling" button? A misclick
  currently costs a letter, with no way back.
- Is a single-player or online (two browsers) mode ever wanted? Today's
  design assumes both players are in the same room.
